#!/usr/bin/env python3
"""Headless bot-vs-bot game simulator for Everdell engine validation.

Runs thousands of games synchronously via GameManager, collecting VP data
and generating summary statistics for the Training Stats dashboard.

Usage:
    python3 tools/simulate.py                          # Full 30K (master only)
    python3 tools/simulate.py --difficulty all          # All difficulties (90K total)
    python3 tools/simulate.py --players 2 --count 100  # Quick test
    python3 tools/simulate.py --summary                # Print summary from existing results
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add ed-engine to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ed_engine.engine.actions import ActionType, GameAction
from ed_engine.engine.game_manager import GameManager
from ed_engine.engine.scoring import ScoringEngine

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DIFFICULTIES = ("apprentice", "journeyman", "master")
DEFAULT_COUNT = 10_000
MAX_TURNS = 500


# ---------------------------------------------------------------------------
# AI strategies
# ---------------------------------------------------------------------------

def _find_card(action: GameAction, game) -> object | None:
    """Find the card object for a play_card action."""
    if action.source == "meadow" and action.meadow_index is not None:
        if 0 <= action.meadow_index < len(game.meadow):
            return game.meadow[action.meadow_index]
    if action.source == "hand" and action.card_name:
        for p in game.players:
            for c in p.hand:
                if c.name == action.card_name:
                    return c
    return None


def pick_action_apprentice(valid_actions: list[GameAction], game, rng: random.Random) -> GameAction:
    """Apprentice: 30% play cards, rest random."""
    if len(valid_actions) == 1:
        return valid_actions[0]

    resolve = [a for a in valid_actions if a.action_type == ActionType.RESOLVE_CHOICE]
    if resolve:
        return rng.choice(resolve)

    play_card = [a for a in valid_actions if a.action_type == ActionType.PLAY_CARD]
    if rng.random() < 0.3 and play_card:
        return rng.choice(play_card)
    return rng.choice(valid_actions)


def pick_action_journeyman(valid_actions: list[GameAction], game, rng: random.Random) -> GameAction:
    """Journeyman: Score cards by base_points + paired bonus, 80% pick best."""
    if len(valid_actions) == 1:
        return valid_actions[0]

    resolve = [a for a in valid_actions if a.action_type == ActionType.RESOLVE_CHOICE]
    if resolve:
        return rng.choice(resolve)

    play_card = [a for a in valid_actions if a.action_type == ActionType.PLAY_CARD]
    place_worker = [a for a in valid_actions if a.action_type == ActionType.PLACE_WORKER]
    prepare = [a for a in valid_actions if a.action_type == ActionType.PREPARE_FOR_SEASON]
    claim_event = [a for a in valid_actions if a.action_type == ActionType.CLAIM_EVENT]

    if claim_event:
        return rng.choice(claim_event)

    if play_card:
        scored = []
        for a in play_card:
            card = _find_card(a, game)
            pts = card.base_points if card else 0
            bonus = 5 if a.use_paired_construction else 0
            scored.append((pts + bonus, a))
        scored.sort(key=lambda x: x[0], reverse=True)

        if len(scored) == 1 or rng.random() < 0.8:
            return scored[0][1]
        return scored[min(1, len(scored) - 1)][1]

    if place_worker:
        return rng.choice(place_worker)
    if prepare:
        return prepare[0]
    return valid_actions[0]


def pick_action_master(valid_actions: list[GameAction], game, rng: random.Random) -> GameAction:
    """Master: Always best card, smart resolve_choice, claims events eagerly,
    prefers forest locations by resource value, journey in autumn."""
    if len(valid_actions) == 1:
        return valid_actions[0]

    # Smart resolve_choice: pick highest-value option (highest choice_index
    # tends to be better resources, but we pick last which is often "best")
    resolve = [a for a in valid_actions if a.action_type == ActionType.RESOLVE_CHOICE]
    if resolve:
        # Pick the last option (highest index) which is typically the best resource
        return max(resolve, key=lambda a: a.choice_index or 0)

    claim_event = [a for a in valid_actions if a.action_type == ActionType.CLAIM_EVENT]
    play_card = [a for a in valid_actions if a.action_type == ActionType.PLAY_CARD]
    place_worker = [a for a in valid_actions if a.action_type == ActionType.PLACE_WORKER]
    prepare = [a for a in valid_actions if a.action_type == ActionType.PREPARE_FOR_SEASON]

    # Always claim events — free VP
    if claim_event:
        return claim_event[0]

    if play_card:
        scored = []
        for a in play_card:
            card = _find_card(a, game)
            pts = card.base_points if card else 0
            bonus = 5 if a.use_paired_construction else 0
            # Purple prosperity cards score bonus VP
            if card and hasattr(card, 'card_type') and str(card.card_type) == "CardType.PURPLE_PROSPERITY":
                bonus += 3
            scored.append((pts + bonus, a))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    if place_worker:
        # Prefer journey locations in autumn for extra VP
        current_player = None
        for p in game.players:
            if not p.has_passed:
                current_player = p
                break

        if current_player and str(current_player.season) in ("Season.AUTUMN", "autumn"):
            journey = [a for a in place_worker if a.location_id and "journey" in a.location_id]
            if journey:
                # Pick highest journey VP
                return max(journey, key=lambda a: int(a.location_id.split("_")[-1].replace("pt", "")) if a.location_id else 0)

        # Prefer forest locations (better resources)
        forest = [a for a in place_worker if a.location_id and "forest" in a.location_id]
        if forest:
            return rng.choice(forest)

        return rng.choice(place_worker)

    if prepare:
        return prepare[0]
    return valid_actions[0]


STRATEGIES = {
    "apprentice": pick_action_apprentice,
    "journeyman": pick_action_journeyman,
    "master": pick_action_master,
}


# ---------------------------------------------------------------------------
# Game runner
# ---------------------------------------------------------------------------

def run_game(player_count: int, seed: int, difficulty: str) -> dict:
    """Run a single bot game and return result dict."""
    names = [f"Bot_{i+1}" for i in range(player_count)]
    rng = random.Random(seed)
    pick_action = STRATEGIES[difficulty]

    gm = GameManager(player_names=names, seed=seed)
    turns = 0

    while not gm.is_game_over() and turns < MAX_TURNS:
        actions = gm.get_valid_actions()
        if not actions:
            gm.current_player.has_passed = True
            gm.advance_turn()
            turns += 1
            continue
        chosen = pick_action(actions, gm.game, rng)
        gm.perform_action(chosen)
        turns += 1

    completed = gm.is_game_over()
    scores_raw = ScoringEngine.calculate_final_scores(gm.game)

    scores = {}
    cards_played = {}
    for p in gm.game.players:
        breakdown = scores_raw.get(p.name)
        if breakdown:
            scores[p.name] = {
                "total": breakdown.total,
                "base_card_points": breakdown.base_card_points,
                "bonus_card_points": breakdown.bonus_card_points,
                "event_points": breakdown.event_points,
                "journey_points": breakdown.journey_points,
                "point_tokens": breakdown.point_tokens,
            }
        else:
            scores[p.name] = {"total": 0}
        cards_played[p.name] = [c.name for c in p.city]

    # Determine winner
    winner = max(scores, key=lambda n: scores[n]["total"]) if scores else None

    return {
        "seed": seed,
        "player_count": player_count,
        "difficulty": difficulty,
        "turns": turns,
        "completed": completed,
        "scores": scores,
        "winner": winner,
        "cards_played": cards_played,
    }


def count_existing(filepath: Path) -> int:
    """Count lines in existing JSONL file."""
    if not filepath.exists():
        return 0
    with open(filepath) as f:
        return sum(1 for _ in f)


def run_batch(player_count: int, difficulty: str, count: int) -> Path:
    """Run a batch of games, writing results to JSONL. Supports resumption."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = RESULTS_DIR / f"results_{player_count}p_{difficulty}.jsonl"

    existing = count_existing(filepath)
    if existing >= count:
        print(f"  {filepath.name}: {existing}/{count} already done, skipping")
        return filepath

    if existing > 0:
        print(f"  {filepath.name}: resuming from game {existing}/{count}")

    t0 = time.time()
    with open(filepath, "a") as f:
        for i in range(existing, count):
            seed = i + (player_count * 100_000)  # unique seeds per player count
            result = run_game(player_count, seed, difficulty)
            f.write(json.dumps(result) + "\n")

            # Progress every 1000 games
            done = i - existing + 1
            if done % 1000 == 0:
                elapsed = time.time() - t0
                rate = done / elapsed
                remaining = (count - existing - done) / rate
                print(f"  {filepath.name}: {i+1}/{count} ({rate:.0f} games/s, ~{remaining:.0f}s left)")

    elapsed = time.time() - t0
    total_new = count - existing
    print(f"  {filepath.name}: {total_new} games in {elapsed:.1f}s ({total_new/elapsed:.0f} games/s)")
    return filepath


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def generate_summary() -> dict:
    """Generate summary.json from all result files."""
    from datetime import datetime, timezone

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "by_player_count": {},
    }

    for pc in (2, 3, 4):
        summary["by_player_count"][str(pc)] = {}
        for diff in DIFFICULTIES:
            filepath = RESULTS_DIR / f"results_{pc}p_{diff}.jsonl"
            if not filepath.exists():
                continue

            results = []
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))

            if not results:
                continue

            # Collect all VP totals (winner VP for simplicity — best player's score)
            all_vp = []
            card_wins = defaultdict(int)
            card_appearances = defaultdict(int)
            total_games = len(results)
            completed = sum(1 for r in results if r["completed"])

            for r in results:
                winner = r.get("winner")
                if winner and winner in r["scores"]:
                    all_vp.append(r["scores"][winner]["total"])

                # Track card win rates
                if winner and winner in r.get("cards_played", {}):
                    for card in r["cards_played"][winner]:
                        card_wins[card] += 1

                # Track card appearances (across all players)
                for player_cards in r.get("cards_played", {}).values():
                    for card in player_cards:
                        card_appearances[card] += 1

            if not all_vp:
                continue

            # Rolling average VP (100-game windows)
            window = 100
            vp_over_time = []
            for i in range(0, len(all_vp), window):
                chunk = all_vp[i:i+window]
                if chunk:
                    vp_over_time.append(round(sum(chunk) / len(chunk), 1))

            # Top cards by win rate (among games where the card appeared)
            top_cards = []
            for card, wins in sorted(card_wins.items(), key=lambda x: x[1], reverse=True)[:15]:
                appearances = card_appearances.get(card, 1)
                rate = round(wins / total_games, 3)
                top_cards.append([card, rate])

            # Average VP across all players (not just winner)
            all_player_vp = []
            for r in results:
                for name, score in r["scores"].items():
                    all_player_vp.append(score["total"])

            # Score breakdown averages
            breakdown_sums = defaultdict(float)
            breakdown_count = 0
            for r in results:
                for name, score in r["scores"].items():
                    for key, val in score.items():
                        if key != "total":
                            breakdown_sums[key] += val
                    breakdown_count += 1

            avg_breakdown = {}
            if breakdown_count > 0:
                for key, total in breakdown_sums.items():
                    avg_breakdown[key] = round(total / breakdown_count, 1)

            summary["by_player_count"][str(pc)][diff] = {
                "games": total_games,
                "completed": completed,
                "avg_winner_vp": round(sum(all_vp) / len(all_vp), 1),
                "avg_vp": round(sum(all_player_vp) / len(all_player_vp), 1) if all_player_vp else 0,
                "min_vp": min(all_vp),
                "max_vp": max(all_vp),
                "vp_over_time": vp_over_time,
                "top_cards": top_cards,
                "avg_breakdown": avg_breakdown,
            }

    return summary


def print_summary():
    """Print summary from existing results."""
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("No summary.json found. Run simulation first.")
        return

    with open(summary_path) as f:
        summary = json.load(f)

    print(f"Generated: {summary['generated_at']}\n")
    for pc, difficulties in sorted(summary["by_player_count"].items()):
        print(f"=== {pc} Players ===")
        for diff, stats in sorted(difficulties.items()):
            print(f"  {diff:12s}: {stats['games']:,} games, "
                  f"avg winner VP={stats['avg_winner_vp']:.1f}, "
                  f"avg VP={stats['avg_vp']:.1f}, "
                  f"range=[{stats['min_vp']}-{stats['max_vp']}], "
                  f"completed={stats['completed']:,}")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Everdell bot game simulator")
    parser.add_argument("--players", type=int, choices=[2, 3, 4], default=None,
                        help="Player count (default: all)")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT,
                        help=f"Games per config (default: {DEFAULT_COUNT})")
    parser.add_argument("--difficulty", type=str, default="master",
                        choices=["apprentice", "journeyman", "master", "all"],
                        help="AI difficulty (default: master)")
    parser.add_argument("--summary", action="store_true",
                        help="Print summary from existing results")
    args = parser.parse_args()

    if args.summary:
        print_summary()
        return

    player_counts = [args.players] if args.players else [2, 3, 4]
    difficulties = list(DIFFICULTIES) if args.difficulty == "all" else [args.difficulty]

    total_games = len(player_counts) * len(difficulties) * args.count
    print(f"Simulating {total_games:,} games ({len(player_counts)} player counts x "
          f"{len(difficulties)} difficulties x {args.count:,} each)\n")

    t0 = time.time()
    for pc in player_counts:
        for diff in difficulties:
            print(f"[{pc}p {diff}]")
            run_batch(pc, diff, args.count)
            print()

    elapsed = time.time() - t0
    print(f"Total time: {elapsed:.1f}s")

    # Generate summary
    print("Generating summary.json...")
    summary = generate_summary()
    summary_path = RESULTS_DIR / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Written to {summary_path}")

    # Print it
    print()
    print_summary()


if __name__ == "__main__":
    main()
