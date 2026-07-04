import os
import json
import zipfile
from pathlib import Path

pipeline_dir = Path(__file__).resolve().parent
manifest_path = pipeline_dir / "manifest.json"
extractions_dir = pipeline_dir / "extractions"
icloud_docs = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
archive_path = icloud_docs / "schematics_dataset.zip"

with open(manifest_path, "r") as f:
    manifest = json.load(f)

# Collect all non-copyrighted entries that have an extraction
to_package = []
for path, data in manifest.get("entries", {}).items():
    if "OOP Japanese Electronics Book" in path:
        continue
    
    slug = data["slug"]
    json_file = extractions_dir / f"{slug}.json"
    if json_file.exists():
        to_package.append((path, json_file, data))

# Create a zip archive
print("Creating archive...")
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for orig_path, json_file, data in to_package:
        # Save JSON
        zipf.write(json_file, f"dataset/json/{json_file.name}")
        # Save original image
        if os.path.exists(orig_path):
            img_name = os.path.basename(orig_path)
            zipf.write(orig_path, f"dataset/images/{img_name}")
            
print(f"Packaged {len(to_package)} schematics into {archive_path}")
