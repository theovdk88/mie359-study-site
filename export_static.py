#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parent
DIST_DIR = SITE_DIR / "dist"
DATA_DIR = SITE_DIR / "data"

ROOT_FILES = [
    "index.html",
    "app.js",
    "styles.css",
]

HEADERS_TEXT = """\
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: SAMEORIGIN

/index.html
  Cache-Control: public, max-age=0, must-revalidate

/app.js
  Cache-Control: public, max-age=0, must-revalidate

/styles.css
  Cache-Control: public, max-age=0, must-revalidate

/data/site.json
  Cache-Control: public, max-age=0, must-revalidate
"""


def main() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "data").mkdir(parents=True, exist_ok=True)

    for filename in ROOT_FILES:
        shutil.copy2(SITE_DIR / filename, DIST_DIR / filename)

    shutil.copy2(DATA_DIR / "site.json", DIST_DIR / "data" / "site.json")
    (DIST_DIR / "_headers").write_text(HEADERS_TEXT, encoding="utf-8")

    print(f"Exported static site to {DIST_DIR}")


if __name__ == "__main__":
    main()
