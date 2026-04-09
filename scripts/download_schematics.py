#!/usr/bin/env python3
"""
Download all schematics from Experimentalists Anonymous into ~/schematics/<category>/
Uses curl (system SSL) to avoid Python cert issues. 10 parallel workers, polite throttle.
"""

import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

BASE_URL  = "https://www.experimentalistsanonymous.com/diy/"
INDEX_URL = BASE_URL + "index.php?dir=Schematics/"
DEST_ROOT = Path.home() / "schematics"

CURL_OPTS = [
    "-s", "-L",
    "--max-time", "20",
    "--retry", "3",
    "--retry-delay", "2",
    "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "-H", "Referer: https://www.experimentalistsanonymous.com/diy/index.php?dir=Schematics/",
    "-H", "Accept: application/pdf,image/gif,image/jpeg,image/png,*/*",
]

EXTS = {".gif", ".jpg", ".jpeg", ".png", ".pdf"}

# ── HTML parser ───────────────────────────────────────────────────────────────

class FolderParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.folders = []
        self.files   = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if not href:
            return
        if "index.php?dir=Schematics//" in href and ".." not in href:
            folder = href.split("index.php?dir=Schematics//")[1]
            if folder:
                self.folders.append(urllib.parse.unquote(folder))
        elif any(href.lower().endswith(ext) for ext in EXTS):
            self.files.append(href)

# ── Network helpers ───────────────────────────────────────────────────────────

def curl_get(url):
    result = subprocess.run(
        ["curl"] + CURL_OPTS + [url],
        capture_output=True
    )
    return result.stdout

def curl_download(url, dest_path):
    result = subprocess.run(
        ["curl"] + CURL_OPTS + ["-o", str(dest_path), url],
        capture_output=True
    )
    return result.returncode == 0

# ── Core logic ────────────────────────────────────────────────────────────────

def list_categories():
    html = curl_get(INDEX_URL).decode("utf-8", errors="replace")
    p = FolderParser()
    p.feed(html)
    return p.folders

def list_files_in_category(cat_name):
    url = BASE_URL + "index.php?dir=Schematics//" + urllib.parse.quote(cat_name)
    html = curl_get(url).decode("utf-8", errors="replace")
    p = FolderParser()
    p.feed(html)
    return p.files

def find_local_dir(cat_name):
    """Match EA category name to an existing local folder, or create it."""
    # Direct match
    direct = DEST_ROOT / cat_name
    if direct.exists():
        return direct
    # Case-insensitive match
    try:
        for d in DEST_ROOT.iterdir():
            if d.is_dir() and d.name != "workshop" and d.name.lower() == cat_name.lower():
                return d
    except Exception:
        pass
    # Create new
    direct.mkdir(parents=True, exist_ok=True)
    return direct

def download_file(rel_path, dest_path):
    """Download one file. Returns (dest_path, status)."""
    if dest_path.exists() and dest_path.stat().st_size > 1000:
        return dest_path, "skip"

    url = BASE_URL + urllib.parse.quote(rel_path, safe="/")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ok = curl_download(url, dest_path)
        if not ok:
            return dest_path, "err:curl"
        if dest_path.stat().st_size < 500:
            content = dest_path.read_bytes()
            if b"<html" in content[:100].lower():
                dest_path.unlink(missing_ok=True)
                return dest_path, "err:html_response"
        return dest_path, "ok"
    except Exception as e:
        return dest_path, f"err:{e}"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching category list…")
    categories = list_categories()
    print(f"Found {len(categories)} categories\n")

    tasks = []  # (rel_path, dest_path)

    for cat in categories:
        print(f"  Scanning: {cat}")
        try:
            files = list_files_in_category(cat)
        except Exception as e:
            print(f"    ERROR listing: {e}")
            continue

        local_dir = find_local_dir(cat)
        for rel in files:
            fname = os.path.basename(urllib.parse.unquote(rel))
            dest  = local_dir / fname
            tasks.append((rel, dest))

        time.sleep(0.2)

    print(f"\nTotal files to process: {len(tasks)}")
    already_done = sum(1 for _, d in tasks if d.exists() and d.stat().st_size > 1000)
    print(f"Already downloaded:     {already_done}")
    print(f"Need to fetch:          {len(tasks) - already_done}")
    print("\nDownloading (8 parallel workers)…\n")

    ok = skip = err = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(download_file, rel, dest): (rel, dest)
                   for rel, dest in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            dest_path, status = future.result()
            if status == "ok":
                ok += 1
                if ok <= 20 or ok % 50 == 0:
                    print(f"  [{i:>4}/{len(tasks)}] ✓  {dest_path.name}")
            elif status == "skip":
                skip += 1
            else:
                err += 1
                print(f"  [{i:>4}/{len(tasks)}] ✗  {dest_path.name}  ({status})")

    elapsed = time.time() - start
    print(f"\nFinished in {elapsed:.0f}s")
    print(f"  Downloaded: {ok}")
    print(f"  Skipped:    {skip} (already present)")
    print(f"  Errors:     {err}")

if __name__ == "__main__":
    main()
