#!/usr/bin/env python3
"""Dependency-free structural checks for the static homepage."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MAX_IMAGE_BYTES = 200_000
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()
        self.links: list[tuple[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.h1_count = 0
        self.html_lang = ""
        self.has_description = False
        self.has_canonical = False
        self.has_viewport = False
        self.inline_styles = 0
        self.element_stack: list[str] = []
        self.nesting_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag not in VOID_ELEMENTS:
            self.element_stack.append(tag)
        element_id = values.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)
        if "style" in values:
            self.inline_styles += 1
        if tag == "html":
            self.html_lang = values.get("lang", "")
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a" and values.get("href"):
            self.links.append(("href", values["href"]))
        elif tag == "link":
            href = values.get("href")
            if href:
                self.links.append(("href", href))
            if values.get("rel") == "canonical":
                self.has_canonical = True
        elif tag == "img":
            self.images.append(values)
            if values.get("src"):
                self.links.append(("src", values["src"]))
        elif tag == "meta":
            if values.get("name") == "description" and values.get("content"):
                self.has_description = True
            if values.get("name") == "viewport" and values.get("content"):
                self.has_viewport = True

    def handle_endtag(self, tag: str) -> None:
        if not self.element_stack:
            self.nesting_errors.append(f"Unexpected closing tag </{tag}>.")
            return
        expected = self.element_stack.pop()
        if expected != tag:
            self.nesting_errors.append(f"Expected </{expected}> before </{tag}>.")


def local_path(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc or url.startswith("mailto:"):
        return None
    path = unquote(parsed.path)
    if not path or path == "/":
        return INDEX
    return ROOT / path.lstrip("/")


def main() -> int:
    errors: list[str] = []
    html = INDEX.read_text(encoding="utf-8")
    parser = SiteParser()
    parser.feed(html)
    if parser.element_stack:
        errors.append(f"Unclosed HTML elements: {', '.join(parser.element_stack)}.")
    errors.extend(parser.nesting_errors)

    if parser.html_lang != "en":
        errors.append("The root html element must declare lang=\"en\".")
    if parser.h1_count != 1:
        errors.append(f"Expected exactly one h1, found {parser.h1_count}.")
    if not parser.has_description:
        errors.append("Missing meta description.")
    if not parser.has_canonical:
        errors.append("Missing canonical link.")
    if not parser.has_viewport:
        errors.append("Missing viewport metadata.")
    if parser.duplicate_ids:
        errors.append(f"Duplicate IDs: {', '.join(sorted(parser.duplicate_ids))}.")
    if parser.inline_styles:
        errors.append(f"Found {parser.inline_styles} inline style attribute(s); use css/style.css.")

    for image in parser.images:
        src = image.get("src", "<missing src>")
        if not image.get("alt"):
            errors.append(f"Image {src} needs meaningful alt text.")
        if not image.get("width") or not image.get("height"):
            errors.append(f"Image {src} needs width and height attributes.")

    for attribute, url in parser.links:
        parsed = urlparse(url)
        if parsed.scheme == "http":
            errors.append(f"Insecure external URL in {attribute}: {url}")
        target = local_path(url)
        if target and not target.exists():
            errors.append(f"Missing local target for {attribute}: {url}")
        if parsed.fragment and (not parsed.path or parsed.path == "/") and parsed.fragment not in parser.ids:
            errors.append(f"Missing fragment target: #{parsed.fragment}")

    for css_file in (ROOT / "css").glob("*.css"):
        css = css_file.read_text(encoding="utf-8")
        for url in re.findall(r"url\([\"']?([^\"')]+)", css):
            if url.startswith("data:"):
                continue
            target = local_path(url) if url.startswith("/") else (css_file.parent / url).resolve()
            if target and not target.exists():
                errors.append(f"Missing CSS asset referenced by {css_file.relative_to(ROOT)}: {url}")

    for image in (ROOT / "images").glob("*"):
        if image.is_file() and image.stat().st_size > MAX_IMAGE_BYTES:
            errors.append(f"Image exceeds {MAX_IMAGE_BYTES // 1000} KB budget: {image.relative_to(ROOT)}")

    if errors:
        print("Site checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Site checks passed: {len(parser.images)} images, {len(parser.links)} local/external references.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
