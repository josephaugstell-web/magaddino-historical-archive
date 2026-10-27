
#!/usr/bin/env python3
"""Magaddino Files: standalone Section 1 test builder.

Run: python build_viewer_test.py
Output: viewer-test-output/
"""
import html
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

ARCHIVE_ID = "magaddino-file-1"
XML_URL = (
    "https://archive.org/download/magaddino-file-1/"
    "Magaddino%20file%201_djvu.xml"
)
EXPECTED_PAGES = 277
ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "viewer-test-output"
CACHE = ROOT / "cache" / "section1_djvu.xml"


def escape(value):
    return html.escape(str(value), quote=True)


def tag_name(element):
    if not isinstance(element.tag, str):
        return ""
    return element.tag.rsplit("}", 1)[-1].upper()


def download_xml():
    CACHE.parent.mkdir(parents=True, exist_ok=True)

    if CACHE.exists() and CACHE.stat().st_size > 1000:
        print("Using cached XML.")
        return

    print("Downloading Internet Archive OCR...")

    request = urllib.request.Request(
        XML_URL,
        headers={
            "User-Agent": "MagaddinoHistoricalArchive/1.0"
        }
    )

    partial = CACHE.with_suffix(".xml.part")

    try:
        with urllib.request.urlopen(
            request, timeout=180
        ) as response:
            with partial.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)

        if partial.stat().st_size <= 1000:
            raise RuntimeError(
                "Downloaded XML is unexpectedly small."
            )

        partial.replace(CACHE)

    finally:
        partial.unlink(missing_ok=True)

    print("Download complete.")


def extract_pages():
    """Extract page-aligned OCR from DjVu XML."""

    pages = []
    root = ET.parse(CACHE).getroot()

    direct_pages = []
    object_pages = []

    for element in root.iter():
        kind = tag_name(element)

        if kind == "PAGE":
            direct_pages.append(element)

        elif kind == "OBJECT":
            has_page_param = any(
                tag_name(child) == "PARAM"
                and child.get("name", "").upper() == "PAGE"
                for child in element
            )

            if has_page_param:
                object_pages.append(element)

    print(
        "XML structure:",
        len(direct_pages),
        "PAGE nodes;",
        len(object_pages),
        "OBJECT page nodes"
    )

    direct_has_words = any(
        any(tag_name(x) == "WORD" for x in e.iter())
        for e in direct_pages[:3]
    )

    if direct_pages and direct_has_words:
        selected = direct_pages
    elif object_pages:
        selected = object_pages
    else:
        selected = direct_pages

    for element in selected:
        source = element.get("value", "")

        if tag_name(element) == "OBJECT":
            source = next(
                (
                    p.get("value", "")
                    for p in element
                    if tag_name(p) == "PARAM"
                    and p.get("name", "").upper() == "PAGE"
                ),
                ""
            )

        lines = []

        for line in element.iter():
            if tag_name(line) == "LINE":
                words = [
                    "".join(w.itertext()).strip()
                    for w in line.iter()
                    if tag_name(w) == "WORD"
                ]

                if words:
                    lines.append(
                        " ".join(w for w in words if w)
                    )

        if lines:
            ocr = "\n".join(lines)
        else:
            ocr = " ".join(
                "".join(w.itertext()).strip()
                for w in element.iter()
                if tag_name(w) == "WORD"
            )

        pages.append({
            "number": len(pages) + 1,
            "source": source,
            "ocr": ocr
        })

    return pages


CSS = """
*{box-sizing:border-box}

body{
 margin:0;
 background:#241b14;
 color:#f0dfc1;
 font-family:Georgia,serif;
}

header{
 background:#140f0b;
 padding:18px 25px;
 border-bottom:3px solid #a18458;
}

header h1{
 margin:0;
 font-size:clamp(19px,3vw,28px);
}

nav{
 display:flex;
 gap:18px;
 flex-wrap:wrap;
 margin-top:12px;
}

a{color:#f0dfc1}

main{
 max-width:1500px;
 margin:auto;
 padding:20px;
}

h2{
 font-size:clamp(20px,3vw,29px);
}

.viewer{
 display:grid;
 grid-template-columns:minmax(0,1fr) minmax(0,1fr);
 gap:18px;
}

.panel{
 background:#d7c4a1;
 color:#241b12;
 padding:16px;
 border:2px solid #96784f;
 min-width:0;
}

.panel h3{margin-top:0}

iframe{
 width:100%;
 height:75vh;
 border:0;
 background:white;
}

.ocr{
 white-space:pre-wrap;
 overflow-wrap:anywhere;
 font:15px/1.6 Consolas,monospace;
 background:#f5ecd9;
 padding:20px;
 min-height:70vh;
}

.controls{
 display:flex;
 justify-content:space-between;
 gap:12px;
 margin:22px 0;
 flex-wrap:wrap;
}

.controls a{
 background:#8c241b;
 padding:13px 20px;
 text-decoration:none;
 border:1px solid #c69a67;
}

.notice{font-size:13px}

.page-grid{
 display:grid;
 grid-template-columns:repeat(auto-fit,minmax(100px,1fr));
 gap:12px;
}

.page-grid a{
 background:#5a3928;
 padding:10px;
 text-align:center;
}

@media(max-width:800px){
 .viewer{grid-template-columns:1fr}
 iframe{height:65vh}
 .ocr{min-height:200px}
}
"""


def render_page(page, total):
    n = page["number"]

    prev = (
        f'<a href="page-{n-1:04d}.html">'
        '← Previous page</a>'
        if n > 1
        else "<span>First page</span>"
    )

    nxt = (
        f'<a href="page-{n+1:04d}.html">'
        'Next page →</a>'
        if n < total
        else "<span>Last page</span>"
    )

    scan_url = (
        f"https://archive.org/embed/{ARCHIVE_ID}"
        f"/page/n{n-1}/mode/1up"
    )

    original_url = (
        f"https://archive.org/details/{ARCHIVE_ID}"
        f"/page/n{n-1}/mode/1up"
    )

    ocr = (
        page["ocr"]
        or "[No OCR text detected on this page]"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
 content="width=device-width,initial-scale=1">
<title>Stefano Magaddino FBI Section 1 — Page {n}</title>
<meta name="description"
 content="Stefano Magaddino FBI Section 1, scanned page {n} and OCR transcription">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
<h1>THE MAGADDINO FILES</h1>
<nav>
<a href="index.html">Section 1 Home</a>
<a href="https://archive.org/details/{ARCHIVE_ID}">
Internet Archive source</a>
</nav>
</header>

<main>
<h2>Stefano Magaddino — FBI Section 1</h2>
<p>Scanned page {n} of {total}</p>

<div class="controls">
{prev}
<span>{n} / {total}</span>
{nxt}
</div>

<div class="viewer">

<section class="panel">
<h3>Original FBI scan</h3>

<iframe
 src="{escape(scan_url)}"
 title="Original FBI scan page {n}"
 loading="lazy">
</iframe>

<p class="notice">
<a href="{escape(original_url)}"
 target="_blank" rel="noopener">
Open original scan directly
</a>
</p>
</section>

<section class="panel">
<h3>OCR transcription — Page {n}</h3>

<article class="ocr">{escape(ocr)}</article>

<p class="notice">
Uncorrected machine OCR. Verify names, dates,
and quotations against the original FBI scan.
</p>
</section>

</div>

<div class="controls">
{prev}
<span>{n} / {total}</span>
{nxt}
</div>

<footer>
Research and online publication: Joseph Augstell.
FBI documents retain their original authorship.
</footer>
</main>
</body>
</html>"""


def main():
    download_xml()
    pages = extract_pages()

    print(
        f"Extracted {len(pages)} OCR pages; "
        f"expected {EXPECTED_PAGES} scanned pages"
    )

    if len(pages) != EXPECTED_PAGES:
        print(
            "First page names:",
            [p["source"] for p in pages[:5]]
        )

        raise RuntimeError(
            f"Page count mismatch: found {len(pages)}, "
            f"expected {EXPECTED_PAGES}. "
            "Do not publish until verified."
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    (OUTPUT / "style.css").write_text(
        CSS, encoding="utf-8"
    )

    links = []

    for page in pages:
        n = page["number"]
        filename = f"page-{n:04d}.html"

        (OUTPUT / filename).write_text(
            render_page(page, len(pages)),
            encoding="utf-8"
        )

        links.append(
            f'<a href="{filename}">Page {n}</a>'
        )

    index = (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" '
        'content="width=device-width,initial-scale=1">'
        '<title>Magaddino FBI Section 1</title>'
        '<link rel="stylesheet" href="style.css">'
        '</head><body>'
        '<header><h1>THE MAGADDINO FILES</h1></header>'
        '<main>'
        '<h2>Stefano Magaddino — FBI Section 1</h2>'
        f'<p>{len(pages)} scanned pages with '
        'page-aligned OCR.</p>'
        '<p><a href="page-0001.html">'
        'Open viewer →</a></p>'
        '<div class="page-grid">'
        + "".join(links)
        + '</div></main></body></html>'
    )

    (OUTPUT / "index.html").write_text(
        index, encoding="utf-8"
    )

    (OUTPUT / "page-data.json").write_text(
        json.dumps(pages, ensure_ascii=False),
        encoding="utf-8"
    )

    print(
        f"SUCCESS: generated {len(pages)} "
        f"page files in {OUTPUT}"
    )

    print(
        "Original scan iframe position still "
        "requires browser verification."
    )


if __name__ == "__main__":
    main()
