#!/usr/bin/env python3
"""Reconcile card_manifest.json against engine card definitions.

Compares extracted scan data field-by-field with the Python card registry.
Outputs a diff table showing OK, MISMATCH, MISSING, and EXTRA entries.

Usage:
    python tools/reconcile.py
    python tools/reconcile.py --manifest path/to/card_manifest.json
    python tools/reconcile.py --json  # Output as JSON instead of table
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add engine to path
TOOLS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(ENGINE_DIR))

from ed_engine.cards import CardRegistry, build_deck  # noqa: E402
from ed_engine.cards.critters import *  # noqa: F401,F403 — force registration
from ed_engine.cards.constructions import *  # noqa: F401,F403
from ed_engine.engine.events import BASIC_EVENT_DEFS, SPECIAL_EVENT_DEFS  # noqa: E402

MANIFEST_PATH = TOOLS_DIR / "card_manifest.json"


def load_manifest(path: Path) -> dict:
    """Load the card manifest."""
    with open(path) as f:
        return json.load(f)


def compare_cards(manifest: dict) -> list[dict]:
    """Compare manifest cards against engine registry."""
    registry = CardRegistry.all()
    results: list[dict] = []

    # Index manifest cards by name
    manifest_cards = {c["name"]: c for c in manifest.get("cards", [])}

    # Check each engine card against manifest
    for name, card_cls in sorted(registry.items()):
        card = card_cls()
        m = manifest_cards.get(name)

        if m is None:
            results.append({
                "card": name,
                "field": "*",
                "engine": "(registered)",
                "manifest": "(missing)",
                "status": "MISSING",
            })
            continue

        # Compare fields
        field_checks = [
            ("category", card.category.value, m.get("category")),
            ("card_type", card.card_type.value, m.get("card_type")),
            ("unique", card.unique, m.get("unique")),
            ("base_points", card.base_points, m.get("base_points")),
            ("cost.twig", card.cost.twig, m.get("cost", {}).get("twig", 0)),
            ("cost.resin", card.cost.resin, m.get("cost", {}).get("resin", 0)),
            ("cost.pebble", card.cost.pebble, m.get("cost", {}).get("pebble", 0)),
            ("cost.berry", card.cost.berry, m.get("cost", {}).get("berry", 0)),
            ("copies_in_deck", card.copies_in_deck, m.get("copies_in_deck")),
        ]

        # Paired_with comparison (engine is str|None, manifest is list)
        engine_paired = [card.paired_with] if card.paired_with else []
        manifest_paired = m.get("paired_with", []) or []
        if isinstance(manifest_paired, str):
            manifest_paired = [manifest_paired]
        field_checks.append(("paired_with", engine_paired, manifest_paired))

        for field, engine_val, manifest_val in field_checks:
            if manifest_val is None and field == "copies_in_deck":
                status = "MISSING"
            elif engine_val == manifest_val:
                status = "OK"
            else:
                status = "MISMATCH"

            results.append({
                "card": name,
                "field": field,
                "engine": str(engine_val),
                "manifest": str(manifest_val),
                "status": status,
            })

    # Check for EXTRA cards in manifest (not in engine)
    for name in sorted(manifest_cards.keys()):
        if name not in registry:
            results.append({
                "card": name,
                "field": "*",
                "engine": "(not registered)",
                "manifest": "(in manifest)",
                "status": "EXTRA",
            })

    return results


def compare_events(manifest: dict) -> list[dict]:
    """Compare manifest events against engine event definitions."""
    results: list[dict] = []

    # Index engine events by name
    engine_basic = {e["name"]: e for e in BASIC_EVENT_DEFS}
    engine_special = {e["name"]: e for e in SPECIAL_EVENT_DEFS}

    # Check manifest events
    for ev in manifest.get("events", []):
        name = ev["name"]
        ev_type = ev.get("type", "special")

        if ev_type == "basic":
            engine_ev = engine_basic.get(name)
        else:
            engine_ev = engine_special.get(name)

        if engine_ev is None:
            results.append({
                "card": f"[Event] {name}",
                "field": "*",
                "engine": "(not defined)",
                "manifest": f"type={ev_type}, pts={ev.get('points')}",
                "status": "EXTRA",
            })
            continue

        # Compare points
        engine_pts = engine_ev.get("points", 0)
        manifest_pts = ev.get("points", 0)
        results.append({
            "card": f"[Event] {name}",
            "field": "points",
            "engine": str(engine_pts),
            "manifest": str(manifest_pts),
            "status": "OK" if engine_pts == manifest_pts else "MISMATCH",
        })

        # Compare required_cards for special events
        if ev_type == "special":
            engine_reqs = sorted(engine_ev.get("required_cards", []))
            manifest_reqs = sorted(ev.get("requirements", []))
            results.append({
                "card": f"[Event] {name}",
                "field": "required_cards",
                "engine": str(engine_reqs),
                "manifest": str(manifest_reqs),
                "status": "OK" if engine_reqs == manifest_reqs else "MISMATCH",
            })

    # Check for engine events missing from manifest
    manifest_event_names = {ev["name"] for ev in manifest.get("events", [])}
    for name in sorted(set(engine_basic.keys()) | set(engine_special.keys())):
        if name not in manifest_event_names:
            results.append({
                "card": f"[Event] {name}",
                "field": "*",
                "engine": "(defined)",
                "manifest": "(missing)",
                "status": "MISSING",
            })

    return results


def print_table(results: list[dict], show_ok: bool = False) -> None:
    """Print results as a formatted table."""
    filtered = results if show_ok else [r for r in results if r["status"] != "OK"]

    if not filtered:
        print("All fields match! No mismatches found.")
        return

    # Column widths
    w_card = max(len(r["card"]) for r in filtered)
    w_field = max(len(r["field"]) for r in filtered)
    w_engine = max(len(r["engine"]) for r in filtered)
    w_manifest = max(len(r["manifest"]) for r in filtered)

    header = f"{'Card':<{w_card}}  {'Field':<{w_field}}  {'Engine':<{w_engine}}  {'Manifest':<{w_manifest}}  Status"
    print(header)
    print("-" * len(header))

    for r in filtered:
        marker = ""
        if r["status"] == "MISMATCH":
            marker = " <--"
        elif r["status"] == "MISSING":
            marker = " ?"
        elif r["status"] == "EXTRA":
            marker = " +"

        print(
            f"{r['card']:<{w_card}}  {r['field']:<{w_field}}  "
            f"{r['engine']:<{w_engine}}  {r['manifest']:<{w_manifest}}  "
            f"{r['status']}{marker}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile card manifest against engine")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Path to card_manifest.json")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--show-ok", action="store_true", help="Include OK results in output")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}", file=sys.stderr)
        print("Run scan_extract.py first to generate the manifest.", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(manifest_path)
    print(f"Manifest: {manifest_path}")
    print(f"Cards in manifest: {len(manifest.get('cards', []))}")
    print(f"Cards in engine: {len(CardRegistry.all())}")
    print()

    card_results = compare_cards(manifest)
    event_results = compare_events(manifest)
    all_results = card_results + event_results

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        # Summary
        counts = {}
        for r in all_results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1

        print("=== Card Reconciliation ===")
        print()
        print_table(card_results, show_ok=args.show_ok)

        if event_results:
            print()
            print("=== Event Reconciliation ===")
            print()
            print_table(event_results, show_ok=args.show_ok)

        print()
        print("Summary:", ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

        mismatches = counts.get("MISMATCH", 0)
        if mismatches > 0:
            print(f"\n{mismatches} MISMATCH(ES) found — review card_manifest.json and fix engine or manifest.")


if __name__ == "__main__":
    main()
