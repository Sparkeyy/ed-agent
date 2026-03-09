from __future__ import annotations

import math


def calculate_expected(rating_a: int, rating_b: int) -> float:
    """Standard ELO expected score for player A vs player B."""
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))


def calculate_elo_change(rating: int, expected: float, actual: float, k: int = 32) -> int:
    return round(k * (actual - expected))


def update_multiplayer_elo(results: list[dict]) -> list[dict]:
    """Update ELO for a multiplayer game based on placement.

    Takes list of {"player_id": str, "elo": int, "placement": int}.
    Returns same list with "elo_delta" and "new_elo" added.
    """
    n = len(results)
    deltas: dict[str, float] = {r["player_id"]: 0.0 for r in results}

    # Compare each pair: lower placement number = win
    for i in range(n):
        for j in range(i + 1, n):
            a, b = results[i], results[j]
            expected_a = calculate_expected(a["elo"], b["elo"])
            expected_b = 1.0 - expected_a

            if a["placement"] < b["placement"]:
                actual_a, actual_b = 1.0, 0.0
            elif a["placement"] > b["placement"]:
                actual_a, actual_b = 0.0, 1.0
            else:
                actual_a, actual_b = 0.5, 0.5

            # Scale K by number of opponents so total impact is reasonable
            k = 32 / (n - 1)
            deltas[a["player_id"]] += k * (actual_a - expected_a)
            deltas[b["player_id"]] += k * (actual_b - expected_b)

    for r in results:
        r["elo_delta"] = round(deltas[r["player_id"]])
        r["new_elo"] = r["elo"] + r["elo_delta"]

    return results
