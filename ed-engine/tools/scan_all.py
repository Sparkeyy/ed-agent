#!/usr/bin/env python3
"""Run vision extraction on all scan directories and merge into manifest.

Processes critters, constructions, forest, and events in sequence.
For critters (pre-named), extracts data but doesn't rename.
For constructions/forest/events (IMG_XXXX), classifies and renames.

Updates card_manifest.json with vision-extracted ability_text and flags
any discrepancies vs engine data.

Usage:
    python tools/scan_all.py [--ollama-host URL] [--start-from TYPE]
    python tools/scan_all.py --ollama-host http://localhost:11434
    python tools/scan_all.py --start-from construction  # skip critters
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TOOLS_DIR.parent
RIG_DIR = ENGINE_DIR.parent
UI_DIR = RIG_DIR / "ed-ui"
CARDS_OUTPUT = UI_DIR / "public" / "assets" / "cards"
SCANS_DIR = RIG_DIR / "docs" / "Everdell_Scans"
MANIFEST_PATH = TOOLS_DIR / "card_manifest.json"
VISION_CACHE = TOOLS_DIR / "vision_cache.json"

DEFAULT_HOST = "http://localhost:11434"

# --- Prompts ---

PROMPT_CRITTER_CONSTRUCTION = """\
You are analyzing a scan of an Everdell card. Extract data as JSON.

Identify:
- name: Card name in the center banner
- category: "critter" or "construction"
- card_type: Banner color — tan/brown="tan_traveler", green="green_production", red="red_destination", blue="blue_governance", purple="purple_prosperity"
- unique: true if subtitle says "UNIQUE", false if "COMMON"
- base_points: Number in gold VP circle (can be negative)
- cost: Count each resource icon on left side — twig (stick), resin (amber drop), pebble (grey stone), berry (red/purple berry)
- cost_type: "and" (pay all) for most cards. For critters only, if icons are visually separated with gap between groups, it's "or" (pay one option)
- paired_with: Paired card name at top (critter) or bottom-right (construction)
- ability_text: The rules text (not flavor text)

Return ONLY valid JSON:
{"name":"...","category":"...","card_type":"...","unique":true,"base_points":0,"cost":{"twig":0,"resin":0,"pebble":0,"berry":0},"cost_type":"and","paired_with":"...","ability_text":"..."}
"""

PROMPT_FOREST = """\
You are analyzing an Everdell forest location card. Extract as JSON:
- name: Location name
- effect: Effect text for when a worker is placed
- exclusive: true if single paw print (1 worker), false if multiple
- worker_spots: Number of paw prints visible

Return ONLY valid JSON:
{"name":"...","effect":"...","exclusive":true,"worker_spots":1}
"""

PROMPT_EVENT = """\
You are analyzing an Everdell event card. Extract as JSON:
- name: Event name
- type: "basic" if requires count of card types, "special" if requires specific named cards
- points: VP value in gold circle
- requirements: List of required card names (special) or condition description (basic)
- description: Full card text

Return ONLY valid JSON:
{"name":"...","type":"special","points":0,"requirements":["Card1","Card2"],"description":"..."}
"""


def encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def query_ollama(image_b64: str, prompt: str, host: str, timeout: int = 120) -> dict:
    url = f"{host}/api/generate"
    payload = json.dumps({
        "model": "minicpm-v:8b",
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "options": {"temperature": 0.1},
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"    ERROR: {e}", file=sys.stderr)
        return {}

    text = data.get("response", "")
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        print(f"    WARNING: No JSON in response: {text[:200]}", file=sys.stderr)
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        print(f"    WARNING: Bad JSON: {e}", file=sys.stderr)
        return {}


def kebab(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_cache() -> dict:
    if VISION_CACHE.exists():
        with open(VISION_CACHE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(VISION_CACHE, "w") as f:
        json.dump(cache, f, indent=2)


def process_critters(host: str, cache: dict) -> list[dict]:
    """Process pre-named critter scans."""
    scan_dir = SCANS_DIR / "critter_scans"
    out_dir = CARDS_OUTPUT / "critters"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for scan in sorted(scan_dir.glob("*.png")):
        cache_key = f"critter/{scan.name}"
        if cache_key in cache:
            print(f"  [cached] {scan.name}")
            results.append(cache[cache_key])
            continue

        print(f"  Scanning: {scan.name}")
        image_b64 = encode_image(scan)
        extracted = query_ollama(image_b64, PROMPT_CRITTER_CONSTRUCTION, host)

        if not extracted:
            print(f"    FAILED — skipping")
            continue

        # Copy to output (use engine-canonical name)
        name = extracted.get("name", "Unknown")
        rarity = "unique" if extracted.get("unique") else "common"
        filename = f"{rarity}_critter_{kebab(name)}.png"
        dest = out_dir / filename
        if not dest.exists():
            shutil.copy2(scan, dest)

        entry = {
            "source": scan.name,
            "extracted": extracted,
            "image_file": f"critters/{filename}",
        }
        results.append(entry)
        cache[cache_key] = entry
        save_cache(cache)
        time.sleep(1)

    return results


def process_constructions(host: str, cache: dict) -> list[dict]:
    """Process IMG_XXXX construction scans — classify and rename."""
    scan_dir = SCANS_DIR / "construction_scans"
    out_dir = CARDS_OUTPUT / "constructions"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for scan in sorted(scan_dir.glob("*.png")):
        cache_key = f"construction/{scan.name}"
        if cache_key in cache:
            print(f"  [cached] {scan.name}")
            results.append(cache[cache_key])
            continue

        print(f"  Scanning: {scan.name}")
        image_b64 = encode_image(scan)
        extracted = query_ollama(image_b64, PROMPT_CRITTER_CONSTRUCTION, host)

        if not extracted:
            print(f"    FAILED — skipping")
            continue

        name = extracted.get("name", "Unknown")
        rarity = "unique" if extracted.get("unique") else "common"
        filename = f"{rarity}_construction_{kebab(name)}.png"
        dest = out_dir / filename

        # Handle collision
        if dest.exists():
            n = 2
            while dest.exists():
                dest = out_dir / f"{rarity}_construction_{kebab(name)}-{n}.png"
                n += 1
            filename = dest.name

        shutil.copy2(scan, dest)
        print(f"    -> {filename} ({name})")

        entry = {
            "source": scan.name,
            "extracted": extracted,
            "image_file": f"constructions/{filename}",
        }
        results.append(entry)
        cache[cache_key] = entry
        save_cache(cache)
        time.sleep(1)

    return results


def process_forest(host: str, cache: dict) -> list[dict]:
    """Process forest location scans."""
    scan_dir = SCANS_DIR / "forest_scans"
    out_dir = CARDS_OUTPUT / "forest"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for scan in sorted(scan_dir.glob("*.png")):
        cache_key = f"forest/{scan.name}"
        if cache_key in cache:
            print(f"  [cached] {scan.name}")
            results.append(cache[cache_key])
            continue

        print(f"  Scanning: {scan.name}")
        image_b64 = encode_image(scan)
        extracted = query_ollama(image_b64, PROMPT_FOREST, host)

        if not extracted:
            print(f"    FAILED — skipping")
            continue

        name = extracted.get("name", "Unknown")
        filename = f"forest_{kebab(name)}.png"
        dest = out_dir / filename
        if dest.exists():
            n = 2
            while dest.exists():
                dest = out_dir / f"forest_{kebab(name)}-{n}.png"
                n += 1
            filename = dest.name

        shutil.copy2(scan, dest)
        print(f"    -> {filename} ({name})")

        entry = {
            "source": scan.name,
            "extracted": extracted,
            "image_file": f"forest/{filename}",
        }
        results.append(entry)
        cache[cache_key] = entry
        save_cache(cache)
        time.sleep(1)

    return results


def process_events(host: str, cache: dict) -> list[dict]:
    """Process event card scans."""
    scan_dir = SCANS_DIR / "special_events_scans"
    out_dir = CARDS_OUTPUT / "events"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for scan in sorted(scan_dir.glob("*.png")):
        cache_key = f"event/{scan.name}"
        if cache_key in cache:
            print(f"  [cached] {scan.name}")
            results.append(cache[cache_key])
            continue

        print(f"  Scanning: {scan.name}")
        image_b64 = encode_image(scan)
        extracted = query_ollama(image_b64, PROMPT_EVENT, host)

        if not extracted:
            print(f"    FAILED — skipping")
            continue

        name = extracted.get("name", "Unknown")
        filename = f"event_{kebab(name)}.png"
        dest = out_dir / filename
        if dest.exists():
            n = 2
            while dest.exists():
                dest = out_dir / f"event_{kebab(name)}-{n}.png"
                n += 1
            filename = dest.name

        shutil.copy2(scan, dest)
        print(f"    -> {filename} ({name})")

        entry = {
            "source": scan.name,
            "extracted": extracted,
            "image_file": f"events/{filename}",
        }
        results.append(entry)
        cache[cache_key] = entry
        save_cache(cache)
        time.sleep(1)

    return results


def merge_into_manifest(
    critter_results: list[dict],
    construction_results: list[dict],
    forest_results: list[dict],
    event_results: list[dict],
) -> None:
    """Merge vision results into the bootstrapped manifest."""
    if not MANIFEST_PATH.exists():
        print("ERROR: No manifest found. Run bootstrap_manifest.py first.", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    # Index existing cards by name
    cards_by_name: dict[str, dict] = {}
    for card in manifest.get("cards", []):
        cards_by_name[card["name"]] = card

    # Merge critter vision data
    for r in critter_results:
        ext = r["extracted"]
        name = ext.get("name", "")
        if name in cards_by_name:
            card = cards_by_name[name]
            card["vision_ability_text"] = ext.get("ability_text", "")
            card["vision_cost"] = ext.get("cost", {})
            card["vision_base_points"] = ext.get("base_points")
            card["vision_unique"] = ext.get("unique")
            card["vision_card_type"] = ext.get("card_type")
            card["vision_paired_with"] = ext.get("paired_with", "")
            card["source_scan"] = r["source"]
            if r.get("image_file"):
                card["image_file"] = r["image_file"]
        else:
            print(f"  WARNING: Vision found critter '{name}' not in engine")

    # Merge construction vision data
    for r in construction_results:
        ext = r["extracted"]
        name = ext.get("name", "")
        if name in cards_by_name:
            card = cards_by_name[name]
            card["vision_ability_text"] = ext.get("ability_text", "")
            card["vision_cost"] = ext.get("cost", {})
            card["vision_base_points"] = ext.get("base_points")
            card["vision_unique"] = ext.get("unique")
            card["vision_card_type"] = ext.get("card_type")
            card["vision_paired_with"] = ext.get("paired_with", "")
            card["source_scan"] = r["source"]
            if r.get("image_file"):
                card["image_file"] = r["image_file"]
            card["status"] = "pending"  # Needs human review
        else:
            # New card from vision — add it
            print(f"  NEW construction from vision: {name}")
            manifest["cards"].append({
                "name": name,
                "category": ext.get("category", "construction"),
                "card_type": ext.get("card_type", ""),
                "unique": ext.get("unique", False),
                "base_points": ext.get("base_points", 0),
                "cost": ext.get("cost", {"twig": 0, "resin": 0, "pebble": 0, "berry": 0}),
                "cost_type": ext.get("cost_type", "and"),
                "paired_with": [ext.get("paired_with", "")] if ext.get("paired_with") else [],
                "ability_text": ext.get("ability_text", ""),
                "copies_in_deck": None,
                "image_file": r.get("image_file", ""),
                "source_scan": r["source"],
                "status": "pending",
            })

    # Add/merge forest locations
    existing_forest = {loc["name"]: loc for loc in manifest.get("forest_locations", [])}
    for r in forest_results:
        ext = r["extracted"]
        name = ext.get("name", "Unknown")
        loc = {
            "name": name,
            "effect": ext.get("effect", ""),
            "exclusive": ext.get("exclusive", True),
            "worker_spots": ext.get("worker_spots", 1),
            "image_file": r.get("image_file", ""),
            "source_scan": r["source"],
            "status": "pending",
        }
        if name in existing_forest:
            existing_forest[name].update(loc)
        else:
            manifest.setdefault("forest_locations", []).append(loc)

    # Merge event vision data
    existing_events = {ev["name"]: ev for ev in manifest.get("events", [])}
    for r in event_results:
        ext = r["extracted"]
        name = ext.get("name", "Unknown")
        ev = {
            "name": name,
            "type": ext.get("type", "special"),
            "points": ext.get("points", 0),
            "requirements": ext.get("requirements", []),
            "description": ext.get("description", ""),
            "image_file": r.get("image_file", ""),
            "source_scan": r["source"],
            "status": "pending",
        }
        if name in existing_events:
            existing_events[name].update(ev)
        else:
            manifest.setdefault("events", []).append(ev)

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest updated: {MANIFEST_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama-host", default=DEFAULT_HOST)
    parser.add_argument("--start-from", choices=["critter", "construction", "forest", "event"])
    args = parser.parse_args()

    cache = load_cache()
    types = ["critter", "construction", "forest", "event"]
    if args.start_from:
        types = types[types.index(args.start_from):]

    critter_results = []
    construction_results = []
    forest_results = []
    event_results = []

    for t in types:
        print(f"\n=== Processing {t}s ===")
        if t == "critter":
            critter_results = process_critters(args.ollama_host, cache)
            print(f"  {len(critter_results)} critters processed")
        elif t == "construction":
            construction_results = process_constructions(args.ollama_host, cache)
            print(f"  {len(construction_results)} constructions processed")
        elif t == "forest":
            forest_results = process_forest(args.ollama_host, cache)
            print(f"  {len(forest_results)} forest locations processed")
        elif t == "event":
            event_results = process_events(args.ollama_host, cache)
            print(f"  {len(event_results)} events processed")

    merge_into_manifest(critter_results, construction_results, forest_results, event_results)


if __name__ == "__main__":
    main()
