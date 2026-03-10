#!/usr/bin/env python3
"""Bootstrap card_manifest.json from engine data + pre-named scan files.

For critters (pre-named files), generates manifest entries directly from
engine card definitions — no vision model needed. Copies files to the
correct output directory.

For constructions/forest/events, only creates the manifest structure
(to be filled by scan_extract.py with vision).

Usage:
    python tools/bootstrap_manifest.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TOOLS_DIR.parent
RIG_DIR = ENGINE_DIR.parent
UI_DIR = RIG_DIR / "ed-ui"
CARDS_OUTPUT = UI_DIR / "public" / "assets" / "cards"
SCANS_DIR = RIG_DIR / "docs" / "Everdell_Scans"
MANIFEST_PATH = TOOLS_DIR / "card_manifest.json"

sys.path.insert(0, str(ENGINE_DIR))

from ed_engine.cards import CardRegistry  # noqa: E402
from ed_engine.cards.critters import *  # noqa: F401,F403
from ed_engine.cards.constructions import *  # noqa: F401,F403
from ed_engine.engine.events import BASIC_EVENT_DEFS, SPECIAL_EVENT_DEFS  # noqa: E402
from ed_engine.models.enums import CardCategory  # noqa: E402

# Card counts from physical inventory
CARD_COUNTS = {
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

# Map card-info.ts abilities (from engine docstrings)
ABILITY_TEXT = {
    "Architect": "+1 VP per leftover resin and pebble, up to 6.",
    "King": "+1 VP per basic Event claimed, +2 VP per special Event.",
    "Gatherer": "+3 VP if paired Harvester is in your city. Shares city space with Harvester.",
    "Barge Toad": "Gain 2 twigs per Farm in your city.",
    "Chip Sweep": "Activate any 1 green Production card in your city.",
    "Doctor": "Pay up to 3 berries, gain 1 VP per berry paid.",
    "Harvester": "If you have a Farm, gain 1 of any resource.",
    "Miner Mole": "Copy 1 green Production card from an opponent's city.",
    "Monk": "Give up to 2 berries to an opponent, gain 2 VP per berry given.",
    "Peddler": "Trade up to 2 resources for 2 other resources.",
    "Teacher": "Draw 2 cards, keep 1, give the other to an opponent.",
    "Woodcarver": "Pay up to 3 twigs, gain 1 VP per twig paid.",
    "Queen": "Play any card worth 3 VP or less from hand or Meadow for free.",
    "Historian": "Draw 1 card after playing any card.",
    "Innkeeper": "Discard to decrease a Critter's cost by 3 berries.",
    "Judge": "When playing a card, replace 1 resource in cost with 1 other resource.",
    "Shopkeeper": "Gain 1 berry after playing a Critter.",
    "Bard": "Discard up to 5 cards, gain 1 VP per card discarded.",
    "Fool": "Played into an opponent's city. Worth -2 VP for them.",
    "Postal Pigeon": "Reveal 2 cards from deck, play 1 worth 3 VP or less for free.",
    "Ranger": "Move 1 of your deployed workers to a new location.",
    "Shepherd": "Gain 3 berries, gain 1 VP per VP token on your Chapel.",
    "Undertaker": "Discard 3 Meadow cards, then draw 1 card from deck.",
    "Wanderer": "Draw 3 cards. Does not occupy a city space.",
    "Castle": "+1 VP per Common Construction in your city.",
    "Ever Tree": "+1 VP per Prosperity (purple) card in your city.",
    "Palace": "+1 VP per Unique Construction in your city.",
    "School": "+1 VP per Common Critter in your city.",
    "Theater": "+1 VP per Unique Critter in your city.",
    "Fair Grounds": "Draw 2 cards.",
    "Farm": "Gain 1 berry.",
    "General Store": "Gain 1 berry, or 2 berries if you have a Farm.",
    "Mine": "Gain 1 pebble.",
    "Resin Refinery": "Gain 1 resin.",
    "Storehouse": "Gain 3 twigs, 2 resin, 1 pebble, or 2 berries (choose 1).",
    "Twig Barge": "Gain 2 twigs.",
    "Cemetery": "Reveal 4 cards from deck/discard, play 1 for free.",
    "Chapel": "Place 1 VP token on Chapel, draw 2 cards per VP token.",
    "Inn": "Play a Critter or Construction from the Meadow for 3 less of any resource.",
    "Lookout": "Copy the effect of any basic or Forest location.",
    "Monastery": "Give 2 resources to an opponent, gain 4 VP. Worker stays permanently.",
    "Post Office": "Give an opponent 2 cards, discard any from hand, draw to hand limit.",
    "University": "Discard 1 card from city, get its cost back, +1 any resource, +1 VP. Worker stays.",
    "Clock Tower": "3 VP tokens; before Prepare for Season, remove 1 to activate a location.",
    "Courthouse": "Gain 1 twig, resin, or pebble when playing a Construction.",
    "Crane": "Discard to decrease a Construction's cost by 3 of any resource.",
    "Dungeon": "Place a Critter from your city beneath to reduce played card cost by 3.",
    "Ruins": "Discard a Construction from city, gain its cost back, draw 2 cards.",
}


def kebab(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def find_critter_scan(name: str) -> Path | None:
    """Find a pre-named critter scan file."""
    scan_dir = SCANS_DIR / "critter_scans"
    if not scan_dir.exists():
        return None
    k = kebab(name)
    # Try various naming patterns
    for pattern in [f"*critter_{k}.png", f"*critter-{k}.png", f"*critter_{k}.*", f"*critter-{k}.*"]:
        matches = list(scan_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def main() -> None:
    registry = CardRegistry.all()
    manifest = {"version": 1, "cards": [], "forest_locations": [], "events": []}

    critter_out = CARDS_OUTPUT / "critters"
    construction_out = CARDS_OUTPUT / "constructions"
    critter_out.mkdir(parents=True, exist_ok=True)
    construction_out.mkdir(parents=True, exist_ok=True)

    critter_count = 0
    construction_count = 0

    for name, card_cls in sorted(registry.items()):
        card = card_cls()
        rarity = "unique" if card.unique else "common"
        cat = card.category.value  # "critter" or "construction"
        k = kebab(name)
        filename = f"{rarity}_{cat}_{k}.png"

        if cat == "critter":
            rel_path = f"critters/{filename}"
            scan = find_critter_scan(name)
            source_scan = scan.name if scan else ""
            if scan:
                dest = critter_out / filename
                if not dest.exists():
                    shutil.copy2(scan, dest)
                    print(f"  Copied: {scan.name} -> {rel_path}")
                else:
                    print(f"  Exists: {rel_path}")
                critter_count += 1
        else:
            rel_path = f"constructions/{filename}"
            source_scan = ""  # Will be filled by scan_extract.py
            construction_count += 1

        # Get paired_with as list
        paired = []
        if card.paired_with:
            paired = [card.paired_with]
        # Dual pairing: Farm also pairs with Gatherer
        if name == "Farm":
            paired = ["Harvester", "Gatherer"]

        entry = {
            "name": name,
            "category": cat,
            "card_type": card.card_type.value,
            "unique": card.unique,
            "base_points": card.base_points,
            "cost": {
                "twig": card.cost.twig,
                "resin": card.cost.resin,
                "pebble": card.cost.pebble,
                "berry": card.cost.berry,
            },
            "cost_type": "and",
            "paired_with": paired,
            "ability_text": ABILITY_TEXT.get(name, ""),
            "copies_in_deck": CARD_COUNTS.get(name),
            "image_file": rel_path,
            "source_scan": source_scan,
            "status": "reviewed" if cat == "critter" else "pending",
        }
        manifest["cards"].append(entry)

    # Add basic events
    for ev in BASIC_EVENT_DEFS:
        manifest["events"].append({
            "name": ev["name"],
            "type": "basic",
            "points": ev["points"],
            "requirements": [ev["description"]],
            "description": ev["description"],
            "image_file": "",
            "source_scan": "",
            "status": "reviewed",
        })

    # Add special events
    for ev in SPECIAL_EVENT_DEFS:
        manifest["events"].append({
            "name": ev["name"],
            "type": "special",
            "points": ev["points"],
            "requirements": ev["required_cards"],
            "description": ev["description"],
            "image_file": "",
            "source_scan": "",
            "status": "reviewed",
        })

    # Save
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest written: {MANIFEST_PATH}")
    print(f"  {critter_count} critters (from engine + pre-named scans)")
    print(f"  {construction_count} constructions (engine data, scans pending vision)")
    print(f"  {len(manifest['events'])} events (from engine)")
    print(f"  Total cards: {len(manifest['cards'])}")


if __name__ == "__main__":
    main()
