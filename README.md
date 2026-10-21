# Magaddino Historical Records Archive — expandable starter

This is a **real, editable static website generator** for the 10 Internet Archive sections. It supports additional collections (including trial transcripts) later. It uses existing Internet Archive OCR and never requires manually typing all the pages.

## What's included

- Home page naming the original FBI author and the contributing researcher/publisher
- Collections list and 10 source sections
- Automatic download of `_djvu.txt` OCR via Internet Archive public metadata API
- One HTML page per OCR page when form-feed boundaries exist; otherwise labeled OCR text segments, with **no invented page numbers**
- Browser search using a compact, precomputed word index (multiple words = AND matching)
- Source links, sitemap.xml, robots.txt, an OCR quality notice and build-report.json
- Extensible `sources.json` for future collections and trial records
- Cloudflare Pages-compatible `public/` output

## Important: Preview vs fully populated site

The included `preview_site/` shows the complete site navigation **without actual OCR** because this build environment cannot fetch Internet Archive document bytes. It is **not the completed 4,646-page transcript site**. A full run of `build.py` from a machine or GitHub Actions runner that can reach Internet Archive downloads the OCR automatically. It may take several minutes. Review `public/build-report.json` to see which files were successfully included. Don't publish the preview in place of the full build unless you only want a navigation hub.

## Easiest repeatable free publishing setup

1. On GitHub, make a free repository and upload the files from this project, including `.github/workflows/build.yml`. (GitHub can manage these site-source files.)
2. In `.github/workflows/build.yml` replace `YOUR-PROJECT` with the Pages project name you choose.
3. In GitHub, open **Actions → Build searchable archive → Run workflow**. Internet connectivity and GitHub Actions free-tier availability apply.
4. When the workflow finishes, download the `magaddino-website` artifact, unzip it to get the built site files. **Check `build-report.json`: all 10 entries should say downloaded/cached OCR, not errors.**
5. In Cloudflare, create a free **Workers & Pages → Pages → Direct Upload** project, and upload the built output folder (not the original source-code ZIP). Follow Cloudflare's current upload flow; a ZIP of the generated contents may also be accepted. Cloudflare issues a `*.pages.dev` URL.
6. In the workflow file, change the base URL to the real Cloudflare Pages URL and run again; republish the updated output so `sitemap.xml` and `robots.txt` point to the actual domain.
7. Verify your Pages domain in [Google Search Console](https://search.google.com/search-console) and submit `https://YOUR-PROJECT.pages.dev/sitemap.xml`. Indexing every word is not guaranteed.

Alternatively run locally with Python 3.10+: `python build.py --base-url https://YOUR-PROJECT.pages.dev`. Files are generated in `public/`.

## Add the entire trial file or more future records

Upload the trial file to Internet Archive and confirm it has a publicly available OCR `.txt` derivative; then add a new collection to `sources.json`:

```json
{
  "id": "magaddino-trial",
  "title": "Magaddino Trial Records",
  "description": "Court documents, transcripts, and exhibits.",
  "items": [
    {"id": "trial-volume-1", "title": "Trial file — volume 1", "archive_id": "REPLACE_WITH_INTERNET_ARCHIVE_ID"}
  ]
}
```

Add this new collection **inside the `collections` array** alongside the FBI collection, keeping valid JSON commas. Rerun the build. New collection pages and search index entries are generated automatically. Add more items the same way.

## Cautions

- This program publishes OCR as-is. Some names, dates, and words will be inaccurate. Never silently present it as a certified verbatim transcript.
- Archive.org does not guarantee a `.txt` derivative for every source; report lists missing or failed downloads.
- If the OCR `.txt` has no form-feed page breaks, generated pages are labeled *text segments*, **not the original scan page numbers**. These link to the item, not fictitious page matches.
- The 20,000-file limit on Cloudflare Pages Free is enough for the current archive, but check growth as you add materials.
- The Google sitemap requires the **real** live URL. Google indexing and AI ingestion are not guaranteed.
- Source documents were authored by government agencies, not the uploader. Crediting the contributor does not convey authorship or guarantee Google attribution.
- Do not include personal contact details or unreviewed private/sensitive personal information in additional contemporary records.
