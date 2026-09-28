# Photography Portfolio

A static portfolio site: justified photo grid, category filters, and a full-screen viewer that shows camera settings.

## Adding or changing photos

1. Drop originals into `pics/`.
2. Add a title and category for each one in `photos.meta.json` (the key is the filename).
3. Run the build:

   ```bash
   python build.py
   ```

   This writes resized copies to `img/thumb/` and `img/large/`, plus `photos.js`. Pass `--force` to regenerate images that already exist. Needs Pillow (`pip install Pillow`).

Web copies are saved without EXIF, so GPS and other metadata in the originals never reach the site. Only camera model, lens, and exposure settings are kept, in `photos.js`.

## Site settings

In `photos.meta.json` under `site`: your name, tagline, email, Instagram handle, and `hero` (the photo id, i.e. its lowercase filename without extension, used as the full-screen cover image). Categories appear in the order listed in `categories`.

## Preview

```bash
python -m http.server 8000
```

Then open http://localhost:8000.

## Deploying

Upload `index.html`, `photos.js`, `assets/`, and `img/`. Don't upload `pics/` (305 MB of originals). Works on GitHub Pages, Netlify, Cloudflare Pages, or any static host.
