#!/usr/bin/env python3
"""Build the vprwre.com static site from the scraped @vprwre posts + research."""
import json, re, html, shutil, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image

ROOT = Path(__file__).parent
RAW = ROOT / "raw" / "vprwre"
OUT = ROOT / "site"
PT = ZoneInfo("America/Los_Angeles")
IG = "https://www.instagram.com/vprwre/"

# Editorial layer: headline = the cover card's headline, plus a section label.
EDIT = {
    "Dd_pqv6GwEH": ("AI is grading you.", "AI tools", "ai-is-grading-you"),
    "Dd_rr8eG3UQ": ("Asana paid $75M to buy one year.", "Deals", "asana-paid-75m-to-buy-one-year"),
    "DeA51JIm32R": ("Your AI butler will take tips.", "Funding", "your-ai-butler-will-take-tips"),
    "DeA6lrhm9mp": ("They called it a wrapper. It’s worth $5.4B.", "Funding", "they-called-it-a-wrapper"),
    "DeA7AdeG7UQ": ("He backs both. He went after one.", "Drama", "he-backs-both-he-went-after-one"),
    "DeB83ftm9KZ": ("Did AI write France’s No. 1 novel?", "Drama", "did-ai-write-frances-no-1-novel"),
    "DeBGUYeG468": ("He agreed to slow down. Then floored it.", "The AI race", "he-agreed-to-slow-down-then-floored-it"),
    "DeBGmRQmyL2": ("Behind in AI, Zuck goes for your keychain.", "The AI race", "behind-in-ai-zuck-goes-for-your-keychain"),
    "DeBHBdPmxHl": ("The man selling shovels says: dig faster.", "The AI race", "the-man-selling-shovels-says-dig-faster"),
}

MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]

def apdate(dt):
    return f"{MONTHS[dt.month-1]} {dt.day}, {dt.year}"

def aptime(dt):
    h = dt.hour % 12 or 12
    ap = "a.m." if dt.hour < 12 else "p.m."
    return f"{h}:{dt.minute:02d} {ap} PT" if dt.minute else f"{h} {ap} PT"

def smart(s):
    """Typographer's quotes for straight quotes in caption text."""
    s = re.sub(r'(^|[\s(\[—–/-])"', r'\1“', s)
    s = s.replace('"', '”')
    s = re.sub(r"(\w)'(\w)", r"\1’\2", s)
    s = re.sub(r"(^|[\s(\[—–/-])'", r"\1‘", s)
    s = s.replace("'", "’")
    s = s.replace("No. 1 ", "No. 1 ")
    return s

def esc(s):
    return html.escape(smart(s), quote=False)

def attr(s):
    return html.escape(s, quote=True)

def reflow(caption):
    """Turn a caption into paragraphs. Some captions were pasted with hard wraps."""
    caption = caption.replace("\r", "")
    if "\n\n" in caption:
        paras = [p.replace("\n", " ").strip() for p in caption.split("\n\n")]
    else:
        lines = [l.strip() for l in caption.split("\n") if l.strip()]
        paras, cur = [], []
        for i, line in enumerate(lines):
            if cur and re.match(r"(Our take|In fairness|Context|On the record|What we can)", line):
                paras.append(" ".join(cur)); cur = []
            cur.append(line)
            ends = re.search(r'[.?!:”"]$', line)
            if ends and (len(line) < 72 or i == 0):
                paras.append(" ".join(cur)); cur = []
        if cur:
            paras.append(" ".join(cur))
    return [re.sub(r"\s+", " ", p) for p in paras if p]

DROP = re.compile(r"^(Sources and photo credits in the first comment\.?|The Take, by VPRWRE\.com\.?)$", re.I)

def split_caption(caption, title):
    paras = reflow(caption)
    out, disclosure = [], None
    for p in paras:
        if p.startswith("#") or DROP.match(p):
            continue
        if p.lower().startswith("disclosure:"):
            disclosure = p.split(":", 1)[1].strip()
            continue
        out.append(p)
    dek, body = out[0], out[1:]
    # If the hook repeats the headline, keep only what follows it.
    norm = lambda x: x.replace("’", "'").lower()
    if norm(dek).startswith(norm(title)):
        rest = dek[len(title):].lstrip(" ?.!")
        if rest:
            dek = rest
    return dek, body, disclosure

LABEL = re.compile(r"^((?:Our take|In fairness|Context|What we can[’']t verify|Still unverified|Founders|Why|Then the investors weighed in)):\s*(.*)$")
RECORD = re.compile(r"^On the record,\s*([^:]+):\s*(.*)$")

def render_body(body):
    parts = []
    for p in body:
        m = RECORD.match(p)
        if m:
            parts.append(
                f'<aside class="record"><p class="record-label"><span class="tag">On the record</span> '
                f'<time>{esc(m.group(1))}</time></p><p>{esc(m.group(2)[:1].upper() + m.group(2)[1:])}</p></aside>')
            continue
        m = LABEL.match(p)
        if m:
            parts.append(f"<p><strong>{esc(m.group(1))}:</strong> {esc(m.group(2))}</p>")
            continue
        parts.append(f"<p>{esc(p)}</p>")
    return "\n".join(parts)

def save_img(src, dst, width, quality):
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    if im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)

FONTS = ""  # fonts are self-hosted in /assets/fonts (see site.css)

def head(title, desc, url, image=None, depth=0):
    pre = "../" * depth
    og_img = f'<meta property="og:image" content="https://vprwre.com/{image}">' if image else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{attr(smart(desc))}">
<link rel="canonical" href="https://vprwre.com/{url}">
<meta property="og:site_name" content="VPRWRE">
<meta property="og:title" content="{attr(smart(title))}">
<meta property="og:description" content="{attr(smart(desc))}">
<meta property="og:url" content="https://vprwre.com/{url}">
{og_img}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
{FONTS}
<link rel="stylesheet" href="{pre}assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>"""

def masthead(depth=0, home=False):
    pre = "../" * depth
    tag = "h1" if home else "p"
    return f"""<header class="masthead">
  <div class="mast-row">
    <p class="dateline" data-today>{apdate(datetime.datetime.now(PT))}</p>
    <{tag} class="wordmark"><a href="{pre or './'}">VPRWRE</a></{tag}>
    <p class="mast-links"><a href="{IG}">Instagram</a></p>
  </div>
  <p class="motto">The pro-human newsroom for AI, startups and venture capital. <span class="since">Since 2021.</span></p>
</header>"""

FOOTER = f"""<footer class="site-footer">
  <p class="wordmark small">VPRWRE</p>
  <p>Every story here first ran as a carousel on <a href="{IG}">@vprwre</a>. VPRWRE drafts with Claude, Anthropic’s AI.</p>
  <p class="fine">© {datetime.date.today().year} VPRWRE</p>
</footer>
<script>
(function(){{var el=document.querySelector('[data-today]');if(!el)return;try{{var d=new Date();var m=['Jan.','Feb.','March','April','May','June','July','Aug.','Sept.','Oct.','Nov.','Dec.'];var w=d.toLocaleDateString('en-US',{{weekday:'long',timeZone:'America/Los_Angeles'}});var p=new Intl.DateTimeFormat('en-US',{{timeZone:'America/Los_Angeles',year:'numeric',month:'numeric',day:'numeric'}}).formatToParts(d);var g=function(t){{return p.find(function(x){{return x.type===t}}).value}};el.textContent=w+', '+m[+g('month')-1]+' '+g('day')+', '+g('year');}}catch(e){{}}}})();
</script>
</body>
</html>"""

def build():
    research = {r["code"]: r for r in json.loads((ROOT / "research.json").read_text())}
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "assets").mkdir()
    shutil.copy(ROOT / "site.css", OUT / "assets" / "site.css")
    shutil.copytree(ROOT / "fonts", OUT / "assets" / "fonts")
    shutil.copy(ROOT / "favicon.svg", OUT / "favicon.svg")

    stories = []
    for d in sorted(RAW.iterdir()):
        meta = json.loads((d / "meta.json").read_text())
        code = meta["code"]
        title, section, slug = EDIT[code]
        dt = datetime.datetime.fromtimestamp(meta["taken_at"], PT)
        dek, body, disclosure = split_caption(meta["caption"], title)
        slides = sorted(d.glob("slide-*.jpg"))
        img_dir = OUT / "images" / slug
        save_img(slides[0], img_dir / "cover.jpg", 1080, 84)
        save_img(slides[0], img_dir / "thumb.jpg", 600, 82)
        for i, s in enumerate(slides, 1):
            save_img(s, img_dir / f"slide-{i:02d}.jpg", 1080, 80)
        stories.append(dict(code=code, title=title, section=section, slug=slug, dt=dt, dek=dek,
                            body=body, disclosure=disclosure, n=len(slides), ig=meta["url"],
                            research=research.get(code)))
    stories.sort(key=lambda s: s["dt"], reverse=True)

    # Article pages
    for idx, s in enumerate(stories):
        r = s["research"]
        bg = ""
        if r:
            paras = "\n".join(f"<p>{esc(p)}</p>" for p in r["background"])
            srcs = "\n".join(
                f'<li><a href="{attr(x["url"])}" rel="noopener">{esc(x["title"])}</a> <span class="pub">{esc(x["publisher"])}</span></li>'
                for x in r["sources"])
            bg = f"""<section class="background" aria-labelledby="bg-h">
  <h2 id="bg-h">Background</h2>
  {paras}
  <h3>Sources</h3>
  <ul class="sources">{srcs}</ul>
</section>"""
        slides_html = "\n".join(
            f'<li><img src="../../images/{s["slug"]}/slide-{i:02d}.jpg" width="1080" height="1350" loading="lazy" decoding="async" alt="Slide {i} of {s["n"]}"></li>'
            for i in range(1, s["n"] + 1))
        more = [o for o in stories if o is not s][:3]
        more_html = "\n".join(f"""<li><a href="../{o['slug']}/">
  <img src="../../images/{o['slug']}/thumb.jpg" width="600" height="750" loading="lazy" alt="">
  <span class="kicker">{esc(o['section'])}</span>
  <span class="more-title">{esc(o['title'])}</span></a></li>""" for o in more)
        disc = esc(s["disclosure"] or "VPRWRE drafts with Claude, Anthropic’s AI.")
        page = head(f"{s['title']} | VPRWRE", s["dek"], f"p/{s['slug']}/", f"images/{s['slug']}/cover.jpg", depth=2)
        page += masthead(depth=2)
        page += f"""
<main id="main" class="article">
  <article>
    <header class="article-head">
      <p class="kicker">{esc(s['section'])}</p>
      <h1 class="headline">{esc(s['title'])}</h1>
      <p class="dek">{esc(s['dek'])}</p>
      <p class="byline"><span class="tag">The Take</span> <span>By VPRWRE</span> <time datetime="{s['dt'].isoformat()}">{apdate(s['dt'])}, {aptime(s['dt'])}</time></p>
    </header>
    <figure class="hero">
      <img src="../../images/{s['slug']}/cover.jpg" width="1080" height="1350" alt="Cover card of the @vprwre carousel: {attr(smart(s['title']))}">
      <figcaption>The cover of the original carousel. <a href="{attr(s['ig'])}">See it on Instagram</a>.</figcaption>
    </figure>
    <div class="body">
{render_body(s['body'])}
    </div>
    {bg}
    <section class="carousel" aria-labelledby="car-h">
      <div class="carousel-head"><h2 id="car-h">The carousel</h2><p>{s['n']} slides · <a href="{attr(s['ig'])}">Open on Instagram</a></p></div>
      <ul class="slides" tabindex="0" aria-label="Carousel slides, scroll sideways">
{slides_html}
      </ul>
    </section>
    <p class="disclosure"><strong>Disclosure:</strong> {disc}</p>
  </article>
  <aside class="more" aria-labelledby="more-h">
    <h2 id="more-h">More from The Take</h2>
    <ul>{more_html}</ul>
  </aside>
</main>
""" + FOOTER
        p = OUT / "p" / s["slug"]
        p.mkdir(parents=True)
        (p / "index.html").write_text(page)

    # Home page
    lead, rest = stories[0], stories[1:]
    def card(o, cls="card"):
        return f"""<li class="{cls}"><a href="p/{o['slug']}/">
  <img src="images/{o['slug']}/thumb.jpg" width="600" height="750" loading="lazy" alt="">
  <span class="kicker">{esc(o['section'])}</span>
  <span class="card-title">{esc(o['title'])}</span>
  <span class="card-dek">{esc(o['dek'])}</span>
  <time datetime="{o['dt'].isoformat()}">{apdate(o['dt'])}</time></a></li>"""
    home = head("VPRWRE — The pro-human newsroom", "The Take by VPRWRE: opinionated, sourced stories on AI, startups and venture capital.", "", f"images/{lead['slug']}/cover.jpg")
    home += masthead(home=True)
    home += f"""
<main id="main" class="front">
  <section class="lead" aria-label="Top story">
    <a class="lead-link" href="p/{lead['slug']}/">
      <div class="lead-text">
        <p class="kicker">{esc(lead['section'])}</p>
        <h2 class="lead-title">{esc(lead['title'])}</h2>
        <p class="lead-dek">{esc(lead['dek'])}</p>
        <p class="lead-meta"><span class="tag">The Take</span> <time datetime="{lead['dt'].isoformat()}">{apdate(lead['dt'])}</time></p>
      </div>
      <img class="lead-img" src="images/{lead['slug']}/cover.jpg" width="1080" height="1350" alt="">
    </a>
  </section>
  <section class="latest" aria-labelledby="latest-h">
    <h2 id="latest-h" class="rule-head">Latest</h2>
    <ul class="grid">
{chr(10).join(card(o) for o in rest)}
    </ul>
  </section>
</main>
""" + FOOTER
    (OUT / "index.html").write_text(home)

    # 404
    nf = head("Page not found | VPRWRE", "Page not found", "404.html")
    nf += masthead() + '<main id="main" class="notfound"><h2>That page isn’t here.</h2><p><a href="/">Go to the front page</a> to see the latest stories.</p></main>' + FOOTER
    (OUT / "404.html").write_text(nf)

    # Data for automations, GitHub Pages config
    (OUT / "posts.json").write_text(json.dumps([
        {"code": s["code"], "title": s["title"], "url": f"https://vprwre.com/p/{s['slug']}/",
         "instagram": s["ig"], "published": s["dt"].isoformat()} for s in stories], indent=2))
    (OUT / "CNAME").write_text("vprwre.com\n")
    (OUT / ".nojekyll").write_text("")
    print("built", len(stories), "stories")
    for s in stories:
        print(f"  {s['dt']:%m-%d %H:%M}  {s['slug']}  | dek: {s['dek'][:70]}")

if __name__ == "__main__":
    build()
