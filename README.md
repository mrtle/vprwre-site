# vprwre.com

The website for **The Take by VPRWRE**. Every story first ran as a carousel on [@vprwre](https://www.instagram.com/vprwre/).
Static site, served by GitHub Pages from the repository root (custom domain in `CNAME`).

## Layout

| Path | What it is |
| --- | --- |
| `content/posts/<code>.json` | One file per Instagram post: headline, section, slug, publish time, caption, slide count, background research. **The source of truth.** |
| `images/<slug>/` | `cover.jpg` (1080w), `thumb.jpg` (600w), `slide-NN.jpg` (1080w) |
| `assets/site.css`, `assets/fonts/`, `favicon.svg` | Edited directly. Fonts: Archivo and Newsreader (SIL Open Font License). |
| `index.html`, `p/<slug>/index.html`, `404.html`, `posts.json` | **Generated** by `tools/build.py`. Don't edit by hand. |
| `tools/` | The generator and the scraping scripts. |

## Adding new posts (what the nightly task does)

1. **Scrape** in Chrome on the always-on Mac (Instagram works signed out):
   for each new post, open `https://www.instagram.com/vprwre/p/<code>/` and run `tools/scrape-post.js`
   with the Claude in Chrome JavaScript tool. It stores the slides and caption in that tab's IndexedDB.
2. **Package**: in the same tab, run `tools/zip-download.js` with two lines prepended:
   `const CODES = [...]; const FILENAME = "vprwre-new-YYYY-MM-DD.zip";`
   Chrome saves the zip to the Mac's Downloads folder.
3. **Bring it over** with the device file tools, unzip, then for each post:
   `python3 tools/add_post.py --src <unzipped>/vprwre/<code> --title "<cover headline>" --section "<section>" --research research.json`
   - `--title`: the headline exactly as printed on the cover card (slide-01).
   - `--section`: reuse one of AI tools, Deals, Funding, Drama, The AI race when it fits.
   - `research.json`: `{"background": ["2-3 short paragraphs"], "sources": [{"title","publisher","url"}], "notes": "fact-check notes"}`
4. `python3 tools/build.py`, check the output, commit and push. Pages redeploys in about a minute.
