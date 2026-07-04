import json
from pathlib import Path

MANIFEST_PATH = Path("manifest.json")

TIER_1_KEYWORDS = [
    "tube screamer", "ts9", "ts808", "ts-9", "ts-808", "rat", "klon", "centaur", 
    "fuzz face", "big muff", "phase 90", "dynacomp", "dyna comp", "tone bender", 
    "guv'nor", "bluesbreaker", "ds-1", "ce-2", "sd-1", "mt-2"
]

TIER_2_KEYWORDS = [
    "boss", "ibanez", "mxr", "dod", "ehx", "electro harmonix", "fuzz", 
    "chorus", "delay", "wah", "crybaby", "dunlop", "compressor", "overdrive", "distortion"
]

def get_priority(name):
    lower_name = name.lower()
    for kw in TIER_1_KEYWORDS:
        if kw in lower_name:
            return 1
    for kw in TIER_2_KEYWORDS:
        if kw in lower_name:
            return 5
    return 10

def main():
    with open(MANIFEST_PATH, "r") as f:
        data = json.load(f)
    
    entries = data.get("entries", {})
    updates = {1: 0, 5: 0, 10: 0}
    
    for path, v in entries.items():
        if v["state"] == "pending":
            prio = get_priority(v["name"])
            v["prio"] = prio
            updates[prio] += 1
            
    with open(MANIFEST_PATH, "w") as f:
        json.dump(data, f, indent=1)
        
    print(f"Ranking complete!")
    print(f"Tier 1 (Legendary): {updates[1]}")
    print(f"Tier 2 (Classic/Common): {updates[5]}")
    print(f"Tier 3 (Other): {updates[10]}")

if __name__ == "__main__":
    main()
