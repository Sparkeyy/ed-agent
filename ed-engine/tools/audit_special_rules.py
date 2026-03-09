#!/usr/bin/env python3
"""Audit special card rules against engine implementation.

Reads the reviewed card_manifest.json and cross-references ability_text
against actual engine behavior. Reports implemented, deferred, and
potentially incorrect rules.

Usage:
    python tools/audit_special_rules.py
    python tools/audit_special_rules.py --manifest path/to/card_manifest.json
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path

# Add engine to path
TOOLS_DIR = Path(__file__).resolve().parent
ENGINE_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(ENGINE_DIR))

from ed_engine.cards import CardRegistry  # noqa: E402
from ed_engine.cards.critters import *  # noqa: F401,F403
from ed_engine.cards.constructions import *  # noqa: F401,F403

MANIFEST_PATH = TOOLS_DIR / "card_manifest.json"

# ---------------------------------------------------------------------------
# Known special conditions to audit
# ---------------------------------------------------------------------------

KNOWN_RULES: list[dict] = [
    # City space
    {"card": "Wanderer", "rule": "Does not occupy city space",
     "check": lambda c: not c.occupies_city_space, "expected": True},

    # Negative VP
    {"card": "Fool", "rule": "Base points = -2",
     "check": lambda c: c.base_points == -2, "expected": True},

    # Open destinations
    {"card": "Inn", "rule": "Open destination (multiple workers)",
     "check": lambda c: c.is_open_destination, "expected": True},
    {"card": "Post Office", "rule": "Open destination (multiple workers)",
     "check": lambda c: c.is_open_destination, "expected": True},

    # Free to play
    {"card": "Ruins", "rule": "Free to play (0 cost)",
     "check": lambda c: c.cost.twig == 0 and c.cost.resin == 0 and c.cost.pebble == 0 and c.cost.berry == 0,
     "expected": True},
]


def check_method_implemented(card, method_name: str) -> str:
    """Check if a card method has a real implementation (not just pass)."""
    method = getattr(card, method_name, None)
    if method is None:
        return "NOT_FOUND"

    try:
        source = inspect.getsource(method)
        # Strip docstring and check if body is just 'pass'
        lines = source.strip().split("\n")
        body_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if in_docstring:
                    in_docstring = False
                    continue
                if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                    continue  # single-line docstring
                in_docstring = True
                continue
            if in_docstring:
                continue
            if stripped.startswith("def "):
                continue
            body_lines.append(stripped)

        non_empty = [l for l in body_lines if l and l != "pass"]
        if not non_empty:
            return "DEFERRED"
        return "IMPLEMENTED"
    except (TypeError, OSError):
        return "UNKNOWN"


def audit_card(name: str, card_cls, manifest_entry: dict | None) -> list[dict]:
    """Audit a single card's special rules."""
    card = card_cls()
    results: list[dict] = []

    # Check lifecycle methods
    lifecycle_methods = {
        "on_play": "tan_traveler",
        "on_production": "green_production",
        "on_worker_placed": "red_destination",
        "on_card_played": "blue_governance",
        "on_score": "purple_prosperity",
    }

    # Check the primary method for this card type
    card_type = card.card_type.value
    for method_name, expected_type in lifecycle_methods.items():
        if card_type == expected_type:
            status = check_method_implemented(card, method_name)
            ability_text = ""
            if manifest_entry:
                ability_text = manifest_entry.get("ability_text", "")

            results.append({
                "card": name,
                "rule": f"{method_name}() — {ability_text[:60] or '(no manifest text)'}",
                "engine_status": status,
            })

    # Check known rules
    for rule_def in KNOWN_RULES:
        if rule_def["card"] == name:
            try:
                actual = rule_def["check"](card)
                status = "OK" if actual == rule_def["expected"] else "MISMATCH"
            except Exception as e:
                status = f"ERROR: {e}"

            results.append({
                "card": name,
                "rule": rule_def["rule"],
                "engine_status": status,
            })

    return results


def audit_pairings(manifest: dict) -> list[dict]:
    """Verify all card pairings are bidirectional."""
    registry = CardRegistry.all()
    results: list[dict] = []

    for name, card_cls in sorted(registry.items()):
        card = card_cls()
        if not card.paired_with:
            continue

        paired_cls = registry.get(card.paired_with)
        if paired_cls is None:
            results.append({
                "card": name,
                "rule": f"Paired with '{card.paired_with}' — partner not in registry",
                "engine_status": "MISMATCH",
            })
            continue

        partner = paired_cls()
        if partner.paired_with != name:
            # Check manifest for dual pairing (e.g., Farm paired with Harvester AND Gatherer)
            results.append({
                "card": name,
                "rule": f"Paired with '{card.paired_with}' but partner paired with '{partner.paired_with}'",
                "engine_status": "MISMATCH" if partner.paired_with else "MISSING",
            })
        else:
            results.append({
                "card": name,
                "rule": f"Paired with '{card.paired_with}' (bidirectional)",
                "engine_status": "OK",
            })

    return results


def print_audit_table(results: list[dict], title: str, show_ok: bool = False) -> None:
    """Print audit results as formatted table."""
    filtered = results if show_ok else [r for r in results if r["engine_status"] != "OK"]

    if not filtered:
        print(f"  All {title.lower()} checks passed!")
        return

    w_card = max(len(r["card"]) for r in filtered)
    w_rule = max(min(len(r["rule"]), 70) for r in filtered)

    header = f"{'Card':<{w_card}}  {'Rule':<{w_rule}}  Engine Status"
    print(header)
    print("-" * len(header))

    for r in filtered:
        rule = r["rule"][:70]
        status = r["engine_status"]
        marker = ""
        if status == "DEFERRED":
            marker = " (not implemented)"
        elif status == "MISMATCH":
            marker = " <--"
        elif status == "MISSING":
            marker = " ?"

        print(f"{r['card']:<{w_card}}  {rule:<{w_rule}}  {status}{marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit special card rules against engine")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Path to card_manifest.json")
    parser.add_argument("--show-ok", action="store_true", help="Include OK results")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest: dict = {"cards": [], "forest_locations": [], "events": []}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        print(f"Manifest: {manifest_path}")
    else:
        print("No manifest found — auditing engine definitions only")

    # Index manifest by name
    manifest_by_name = {c["name"]: c for c in manifest.get("cards", [])}

    registry = CardRegistry.all()
    print(f"Engine cards: {len(registry)}")
    print()

    # Audit each card
    all_results: list[dict] = []
    for name, card_cls in sorted(registry.items()):
        m_entry = manifest_by_name.get(name)
        results = audit_card(name, card_cls, m_entry)
        all_results.extend(results)

    # Audit pairings
    pairing_results = audit_pairings(manifest)

    if args.json:
        print(json.dumps({"rules": all_results, "pairings": pairing_results}, indent=2))
        return

    print("=== Special Rules Audit ===")
    print()
    print_audit_table(all_results, "Rules", show_ok=args.show_ok)

    print()
    print("=== Pairing Audit ===")
    print()
    print_audit_table(pairing_results, "Pairings", show_ok=args.show_ok)

    # Summary
    counts: dict[str, int] = {}
    for r in all_results + pairing_results:
        s = r["engine_status"]
        counts[s] = counts.get(s, 0) + 1

    print()
    print("Summary:", ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

    deferred = counts.get("DEFERRED", 0)
    mismatches = counts.get("MISMATCH", 0)
    if deferred > 0:
        print(f"\n{deferred} DEFERRED rule(s) — these cards have stub implementations (pass)")
    if mismatches > 0:
        print(f"\n{mismatches} MISMATCH(ES) — engine behavior may not match card text")


if __name__ == "__main__":
    main()
