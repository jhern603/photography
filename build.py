"""Build web-ready images and photos.js for the portfolio.

Usage:  python build.py [--force]

Reads originals from pics/, titles/categories from photos.meta.json, and writes:
  img/thumb/<slug>.jpg   grid images (1200px long edge)
  img/large/<slug>.jpg   lightbox images (2400px long edge)
  photos.js              data loaded by index.html

Web copies are re-encoded without EXIF, so GPS and other metadata in the
originals never reach the site. Only the camera settings listed below are kept.
"""

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
            "category": info.get("category") or "Uncategorized",
            "ratio": round(w / h, 4),
            "thumb": f"img/thumb/{slug}.jpg",
            "large": f"img/large/{slug}.jpg",
            "exif": exif,
        })
        print(f"  {src.name:<22} -> {slug}  {w}x{h}")
        if src.name not in photo_meta:
            print(f"    (no entry in photos.meta.json — add a title and category)")

    used = [c for c in categories if any(p["category"] == c for p in photos)]
    used += sorted({p["category"] for p in photos} - set(used))
    data = {"site": meta.get("site", {}), "categories": used, "photos": photos}
    js = "window.PORTFOLIO = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    (ROOT / "photos.js").write_text(js, encoding="utf-8")
    print(f"Wrote photos.js with {len(photos)} photos.")


if __name__ == "__main__":
    main()
