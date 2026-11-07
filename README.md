# Photography Portfolio

A static portfolio site: justified photo grid, category filters, and a full-screen viewer that shows camera settings.

## Adding or changing photos

1. Drop originals into `pics/`.
2. Add a title, category, and alt text for each one in `photos.meta.json` (the key is the filename). Alt text describes what's in the photo for people using screen readers, and helps it show up in image search.
3. Run the build:

   ```bash
   python build.py
   ```

   This writes resized copies to `img/thumb/` and `img/large/`, plus `photos.js` and `sitemap.xml`, and refreshes the parts of `index.html` between `<!-- build:... -->` markers (edit `photos.meta.json` rather than those parts). Pass `--force` to regenerate images that already exist. Needs Pillow (`pip install Pillow`).

Web copies are saved without EXIF, so GPS and other metadata in the originals never reach the site. Only camera model, lens, and exposure settings are kept, in `photos.js`.

## Site settings

In `photos.meta.json` under `site`: your name, site URL, portfolio URL, tagline, email, Instagram handle, and `hero` (the photo id, i.e. its lowercase filename without extension, used as the full-screen cover image). Categories appear in the order listed in `categories`.

## Preview

```bash
python -m http.server 8000
```

Then open http://localhost:8000.

## Deploying

Upload `index.html`, `404.html`, `favicon.svg`, `robots.txt`, `sitemap.xml`, `photos.js`, `assets/`, and `img/`. Don't upload `pics/` (305 MB of originals). Works on GitHub Pages, Netlify, Cloudflare Pages, or any static host.
