"""Indexes the existing schematic library into the database.

Walks all directories in the schematics root (excluding workshop/),
creates a row in the schematics table for each image/PDF file.

Idempotent: uses INSERT OR IGNORE on the unique constraint.
"""

import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from api.models.schematic import Schematic

CATEGORY_MAP = {
    "ADSR Gen and Evenlope Gen": "envelope",
    "Amplifiers and VCAs": "amplifier",
    "Buffers Switchers Mixers and Routers": "utility",
    "Chorus": "chorus",
    "Circuit Bending and Modifications": "modification",
    "Compressors Gates and Limiters": "compressor",
    "Delay Echo and Samplers": "delay",
    "Distortion Boost and Overdrive": "distortion",
    "Filters Wahs and VCFs": "filter",
    "Flangers": "flanger",
    "Full Synths Drum Synths and Misc Synth": "synth",
    "Fuzz and Fuzzy Noisemakers": "fuzz",
    "Guitar Synth and Misc Signal Shapers": "synth",
    "MIDI": "midi",
    "Miscellaneous": "misc",
    "OOP Japanese Electronics Book": "reference",
    "Oscillators LFOs and Signal Generators": "oscillator",
    "Phasers": "phaser",
    "Power Supplies and Other Useful Stuff": "power",
    "Reverb": "reverb",
    "Ring Modulators and Frequency Shifters": "ring_mod",
    "Tone Control and EQs": "eq",
    "Tremolos and Panners": "tremolo",
    "Vibrato and Pitch Shift": "pitch",
}

VALID_EXTENSIONS = {".gif", ".pdf", ".png", ".jpg", ".jpeg"}


def index_schematics(db: Session, schematics_root: str) -> int:
    """Scan the schematics library and insert/update rows. Returns count of new entries."""
    root = Path(schematics_root)
    count = 0

    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name == "workshop" or entry.name.startswith("."):
            continue

        category_folder = entry.name
        effect_type = CATEGORY_MAP.get(category_folder)

        for file_entry in sorted(entry.iterdir()):
            if not file_entry.is_file():
                continue
            ext = file_entry.suffix.lower()
            if ext not in VALID_EXTENSIONS:
                continue

            file_name = file_entry.name
            file_path = f"{category_folder}/{file_name}"
            file_size = file_entry.stat().st_size

            # Generate tags from filename
            name_no_ext = file_entry.stem
            tags = [t.strip().lower() for t in name_no_ext.replace("-", " ").replace("_", " ").split() if len(t.strip()) > 1]
            if effect_type:
                tags.append(effect_type)

            # Check if already exists
            existing = db.query(Schematic).filter_by(
                category_folder=category_folder, file_name=file_name
            ).first()

            if existing:
                continue

            schematic = Schematic(
                category_folder=category_folder,
                file_name=file_name,
                file_path=file_path,
                file_type=ext.lstrip("."),
                file_size=file_size,
                effect_type=effect_type,
                tags=json.dumps(tags),
            )
            db.add(schematic)
            count += 1

    db.commit()
    return count
