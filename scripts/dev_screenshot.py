"""Dev-only screenshot helper for visual review of the running site.

Usage (with the dev server running and `pip install playwright` done):
    python scripts/dev_screenshot.py /                 # one path
    python scripts/dev_screenshot.py / /en/ /tarifas/  # several
    BASE=http://127.0.0.1:8000 VIEWPORT=375x812 python scripts/dev_screenshot.py /

PNGs are written to /tmp/redib-shots/. Not part of the app; needs Playwright
(not in requirements) and a headless Chromium (`playwright install chromium`).
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8000")
VW, VH = (int(x) for x in os.environ.get("VIEWPORT", "1280x900").split("x"))
FULL = os.environ.get("FULL", "1") != "0"
OUT = Path("/tmp/redib-shots")
OUT.mkdir(parents=True, exist_ok=True)

paths = sys.argv[1:] or ["/"]

with sync_playwright() as p:
    browser = p.chromium.launch()
    for path in paths:
        page = browser.new_page(viewport={"width": VW, "height": VH})
        page.goto(BASE + path, wait_until="networkidle", timeout=30000)
        # Strip the Django Debug Toolbar (dev-only; absent in prod) so it
        # doesn't overlap the page in screenshots.
        page.evaluate("document.getElementById('djDebug')?.remove()")
        wait = int(os.environ.get("WAIT", "0"))
        if wait:
            page.wait_for_timeout(wait)
        slug = path.strip("/").replace("/", "_").replace("?", "_") or "home"
        if wait:
            slug = f"{slug}_t{wait}"
        fp = OUT / f"{slug}_{VW}x{VH}.png"
        page.screenshot(path=str(fp), full_page=FULL)
        print(fp)
        page.close()
    browser.close()
