"""Model checkpoint save/load with metadata and difficulty tier mapping."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import torch

from ed_ai.rl.network import EverdellNetwork

logger = logging.getLogger("ed_ai.rl.checkpoint")

# Default model directory (gitignored)
DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent / "models"

# Difficulty tier → checkpoint filename
TIER_CHECKPOINTS = {
    "apprentice": "apprentice.pt",
    "journeyman": "journeyman.pt",
    "master": "master.pt",
}

# Temperature per difficulty tier
TIER_TEMPERATURES = {
    "apprentice": 1.5,
    "journeyman": 1.0,
    "master": 0.3,
}


def save_checkpoint(
    network: EverdellNetwork,
    path: str | Path,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Save model checkpoint with metadata.

    Args:
        network: The network to save
        path: Path to save the checkpoint
        metadata: Optional metadata dict (iteration, win_rate, avg_score, etc.)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "model_state_dict": network.state_dict(),
        "state_size": network.state_size,
        "action_size": network.action_size,
        "param_count": network.param_count(),
        "metadata": metadata or {},
    }
    torch.save(checkpoint, path)
    logger.info("Saved checkpoint to %s (params=%d)", path, network.param_count())

    # Also save metadata as JSON for easy inspection
    meta_path = path.with_suffix(".json")
    meta = {
        "param_count": network.param_count(),
        "state_size": network.state_size,
        "action_size": network.action_size,
        **(metadata or {}),
    }
    meta_path.write_text(json.dumps(meta, indent=2, default=str))


def load_checkpoint(
    path: str | Path,
    device: str = "cpu",
) -> tuple[EverdellNetwork, dict[str, Any]]:
    """Load model checkpoint.

    Args:
        path: Path to the checkpoint file
        device: Device to load onto

    Returns:
        (network, metadata) tuple
    """
    path = Path(path)
    checkpoint = torch.load(path, map_location=device, weights_only=True)

    state_size = checkpoint.get("state_size")
    action_size = checkpoint.get("action_size")
    network = EverdellNetwork(
        state_size=state_size,
        action_size=action_size,
    )
    network.load_state_dict(checkpoint["model_state_dict"])
    network.eval()

    metadata = checkpoint.get("metadata", {})
    logger.info("Loaded checkpoint from %s (params=%d)", path, network.param_count())
    return network, metadata


def load_for_difficulty(
    difficulty: str,
    model_dir: str | Path | None = None,
    device: str = "cpu",
) -> tuple[EverdellNetwork, float, dict[str, Any]]:
    """Load the appropriate checkpoint for a difficulty tier.

    Args:
        difficulty: "apprentice", "journeyman", or "master"
        model_dir: Directory containing model files
        device: Device to load onto

    Returns:
        (network, temperature, metadata)
    """
    model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    filename = TIER_CHECKPOINTS.get(difficulty, "journeyman.pt")
    temperature = TIER_TEMPERATURES.get(difficulty, 1.0)

    path = model_dir / filename
    if not path.exists():
        # Fall back: try any available checkpoint
        for tier in ["master", "journeyman", "apprentice"]:
            fallback = model_dir / TIER_CHECKPOINTS[tier]
            if fallback.exists():
                logger.warning(
                    "Checkpoint %s not found, falling back to %s", path, fallback
                )
                path = fallback
                break
        else:
            raise FileNotFoundError(
                f"No RL model checkpoints found in {model_dir}. "
                "Run training first: python -m ed_ai.rl.train"
            )

    network, metadata = load_checkpoint(path, device=device)
    return network, temperature, metadata


def list_checkpoints(model_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """List all available checkpoints with their metadata."""
    model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
    if not model_dir.exists():
        return []

    checkpoints = []
    for pt_file in sorted(model_dir.glob("*.pt")):
        meta_file = pt_file.with_suffix(".json")
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
            except json.JSONDecodeError:
                pass
        checkpoints.append({
            "filename": pt_file.name,
            "path": str(pt_file),
            "size_mb": pt_file.stat().st_size / (1024 * 1024),
            **meta,
        })
    return checkpoints
