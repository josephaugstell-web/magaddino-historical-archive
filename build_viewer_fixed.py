
#!/usr/bin/env python3
"""
Magaddino Files - synchronized viewer test.

Builds the existing 277-page viewer, then creates a
separate version where the embedded Internet Archive
reader cannot advance independently of the OCR.
"""

import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
FIXED = ROOT / "viewer-fixed-output"


def main():
    print("Building original Section 1 viewer...")

    subprocess.run(
        [sys.executable, str(ROOT / "build_viewer_test.py")],
        cwd=ROOT,
        check=True
    )

    # Find the folder produced by the existing builder.
    candidates = []

    for file in ROOT.rglob("page-0001.html"):
        parent = file.parent

        if FIXED in file.parents:
            continue

        if parent == ROOT:
            continue

        count = len(list(parent.glob("page-*.html")))

        if count >= 277:
            candidates.append(parent)

    if not candidates:
        raise RuntimeError(
            "Could not find the 277 generated HTML pages."
        )

    source = candidates[0]
    print("Found original viewer:", source)

    if FIXED.exists():
        shutil.rmtree(FIXED)

    shutil.copytree(source, FIXED)

    # Disable the embedded reader's independent controls.
    # Our HTML Previous/Next links remain functional.
    css_files = list(FIXED.glob("*.css"))

    sync_css = """

/* Synchronized page navigation */
iframe {
    pointer-events: none !important;
}

iframe, .viewer iframe {
    touch-action: none !important;
}
/* Internet Archive toolbar cleanup - test only */
iframe {
    clip-path: inset(0 0 45px 0);
}
"""

    if css_files:
        for css_file in css_files:
            with css_file.open(
                "a", encoding="utf-8"
            ) as f:
                f.write(sync_css)

    changed = 0

    for file in sorted(FIXED.glob("page-*.html")):
        text = file.read_text(encoding="utf-8")

        # Also disable interaction directly on each iframe.
        text = re.sub(
            r"<iframe\b",
            '<iframe tabindex="-1" '
            'style="pointer-events:none" ',
            text,
            count=1,
            flags=re.IGNORECASE
        )

        # Add a clear navigation instruction.
        instruction = (
            '<p style="background:#f4e3b9;'
            'color:#302015;padding:12px;'
            'border:2px solid #8b6842;">'
            '<strong>SYNCED VIEWER:</strong> '
            'Use the red Previous Page and Next Page '
            'buttons outside the original FBI scan. '
            'Both panels will change together.'
            '</p>'
        )

        if "<main" in text:
            text = re.sub(
                r"(<main\b[^>]*>)",
                lambda m: m.group(1) + instruction,
                text,
                count=1,
                flags=re.IGNORECASE
            )

        file.write_text(text, encoding="utf-8")
        changed += 1

    if changed != 277:
        raise RuntimeError(
            f"Expected 277 HTML pages, found {changed}"
        )

    print("SUCCESS: 277 synchronized viewer pages created.")
    print("Output:", FIXED)
    print("The original viewer has not been modified.")
    print("OCR correction is a separate next step.")


if __name__ == "__main__":
    main()
