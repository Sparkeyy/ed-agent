#!/usr/bin/env python3
"""Card scan extraction pipeline.

Processes raw card scan images using Ollama vision model (minicpm-v:8b) to:
1. Classify each card (critter/construction/forest/event)
2. Extract structured data (name, cost, VP, abilities, etc.)
3. Auto-rename files to convention: {rarity}_{type}_{kebab-name}.png
4. Move to correct category directory
5. Write card_manifest.json

Usage:
    python tools/scan_extract.py /path/to/scans/ [--type critter|construction|forest|event]
    python tools/scan_extract.py /path/to/scans/ --ollama-host http://192.168.0.14:11434

All scans are expected to be 1560x2160 PNG. No cropping needed.
Stdlib only — no pip dependencies.
"""

from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Resolve paths relative to this script
TOOLS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TOOLS_DIR.parent
RIG_DIR = ENGINE_DIR.parent
UI_DIR = RIG_DIR / "ed-ui"
CARDS_OUTPUT_DIR = UI_DIR / "public" / "assets" / "cards"
MANIFEST_PATH = TOOLS_DIR / "card_manifest.json"

CATEGORY_DIRS = {
    "critter": CARDS_OUTPUT_DIR / "critters",
    "construction": CARDS_OUTPUT_DIR / "constructions",
    "forest": CARDS_OUTPUT_DIR / "forest",
    "event": CARDS_OUTPUT_DIR / "events",
}

DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# Card counts from physical inventory (card_counts.csv)
CARD_COUNTS: dict[str, int] = {
    "Fool": 2, "Bard": 2, "Postal Pigeon": 3, "Monk": 2, "Shepherd": 2,
    "Shopkeeper": 3, "Historian": 3, "Innkeeper": 3, "Undertaker": 2,
    "Barge Toad": 3, "Wanderer": 3, "Miner Mole": 3, "Peddler": 3,
    "Ranger": 2, "Judge": 2, "Architect": 2, "Teacher": 3, "Chip Sweep": 3,
    "Woodcarver": 3, "Harvester": 4, "Gatherer": 4, "Doctor": 2,
    "Queen": 2, "King": 2,
    "Ever Tree": 2, "Palace": 2, "Castle": 2, "Theater": 2,
    "University": 2, "Fair Grounds": 3, "Courthouse": 2, "Lookout": 2,
    "Inn": 3, "School": 2, "Mine": 3, "Storehouse": 3, "Post Office": 3,
    "Twig Barge": 3, "Resin Refinery": 3, "Monastery": 2, "General Store": 3,
    "Crane": 3, "Chapel": 2, "Farm": 8, "Dungeon": 2, "Clock Tower": 3,
    "Cemetery": 2, "Ruins": 3,
}

# ---------------------------------------------------------------------------
# Vision prompts — one per card type
# ---------------------------------------------------------------------------

PROMPT_CRITTER_CONSTRUCTION = """\
You are analyzing a scan of an Everdell card game card. Extract the following data as JSON.

Look carefully at the card and identify:
- **name**: The card name in the center banner
- **category**: "critter" or "construction" (critters have animal art, constructions have building art)
- **card_type**: Determined by the color of the banner/border:
  - tan/brown = "tan_traveler"
  - green = "green_production"
  - red = "red_destination"
  - blue = "blue_governance"
  - purple = "purple_prosperity"
- **unique**: true if the subtitle says "UNIQUE", false if "COMMON"
- **base_points**: The number in the gold VP circle (can be negative like -2 for Fool)
- **cost**: Count each resource icon on the left side:
  - twig (stick/branch icon)
  - resin (amber drop icon)
  - pebble (grey stone icon)
  - berry (red/purple berry icon)
- **cost_type**: For critters, if cost icons are visually separated with a gap between groups, it's "or" (pay one option). For constructions, costs are always "and" (pay all). Most cards have "and" costs.
- **paired_with**: The paired card name shown at top (critter) or bottom-right corner (construction). If dual pairing (like "HARVESTER/GATHERER"), list both separated by comma.
- **ability_text**: The rules text on the card (not flavor text)
- **copies_in_deck**: null (not visible on card)

Return ONLY valid JSON, no markdown formatting:
{"name": "...", "category": "...", "card_type": "...", "unique": true/false, "base_points": 0, "cost": {"twig": 0, "resin": 0, "pebble": 0, "berry": 0}, "cost_type": "and", "paired_with": ["..."], "ability_text": "...", "copies_in_deck": null}
"""

PROMPT_FOREST = """\
You are analyzing a scan of an Everdell forest location card. Extract the following data as JSON.

Look carefully at the card:
- **name**: The location name
- **effect**: The effect text describing what happens when a worker is placed here
- **exclusive**: true if only 1 worker can be placed here (single paw print), false if multiple

Return ONLY valid JSON, no markdown formatting:
{"name": "...", "effect": "...", "exclusive": true/false}
"""

PROMPT_EVENT = """\
You are analyzing a scan of an Everdell event card. Extract the following data as JSON.

Look carefully at the card:
- **name**: The event name
- **type**: "basic" if it requires a count of card types (e.g., "3 Governance cards"), "special" if it requires specific named cards
- **points**: The VP value in the gold circle
- **requirements**: For basic events, describe the condition. For special events, list the required card names.
- **description**: The full text on the card

Return ONLY valid JSON, no markdown formatting:
{"name": "...", "type": "basic"/"special", "points": 0, "requirements": ["..."], "description": "..."}
"""


def encode_image(path: Path) -> str:
    """Base64-encode an image file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def query_ollama(
    image_b64: str,
    prompt: str,
    host: str = DEFAULT_OLLAMA_HOST,
    model: str = "minicpm-v:8b",
    timeout: int = 120,
) -> dict:
    """Send image + prompt to Ollama vision model, return parsed JSON."""
    url = f"{host}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "options": {"temperature": 0.1},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"  ERROR: Ollama request failed: {e}", file=sys.stderr)
        return {}

    response_text = data.get("response", "")

    # Try to extract JSON from response (may have markdown fences)
    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if not json_match:
        print(f"  WARNING: No JSON found in response: {response_text[:200]}", file=sys.stderr)
        return {}

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"  WARNING: Invalid JSON in response: {e}", file=sys.stderr)
        print(f"  Raw: {json_match.group()[:300]}", file=sys.stderr)
        return {}


def to_kebab(name: str) -> str:
    """Convert card name to kebab-case: 'Postal Pigeon' -> 'postal-pigeon'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build_filename(extracted: dict, category: str) -> str:
    """Build canonical filename from extracted data."""
    name = extracted.get("name", "unknown")
    kebab = to_kebab(name)

    if category in ("critter", "construction"):
        rarity = "unique" if extracted.get("unique") else "common"
        return f"{rarity}_{category}_{kebab}.png"
    elif category == "forest":
        return f"forest_{kebab}.png"
    elif category == "event":
        return f"event_{kebab}.png"
    return f"unknown_{kebab}.png"


def resolve_collision(dest: Path) -> Path:
    """If dest exists, append -2, -3, etc."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    n = 2
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def get_prompt_for_type(card_type: str | None) -> str:
    """Return the appropriate vision prompt."""
    if card_type == "forest":
        return PROMPT_FOREST
    if card_type == "event":
        return PROMPT_EVENT
    return PROMPT_CRITTER_CONSTRUCTION


def parse_prenamed_critter(scan_path: Path) -> dict | None:
    """Parse card info from a pre-named critter file like common_critter_postal-pigeon.png."""
    name = scan_path.stem  # e.g. "common_critter_postal-pigeon"
    parts = name.split("_", 2)
    # Handle both common_critter_name and common_critter-name (inconsistent separators)
    if len(parts) < 3:
        # Try split with hyphen after critter
        match = re.match(r"(common|unique)_critter[_-](.+)", name)
        if not match:
            return None
        rarity = match.group(1)
        kebab_name = match.group(2)
    else:
        rarity = parts[0]
        kebab_name = parts[2]

    # Convert kebab to title case: "postal-pigeon" -> "Postal Pigeon"
    card_name = " ".join(w.capitalize() for w in kebab_name.split("-"))

    return {
        "name": card_name,
        "category": "critter",
        "unique": rarity == "unique",
    }


def process_scan(
    scan_path: Path,
    card_type: str | None,
    host: str,
    dry_run: bool = False,
    skip_vision: bool = False,
) -> dict | None:
    """Process a single scan image. Returns manifest entry or None on failure."""
    print(f"  Processing: {scan_path.name}")

    # Check if this is a pre-named critter scan
    prenamed = parse_prenamed_critter(scan_path)
    if prenamed and (card_type is None or card_type == "critter"):
        skip_vision = True
        # For pre-named critters, we still need vision for detailed fields
        # but we know the name, category, and uniqueness already

    if skip_vision and prenamed:
        # Use filename-derived data, still call vision for cost/ability/etc.
        image_b64 = encode_image(scan_path)
        prompt = get_prompt_for_type("critter")
        extracted = query_ollama(image_b64, prompt, host=host)
        if extracted:
            # Override with known-good data from filename
            extracted["name"] = prenamed["name"]
            extracted["category"] = "critter"
            extracted["unique"] = prenamed["unique"]
        else:
            # Vision failed — use filename data only
            extracted = prenamed
    else:
        image_b64 = encode_image(scan_path)
        prompt = get_prompt_for_type(card_type)
        extracted = query_ollama(image_b64, prompt, host=host)

    if not extracted:
        print(f"  SKIP: No data extracted from {scan_path.name}")
        return None

    # Determine category
    category = card_type
    if category is None:
        category = extracted.get("category", "unknown")
    if category not in CATEGORY_DIRS:
        print(f"  WARNING: Unknown category '{category}' for {scan_path.name}")
        return None

    # Build filename and destination
    new_filename = build_filename(extracted, category)
    dest_dir = CATEGORY_DIRS[category]
    dest_path = resolve_collision(dest_dir / new_filename)

    rel_path = dest_path.relative_to(CARDS_OUTPUT_DIR)

    print(f"    Name: {extracted.get('name', '?')}")
    print(f"    Category: {category}")
    print(f"    Rename: {scan_path.name} -> {dest_path.name}")
    print(f"    Dest: {rel_path}")

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(scan_path, dest_path)

    # Build manifest entry
    if category in ("critter", "construction"):
        paired = extracted.get("paired_with", [])
        if isinstance(paired, str):
            paired = [p.strip() for p in paired.split(",") if p.strip()]

        cost = extracted.get("cost", {})
        entry = {
            "name": extracted.get("name", "Unknown"),
            "category": category,
            "card_type": extracted.get("card_type", "unknown"),
            "unique": extracted.get("unique", False),
            "base_points": extracted.get("base_points", 0),
            "cost": {
                "twig": cost.get("twig", 0),
                "resin": cost.get("resin", 0),
                "pebble": cost.get("pebble", 0),
                "berry": cost.get("berry", 0),
            },
            "cost_type": extracted.get("cost_type", "and"),
            "paired_with": paired,
            "ability_text": extracted.get("ability_text", ""),
            "copies_in_deck": CARD_COUNTS.get(extracted.get("name", ""), None),
            "image_file": str(rel_path),
            "source_scan": scan_path.name,
            "status": "pending",
        }
        return entry

    elif category == "forest":
        entry = {
            "name": extracted.get("name", "Unknown"),
            "effect": extracted.get("effect", ""),
            "exclusive": extracted.get("exclusive", True),
            "image_file": str(rel_path),
            "source_scan": scan_path.name,
            "status": "pending",
        }
        return entry

    elif category == "event":
        reqs = extracted.get("requirements", [])
        if isinstance(reqs, str):
            reqs = [reqs]
        entry = {
            "name": extracted.get("name", "Unknown"),
            "type": extracted.get("type", "special"),
            "points": extracted.get("points", 0),
            "requirements": reqs,
            "description": extracted.get("description", ""),
            "image_file": str(rel_path),
            "source_scan": scan_path.name,
            "status": "pending",
        }
        return entry

    return None


def load_manifest() -> dict:
    """Load existing manifest or create empty one."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {"version": 1, "cards": [], "forest_locations": [], "events": []}


def save_manifest(manifest: dict) -> None:
    """Write manifest to disk."""
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written: {MANIFEST_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract card data from scans using Ollama vision")
    parser.add_argument("scan_dir", help="Directory containing card scan images")
    parser.add_argument(
        "--type",
        choices=["critter", "construction", "forest", "event"],
        default=None,
        help="Force card type (auto-detected if omitted)",
    )
    parser.add_argument(
        "--ollama-host",
        default=DEFAULT_OLLAMA_HOST,
        help=f"Ollama server URL (default: {DEFAULT_OLLAMA_HOST})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Extract but don't move files")
    parser.add_argument("--append", action="store_true", help="Append to existing manifest")
    args = parser.parse_args()

    scan_dir = Path(args.scan_dir)
    if not scan_dir.is_dir():
        print(f"ERROR: {scan_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find all image files
    patterns = ["*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg", "*.JPEG"]
    scan_files: list[Path] = []
    for pattern in patterns:
        scan_files.extend(scan_dir.glob(pattern))
    scan_files.sort()

    if not scan_files:
        print(f"No image files found in {scan_dir}")
        sys.exit(1)

    print(f"Found {len(scan_files)} scan(s) in {scan_dir}")
    print(f"Ollama host: {args.ollama_host}")
    print(f"Card type: {args.type or 'auto-detect'}")
    print(f"Output: {CARDS_OUTPUT_DIR}")
    print()

    # Ensure output dirs exist
    for d in CATEGORY_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

    # Load or create manifest
    if args.append:
        manifest = load_manifest()
    else:
        manifest = {"version": 1, "cards": [], "forest_locations": [], "events": []}

    success = 0
    errors = 0

    for scan_path in scan_files:
        entry = process_scan(scan_path, args.type, args.ollama_host, dry_run=args.dry_run)
        if entry is None:
            errors += 1
            continue

        # Add to manifest
        category = entry.get("category") or args.type
        if category in ("critter", "construction"):
            manifest["cards"].append(entry)
        elif category == "forest":
            manifest["forest_locations"].append(entry)
        elif category == "event":
            manifest["events"].append(entry)

        success += 1
        # Be polite to Ollama
        time.sleep(1)

    # Save manifest
    if not args.dry_run:
        save_manifest(manifest)

    print(f"\nDone: {success} processed, {errors} errors")


if __name__ == "__main__":
    main()
