"""Headless self-play runner — imports GameManager directly, no HTTP.

Plays complete games using the RL agent against itself, collecting
trajectories for PPO training.
"""

from __future__ import annotations

import logging
import random
import sys
import traceback
from multiprocessing import Pool
from typing import Any

import numpy as np

from ed_ai.rl.action_encoder import (
    ACTION_SPACE_SIZE,
    build_action_mask,
    build_event_id_map,
    decode_action,
    encode_action,
)
from ed_ai.rl.ppo_agent import Trajectory
from ed_ai.rl.state_encoder import STATE_SIZE, encode_state_from_game

logger = logging.getLogger("ed_ai.rl.self_play")


def _make_player_names(num_players: int) -> list[str]:
    return [f"RL_{i}" for i in range(num_players)]


def play_one_game(
    network_state_dict: dict | None,
    seed: int | None = None,
    num_players: int | None = None,
    temperature: float = 1.0,
    max_turns: int = 200,
) -> list[dict[str, Any]]:
    """Play a complete headless game, returning trajectory data.

    This function is designed to run in a subprocess — it imports the engine
    and creates a fresh network instance to avoid pickling issues.

    Args:
        network_state_dict: Serialized network weights (or None for random policy)
        seed: Random seed for reproducibility
        num_players: 2-4 (or None for random)
        temperature: Action sampling temperature
        max_turns: Safety limit

    Returns:
        List of trajectory dicts (one per player), each containing:
        - transitions: list of (state, action, log_prob, value, mask) tuples
        - final_score: int
    """
    import torch
    from ed_engine.engine.game_manager import GameManager
    from ed_ai.rl.network import EverdellNetwork

    rng = random.Random(seed)

    if num_players is None:
        num_players = rng.choice([2, 3, 4])

    player_names = _make_player_names(num_players)
    gm = GameManager(player_names, seed=seed)

    # Create network
    net = EverdellNetwork()
    if network_state_dict is not None:
        net.load_state_dict(network_state_dict)
    net.eval()

    # Per-player trajectories
    trajectories: list[list[tuple]] = [[] for _ in range(num_players)]
    event_id_map = build_event_id_map(gm.game)

    turn_count = 0
    try:
        while not gm.is_game_over() and turn_count < max_turns:
            current_idx = gm.game.current_player_idx
            player = gm.game.players[current_idx]

            valid_actions = gm.get_valid_actions()
            if not valid_actions:
                # No valid actions — should not happen, but safety
                break

            # Encode state and mask
            state = encode_state_from_game(gm, current_idx)
            mask = build_action_mask(
                [a.model_dump() for a in valid_actions],
                event_id_map,
            )

            # Check mask has at least one valid action
            if mask.sum() == 0:
                # Fallback: pick first valid action
                action_dict = valid_actions[0].model_dump()
                gm.perform_action(valid_actions[0])
                turn_count += 1
                continue

            # Select action
            state_t = torch.from_numpy(state).float()
            mask_t = torch.from_numpy(mask).float()
            action_idx, log_prob, value = net.get_action(
                state_t, mask_t, temperature=temperature
            )

            # Decode to valid action
            valid_dicts = [a.model_dump() for a in valid_actions]
            action_dict = decode_action(action_idx, valid_dicts, event_id_map)

            if action_dict is None:
                # Mask/decode mismatch — pick action with highest mask overlap
                action_dict = valid_dicts[0]
                action_idx = encode_action(action_dict, event_id_map)

            # Record transition
            trajectories[current_idx].append((
                state.copy(), action_idx, log_prob, value, mask.copy()
            ))

            # Find the matching GameAction
            chosen_action = None
            for va in valid_actions:
                va_dict = va.model_dump()
                if encode_action(va_dict, event_id_map) == action_idx:
                    chosen_action = va
                    break
            if chosen_action is None:
                chosen_action = valid_actions[0]

            gm.perform_action(chosen_action)
            turn_count += 1

    except Exception as e:
        logger.warning("Game error (seed=%s): %s", seed, e)
        traceback.print_exc()

    # Calculate final scores
    try:
        scores = gm.calculate_scores()
    except Exception:
        scores = {p.name: p.score for p in gm.game.players}

    # Build result
    results = []
    for i in range(num_players):
        player_name = player_names[i]
        score = scores.get(player_name, 0)
        results.append({
            "transitions": trajectories[i],
            "final_score": score,
            "player_name": player_name,
            "num_turns": len(trajectories[i]),
        })

    return results


def _play_game_wrapper(args: tuple) -> list[dict]:
    """Wrapper for multiprocessing — unpacks args tuple."""
    return play_one_game(*args)


def parallel_self_play(
    network_state_dict: dict | None,
    num_games: int = 64,
    num_workers: int | None = None,
    temperature: float = 1.0,
    base_seed: int | None = None,
) -> list[Trajectory]:
    """Play multiple games in parallel using multiprocessing.

    Args:
        network_state_dict: Network weights to use
        num_games: Number of games to play
        num_workers: Number of worker processes (default: CPU count / 2)
        temperature: Action sampling temperature
        base_seed: Base seed (each game gets base_seed + i)

    Returns:
        List of Trajectory objects (one per player per game)
    """
    import os
    if num_workers is None:
        num_workers = max(1, (os.cpu_count() or 4) // 2)

    rng = random.Random(base_seed)

    # Prepare args for each game
    args_list = []
    for i in range(num_games):
        game_seed = rng.randint(0, 2**31) if base_seed is not None else None
        num_players = rng.choice([2, 3, 4])
        args_list.append((network_state_dict, game_seed, num_players, temperature))

    # Run games in parallel
    all_trajectories: list[Trajectory] = []

    if num_workers <= 1:
        # Sequential for debugging
        for args in args_list:
            game_results = play_one_game(*args)
            all_trajectories.extend(_convert_results(game_results))
    else:
        with Pool(processes=num_workers) as pool:
            for game_results in pool.imap_unordered(_play_game_wrapper, args_list):
                all_trajectories.extend(_convert_results(game_results))

    return all_trajectories


def _convert_results(game_results: list[dict]) -> list[Trajectory]:
    """Convert raw game results to Trajectory objects."""
    trajectories = []
    for result in game_results:
        traj = Trajectory()
        for state, action, log_prob, value, mask in result["transitions"]:
            traj.transitions.append(
                __import__("ed_ai.rl.ppo_agent", fromlist=["Transition"]).Transition(
                    state=state,
                    action=action,
                    log_prob=log_prob,
                    value=value,
                    reward=0.0,
                    done=False,
                    action_mask=mask,
                )
            )
        traj.finalize(result["final_score"])
        if traj.transitions:
            trajectories.append(traj)
    return trajectories
