"""Evaluation harness: pit RL agent against baselines.

Supports evaluation against random agent, heuristic agent, and previous checkpoints.
Tracks ELO-like ratings and generates training curves.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("ed_ai.rl.evaluate")


def evaluate_vs_random(
    network_state_dict: dict,
    num_games: int = 100,
    seed: int | None = None,
    temperature: float = 1.0,
) -> dict[str, Any]:
    """Evaluate RL agent vs random opponent.

    Returns win rate, average score, and score distributions.
    """
    from ed_ai.rl.self_play import play_one_game

    rng = random.Random(seed)
    rl_wins = 0
    rl_scores = []
    random_scores = []

    for i in range(num_games):
        game_seed = rng.randint(0, 2**31)
        results = _play_rl_vs_random(network_state_dict, game_seed, temperature)
        rl_score = results["rl_score"]
        rand_score = results["random_score"]
        rl_scores.append(rl_score)
        random_scores.append(rand_score)
        if rl_score > rand_score:
            rl_wins += 1

    return {
        "opponent": "random",
        "num_games": num_games,
        "rl_win_rate": rl_wins / max(num_games, 1),
        "rl_avg_score": np.mean(rl_scores),
        "rl_std_score": np.std(rl_scores),
        "random_avg_score": np.mean(random_scores),
        "random_std_score": np.std(random_scores),
        "rl_score_range": (int(np.min(rl_scores)), int(np.max(rl_scores))),
    }


def _play_rl_vs_random(
    network_state_dict: dict,
    seed: int,
    temperature: float = 1.0,
) -> dict[str, int]:
    """Play one game: RL agent (player 0) vs random agent (player 1)."""
    import torch
    from ed_engine.engine.game_manager import GameManager
    from ed_ai.rl.action_encoder import build_action_mask, build_event_id_map, decode_action, encode_action
    from ed_ai.rl.network import EverdellNetwork
    from ed_ai.rl.state_encoder import encode_state_from_game

    gm = GameManager(["RL", "Random"], seed=seed)
    net = EverdellNetwork()
    net.load_state_dict(network_state_dict)
    net.eval()
    event_id_map = build_event_id_map(gm.game)
    rng = random.Random(seed + 1)

    turn = 0
    while not gm.is_game_over() and turn < 200:
        current_idx = gm.game.current_player_idx
        valid_actions = gm.get_valid_actions()
        if not valid_actions:
            break

        if current_idx == 0:
            # RL agent
            state = encode_state_from_game(gm, 0)
            mask = build_action_mask([a.model_dump() for a in valid_actions], event_id_map)
            if mask.sum() == 0:
                chosen = valid_actions[0]
            else:
                state_t = torch.from_numpy(state).float()
                mask_t = torch.from_numpy(mask).float()
                action_idx, _, _ = net.get_action(state_t, mask_t, temperature=temperature)
                action_dict = decode_action(action_idx, [a.model_dump() for a in valid_actions], event_id_map)
                chosen = valid_actions[0]
                if action_dict:
                    for va in valid_actions:
                        if encode_action(va.model_dump(), event_id_map) == action_idx:
                            chosen = va
                            break
        else:
            # Random agent
            chosen = rng.choice(valid_actions)

        gm.perform_action(chosen)
        turn += 1

    try:
        scores = gm.calculate_scores()
    except Exception:
        scores = {p.name: p.score for p in gm.game.players}

    return {
        "rl_score": scores.get("RL", 0),
        "random_score": scores.get("Random", 0),
    }


def evaluate_vs_heuristic(
    network_state_dict: dict,
    num_games: int = 100,
    seed: int | None = None,
    temperature: float = 1.0,
) -> dict[str, Any]:
    """Evaluate RL agent vs heuristic opponent (same as AIPlayer fallback)."""
    rng = random.Random(seed)
    rl_wins = 0
    rl_scores = []
    heuristic_scores = []

    for i in range(num_games):
        game_seed = rng.randint(0, 2**31)
        results = _play_rl_vs_heuristic(network_state_dict, game_seed, temperature)
        rl_scores.append(results["rl_score"])
        heuristic_scores.append(results["heuristic_score"])
        if results["rl_score"] > results["heuristic_score"]:
            rl_wins += 1

    return {
        "opponent": "heuristic",
        "num_games": num_games,
        "rl_win_rate": rl_wins / max(num_games, 1),
        "rl_avg_score": np.mean(rl_scores),
        "rl_std_score": np.std(rl_scores),
        "heuristic_avg_score": np.mean(heuristic_scores),
        "heuristic_std_score": np.std(heuristic_scores),
    }


def _play_rl_vs_heuristic(
    network_state_dict: dict,
    seed: int,
    temperature: float = 1.0,
) -> dict[str, int]:
    """Play one game: RL agent vs heuristic agent."""
    import torch
    from ed_engine.engine.game_manager import GameManager
    from ed_ai.rl.action_encoder import build_action_mask, build_event_id_map, decode_action, encode_action
    from ed_ai.rl.network import EverdellNetwork
    from ed_ai.rl.state_encoder import encode_state_from_game

    gm = GameManager(["RL", "Heuristic"], seed=seed)
    net = EverdellNetwork()
    net.load_state_dict(network_state_dict)
    net.eval()
    event_id_map = build_event_id_map(gm.game)

    # Import heuristic
    from ed_ai.agent import AIPlayer
    heuristic = AIPlayer(game_id="", player_token="", player_id="", difficulty="journeyman")

    turn = 0
    while not gm.is_game_over() and turn < 200:
        current_idx = gm.game.current_player_idx
        valid_actions = gm.get_valid_actions()
        if not valid_actions:
            break

        valid_dicts = [a.model_dump() for a in valid_actions]

        if current_idx == 0:
            # RL agent
            state = encode_state_from_game(gm, 0)
            mask = build_action_mask(valid_dicts, event_id_map)
            if mask.sum() == 0:
                chosen = valid_actions[0]
            else:
                state_t = torch.from_numpy(state).float()
                mask_t = torch.from_numpy(mask).float()
                action_idx, _, _ = net.get_action(state_t, mask_t, temperature=temperature)
                chosen = valid_actions[0]
                for va in valid_actions:
                    if encode_action(va.model_dump(), event_id_map) == action_idx:
                        chosen = va
                        break
        else:
            # Heuristic agent
            action_dict = heuristic.heuristic_fallback(valid_dicts, {})
            chosen = valid_actions[0]
            for va in valid_actions:
                vd = va.model_dump()
                if vd.get("action_type") == action_dict.get("action_type"):
                    match = True
                    for k in ("card_name", "location_id", "meadow_index"):
                        if k in action_dict and k in vd and action_dict[k] != vd[k]:
                            match = False
                    if match:
                        chosen = va
                        break

        gm.perform_action(chosen)
        turn += 1

    try:
        scores = gm.calculate_scores()
    except Exception:
        scores = {p.name: p.score for p in gm.game.players}

    return {
        "rl_score": scores.get("RL", 0),
        "heuristic_score": scores.get("Heuristic", 0),
    }


def save_eval_results(
    results: dict[str, Any],
    path: str | Path,
) -> None:
    """Append evaluation results to a JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(results, default=str) + "\n")
