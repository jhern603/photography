"""Build web-ready images and photos.js for the portfolio.

Usage:  python build.py [--force]

Reads originals from pics/, titles/categories/alt text from photos.meta.json, and writes:
  img/thumb/<slug>.jpg   grid images (1200px long edge)
  img/large/<slug>.jpg   lightbox images (2400px long edge)
  photos.js              data loaded by index.html
  index.html             refreshes everything that must work without JavaScript
  sitemap.xml            page and image sitemap for search engines

Web copies are re-encoded without EXIF, so GPS and other metadata in the
originals never reach the site. Only the camera settings listed below are kept.
"""

import datetime
import html
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).parent
SRC = ROOT / "pics"
OUT = ROOT / "img"
SIZES = {"thumb": (1200, 80), "large": (2400, 85)}
EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

EXIF_IFD = 0x8769
TAGS = {
    "model": 0x0110,
    "lens": 0xA434,
    "fnumber": 0x829D,
    "exposure": 0x829A,
    "iso": 0x8827,
    "focal": 0x920A,
    "date": 0x9003,
}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")


def read_exif(img):
    exif = img.getexif()
    ifd = exif.get_ifd(EXIF_IFD)
    raw = {k: ifd.get(tag, exif.get(tag)) for k, tag in TAGS.items()}
    out = {}
    if raw["model"]:
        out["camera"] = str(raw["model"]).strip("\x00 ")
    if raw["lens"]:
        out["lens"] = str(raw["lens"]).strip("\x00 ")
    if raw["focal"]:
        out["focal"] = f"{float(raw['focal']):g}mm"
    if raw["fnumber"]:
        out["aperture"] = f"f/{float(raw['fnumber']):g}"
    if raw["exposure"]:
        t = float(raw["exposure"])
        out["shutter"] = f"{t:g}s" if t >= 0.3 else f"1/{round(1 / t)}s"
    if raw["iso"]:
        iso = raw["iso"][0] if isinstance(raw["iso"], tuple) else raw["iso"]
        out["iso"] = f"ISO {iso}"
    if raw["date"]:
        out["date"] = str(raw["date"])[:10].replace(":", "-")
    return out


def save_resized(img, dest, long_edge, quality, force):
    if dest.exists() and not force:
        return
    copy = img.copy()
    copy.thumbnail((long_edge, long_edge), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    copy.convert("RGB").save(dest, "JPEG", quality=quality, optimize=True, progressive=True)


def fill_block(page, name, content):
    """Replace what sits between <!-- build:name --> and <!-- /build:name -->."""
    pattern = rf"(<!-- build:{name} -->).*?(\s*<!-- /build:{name} -->)"
    page, count = re.subn(pattern, lambda m: f"{m[1]}\n{content}{m[2]}", page, count=1, flags=re.S)
    if not count:
        raise SystemExit(f"index.html is missing the build:{name} markers")
    return page


def thumb_size(photo):
    """Pixel size of a grid image, whose long edge is the thumb size unless the original is smaller."""
    edge = SIZES["thumb"][0]
    ratio = photo["ratio"]
    return (edge, round(edge / ratio)) if ratio >= 1 else (round(edge * ratio), edge)


def structured_data(site, photos):
    url = site["url"]
    person = {"@type": "Person", "name": site["name"], "url": site.get("portfolio", url)}
    if site.get("instagram"):
        person["sameAs"] = [f"https://instagram.com/{site['instagram'].lstrip('@')}"]
    data = {
        "@context": "https://schema.org",
        "@type": "ImageGallery",
        "name": f"{site['name']} Photography",
        "description": site.get("tagline", ""),
        "url": url,
        "inLanguage": "en",
        "author": person,
        "image": [{
            "@type": "ImageObject",
            "contentUrl": url + p["large"],
            "thumbnailUrl": url + p["thumb"],
            "name": p["title"],
            "description": p["alt"],
            "creator": person,
            "creditText": site["name"],
            "copyrightNotice": f"© {site['name']}",
        } for p in photos],
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def write_index(site, photos):
    """Put the content crawlers and no-JS visitors need directly into index.html."""
    path = ROOT / "index.html"
    page = path.read_text(encoding="utf-8")
    e = lambda s: html.escape(str(s), quote=True)
    url = site["url"]
    hero = next((p for p in photos if p["id"] == site.get("hero")), photos[0])
    w, h = thumb_size(hero)
    image_alt = f"{hero['title']} by {site['name']}"

    page = re.sub(r'(data-site="(\w+)"[^>]*>)[^<]*',
                  lambda m: m[1] + e(site.get(m[2], "")), page)
    page = re.sub(r'(id="year">)\d*', rf"\g<1>{datetime.date.today().year}", page)

    page = fill_block(page, "social", "\n".join([
        f'  <meta property="og:image" content="{e(url + hero["thumb"])}">',
        f'  <meta property="og:image:width" content="{w}">',
        f'  <meta property="og:image:height" content="{h}">',
        f'  <meta property="og:image:alt" content="{e(image_alt)}">',
        f'  <meta name="twitter:image" content="{e(url + hero["thumb"])}">',
        f'  <meta name="twitter:image:alt" content="{e(image_alt)}">',
        f'  <script type="application/ld+json">{structured_data(site, photos)}</script>',
    ]))

    page = fill_block(page, "hero", (
        f'      <img class="hero-img" id="hero-img" src="{e(hero["large"])}" '
        f'srcset="{e(hero["thumb"])} 1200w, {e(hero["large"])} 2400w" '
        f'sizes="max(100vw, {round(100 * hero["ratio"])}vh)" width="{w}" height="{h}" '
        f'alt="{e(hero["alt"])}" fetchpriority="high">'
    ))

    contact = []
    if site.get("email"):
        contact.append(f'        <a href="mailto:{e(site["email"])}">{e(site["email"])}</a>')
    if site.get("instagram"):
        handle = site["instagram"].lstrip("@")
        contact.append(f'        <a href="https://instagram.com/{e(handle)}" target="_blank" rel="noopener">'
                       f'@{e(handle)}<span class="visually-hidden"> on Instagram (opens in a new tab)</span></a>')
    page = fill_block(page, "contact", "\n".join(contact))

    items = []
    for p in photos:
        tw, th = thumb_size(p)
        items.append(f'          <li><a href="{e(p["large"])}"><img src="{e(p["thumb"])}" alt="{e(p["alt"])}" '
                     f'width="{tw}" height="{th}" loading="lazy" decoding="async">{e(p["title"])}</a></li>')
    page = fill_block(page, "noscript", '        <noscript><ul class="noscript-gallery">\n'
                      + "\n".join(items) + "\n        </ul></noscript>")
    path.write_text(page, encoding="utf-8")


def write_sitemap(site, photos):
    url = html.escape(site["url"])
    images = "\n".join(f"    <image:image><image:loc>{url}{html.escape(p['large'])}</image:loc></image:image>"
                       for p in photos)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        f"  <url>\n    <loc>{url}</loc>\n{images}\n  </url>\n</urlset>\n",
        encoding="utf-8",
    )


def main():
    force = "--force" in sys.argv
    meta = json.loads((ROOT / "photos.meta.json").read_text(encoding="utf-8"))
    photo_meta = meta.get("photos", {})
    categories = meta.get("categories", [])

    sources = sorted(p for p in SRC.iterdir() if p.is_file() and p.suffix.lower() in EXTS)
    # Order by category (as listed in meta), then by the order photos appear in meta.
    order = list(photo_meta)
    sources.sort(key=lambda p: (
        categories.index(photo_meta.get(p.name, {}).get("category"))
        if photo_meta.get(p.name, {}).get("category") in categories else len(categories),
        order.index(p.name) if p.name in order else len(order),
        p.name,
    ))

    photos = []
    for src in sources:
        slug = slugify(src.name)
        info = photo_meta.get(src.name, {})
        with Image.open(src) as img:
            exif = read_exif(img)
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            for kind, (edge, q) in SIZES.items():
                save_resized(img, OUT / kind / f"{slug}.jpg", edge, q, force)
        photos.append({
            "id": slug,
            "title": info.get("title") or src.stem,
            "alt": info.get("alt") or info.get("title") or src.stem,
            "category": info.get("category") or "Uncategorized",
            "ratio": round(w / h, 4),
            "thumb": f"img/thumb/{slug}.jpg",
            "large": f"img/large/{slug}.jpg",
            "exif": exif,
        })
        print(f"  {src.name:<22} -> {slug}  {w}x{h}")
        if src.name not in photo_meta:
            print(f"    (no entry in photos.meta.json — add a title, category, and alt text)")
        elif not info.get("alt"):
            print(f"    (no alt text in photos.meta.json — describe the photo for screen readers)")

    used = [c for c in categories if any(p["category"] == c for p in photos)]
    used += sorted({p["category"] for p in photos} - set(used))
    data = {"site": meta.get("site", {}), "categories": used, "photos": photos}
    js = "window.PORTFOLIO = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    (ROOT / "photos.js").write_text(js, encoding="utf-8")
    write_index(data["site"], photos)
    write_sitemap(data["site"], photos)
    print(f"Wrote photos.js, index.html, and sitemap.xml with {len(photos)} photos.")


if __name__ == "__main__":
    main()
