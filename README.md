# Fanxu Meng — Academic homepage

Source for [fxmeng.github.io](https://fxmeng.github.io/). The site is intentionally built with semantic HTML and modern CSS only: there is no package manager, JavaScript framework, or build step.

## Local preview

From the repository root, run:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000>.

## Updating the site

- Edit biography, links, and publication entries in `index.html`.
- Put optimized images in `images/` and prefer WebP for photographs and publication thumbnails.
- Keep meaningful alternative text and explicit `width`/`height` attributes on every image.
- Run `python3 scripts/check_site.py` before committing.

GitHub Pages publishes the repository root from `main`. The quality workflow checks the HTML structure, local links, metadata, and image-size budget on every pull request.
