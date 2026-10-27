
#!/usr/bin/env python3
"""Magaddino Files - Section 1 test viewer."""
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
OUTPUT = pathlib.Path("viewer-test-output")
CACHE = pathlib.Path("cache/section1_djvu.xml")


def escape(value):
    return html.escape(str(value), quote=True)


def download_xml():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    if CACHE.exists() and CACHE.stat().st_size > 1000:
        print("Using cached XML.")
        return

    print("Downloading page-structured OCR...")
    request = urllib.request.Request(
        XML_URL,
        headers={"User-Agent": "MagaddinoHistoricalArchive/1.0"}
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        with CACHE.open("wb") as destination:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                destination.write(chunk)
    print("Download complete.")


def extract_pages():
    pages = []
    for event, element in ET.iterparse(str(CACHE), events=("end",)):
if element.tag.upper() != "OBJECT":
            continue

        words = []
        for word in element.iter():
            if word.tag.upper() == "WORD" and word.text:
                words.append(word.text.strip())

        pages.append({
            "number": len(pages) + 1,
         "source": next((p.get("value", "") for p in element.findall("PARAM") if p.get("name") == "PAGE"), ""),
            "ocr": " ".join(words)
        })
        element.clear()

    return pages


CSS = """
*{box-sizing:border-box}
body{
 margin:0;
 background:#292017;
 color:#f0dfc1;
 font-family:Georgia,serif;
}
header{
 background:#17110c;
 padding:18px 25px;
 border-bottom:3px solid #a18458;
}
header h1{margin:0;font-size:24px}
nav{margin-top:12px}
a{color:#f0dfc1}
nav a{margin-right:18px}
main{max-width:1500px;margin:auto;padding:20px}
h2{font-size:25px}
.viewer{
 display:grid;
 grid-template-columns:1fr 1fr;
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
 font:16px/1.7 Consolas,monospace;
 background:#f5ecd9;
 padding:20px;
 min-height:70vh;
}
.controls{
 display:flex;
 justify-content:space-between;
 gap:12px;
 margin:22px 0;
}
.controls a{
 background:#8c241b;
 padding:13px 20px;
 text-decoration:none;
 border:1px solid #c69a67;
}
.notice{font-size:13px}
@media(max-width:800px){
 .viewer{grid-template-columns:1fr}
 iframe{height:65vh}
 .ocr{min-height:200px}
 header h1{font-size:20px}
}
"""


def render_page(page, total):
    n = page["number"]
    previous = f"page-{n-1:04d}.html" if n > 1 else None
    following = f"page-{n+1:04d}.html" if n < total else None

    scan_url = (
        f"https://archive.org/embed/{ARCHIVE_ID}"
        f"/page/n{n-1}/mode/1up"
    )

    previous_link = (
        f'<a href="{previous}">← Previous page</a>'
        if previous else "<span>First page</span>"
    )
    next_link = (
        f'<a href="{following}">Next page →</a>'
        if following else "<span>Last page</span>"
    )

    ocr_text = page["ocr"] or "[No OCR text detected]"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stefano Magaddino FBI Section 1 Page {n}</title>
<meta name="description"
 content="FBI Section 1 page {n}: original scan and searchable OCR.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
<h1>THE MAGADDINO FILES</h1>
<nav>
<a href="index.html">Home</a>
<a href="index.html">Back to Section 1</a>
<a href="https://archive.org/details/{ARCHIVE_ID}">
Original source</a>
</nav>
</header>
<main>
<h2>Stefano Magaddino — FBI Section 1</h2>
<p>Document page {n} of {total}</p>
<div class="controls">
{previous_link}
{next_link}
</div>
<div class="viewer">
<section class="panel">
<h3>Original FBI scan</h3>
<iframe src="{escape(scan_url)}"
 title="Original FBI scan, page {n}"
 loading="lazy"></iframe>
<p class="notice">
If the embedded reader does not display the correct page,
<a href="https://archive.org/details/{ARCHIVE_ID}/page/n{n-1}/mode/1up"
 target="_blank" rel="noopener">open the original scan</a>.
</p>
</section>
<section class="panel">
<h3>OCR transcription — Page {n}</h3>
<div class="ocr">{escape(ocr_text)}</div>
<p class="notice">
Machine-generated OCR. Verify against the original scan.
</p>
</section>
</div>
<div class="controls">
{previous_link}
{next_link}
</div>
<footer>Historical archive research: Joseph Augstell</footer>
</main>
</body>
</html>"""


def main():
    download_xml()
    pages = extract_pages()

    print(f"XML pages found: {len(pages)}")
    if len(pages) != EXPECTED_PAGES:
        raise RuntimeError(
            f"Expected {EXPECTED_PAGES} pages, found {len(pages)}. "
            "Review page alignment before publishing."
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "style.css").write_text(CSS, encoding="utf-8")

    links = []
    for page in pages:
        n = page["number"]
        filename = f"page-{n:04d}.html"
        (OUTPUT / filename).write_text(
            render_page(page, len(pages)),
            encoding="utf-8"
        )
        links.append(f'<a href="{filename}">Page {n}</a>')

    index = (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Magaddino FBI Section 1</title>'
        '<link rel="stylesheet" href="style.css"></head>'
        '<body><header><h1>THE MAGADDINO FILES</h1></header>'
        '<main><h2>Stefano Magaddino — FBI Section 1</h2>'
        '<p>277 original pages with matching OCR transcriptions.</p>'
        '<p><a href="page-0001.html">Open the viewer →</a></p>'
        '<div style="display:grid;grid-template-columns:'
        'repeat(auto-fit,minmax(100px,1fr));gap:15px">'
        + "".join(links) +
        '</div></main></body></html>'
    )
    (OUTPUT / "index.html").write_text(
        index, encoding="utf-8"
    )

    (OUTPUT / "page-data.json").write_text(
        json.dumps(pages, ensure_ascii=False),
        encoding="utf-8"
    )

    print("SUCCESS: Section 1 test viewer generated.")
    print("Output directory:", OUTPUT)


if __name__ == "__main__":
    main()
