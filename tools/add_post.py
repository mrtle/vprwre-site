#!/usr/bin/env python3
"""Add one scraped @vprwre post to the site's content.

Usage:
  python3 tools/add_post.py --src DIR --title "Cover headline." --section "Funding" \
      [--slug custom-slug] [--research research.json]

DIR is one post folder from the scrape zip: meta.json plus slide-01.jpg, slide-02.jpg, ...
--title   the headline exactly as printed on the cover card (slide-01), sentence case.
--section one short section label; reuse an existing one when it fits
          (AI tools, Deals, Funding, Drama, The AI race).
--research a JSON file: {"background": ["para", ...], "sources": [{"title","publisher","url"}], "notes": "..."}

Writes images/<slug>/{cover,thumb,slide-NN}.jpg and content/posts/<code>.json.
Then run: python3 tools/build.py
"""
import argparse, json, re, datetime, unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PT = ZoneInfo("America/Los_Angeles")


def slugify(title):
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:70].rstrip("-")


def save_img(src, dst, width, quality):
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    if im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--section", required=True)
    ap.add_argument("--slug")
    ap.add_argument("--research")
    a = ap.parse_args()

    src = Path(a.src)
    meta = json.loads((src / "meta.json").read_text())
    slides = sorted(src.glob("slide-*.jpg"))
    if not slides:
        raise SystemExit(f"no slides in {src}")
    code = meta["code"]
    slug = a.slug or slugify(a.title)
    existing = {json.loads(f.read_text())["slug"]: f.stem for f in (ROOT / "content" / "posts").glob("*.json")}
    if slug in existing and existing[slug] != code:
        slug = f"{slug}-{code.lower()[:6]}"

    img = ROOT / "images" / slug
    save_img(slides[0], img / "cover.jpg", 1080, 84)
    save_img(slides[0], img / "thumb.jpg", 600, 82)
    for i, s in enumerate(slides, 1):
        save_img(s, img / f"slide-{i:02d}.jpg", 1080, 80)

    research = json.loads(Path(a.research).read_text()) if a.research else {}
    post = {
        "code": code,
        "slug": slug,
        "title": a.title,
        "section": a.section,
        "published": datetime.datetime.fromtimestamp(meta["taken_at"], PT).isoformat(),
        "instagram": f"https://www.instagram.com/vprwre/p/{code}/",
        "slides": len(slides),
        "caption": meta["caption"],
        "research": {k: research[k] for k in ("background", "sources", "notes") if k in research},
    }
    out = ROOT / "content" / "posts" / f"{code}.json"
    out.write_text(json.dumps(post, indent=2, ensure_ascii=False))
    print(f"added {code} -> /p/{slug}/ ({len(slides)} slides)")


if __name__ == "__main__":
    main()
