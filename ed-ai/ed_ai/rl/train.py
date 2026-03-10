"""Training orchestrator for Everdell RL agent.

Supports both CLI execution and background API-triggered training.
Logs progress to a JSONL file for monitoring.

Usage:
    python -m ed_ai.rl.train [--batches 10000] [--games-per-batch 64] [--workers 8]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from ed_ai.rl.checkpoint import DEFAULT_MODEL_DIR, save_checkpoint
from ed_ai.rl.network import EverdellNetwork
from ed_ai.rl.ppo_agent import PPOAgent
from ed_ai.rl.self_play import parallel_self_play

logger = logging.getLogger("ed_ai.rl.train")

# Progress file for monitoring
PROGRESS_FILE = DEFAULT_MODEL_DIR / "training_progress.jsonl"
STATUS_FILE = DEFAULT_MODEL_DIR / "training_status.json"


class TrainingRun:
    """Manages a single training run with progress tracking."""

    def __init__(
        self,
        num_batches: int = 10000,
        games_per_batch: int = 64,
        num_workers: int | None = None,
        lr: float = 3e-4,
        temperature: float = 1.0,
        eval_interval: int = 100,
        save_interval: int = 1000,
        model_dir: str | Path | None = None,
        resume_from: str | Path | None = None,
    ):
        self.num_batches = num_batches
        self.games_per_batch = games_per_batch
        self.num_workers = num_workers or max(1, (os.cpu_count() or 4) // 2)
        self.lr = lr
        self.temperature = temperature
        self.eval_interval = eval_interval
        self.save_interval = save_interval
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.network = EverdellNetwork()
        self.start_batch = 0
        self.is_running = False
        self.is_cancelled = False
        self.current_batch = 0
        self.metrics_history: list[dict] = []

        # Resume from checkpoint
        if resume_from:
            self._load_resume(resume_from)

        self.agent = PPOAgent(self.network, lr=lr)

        logger.info(
            "Training config: batches=%d, games/batch=%d, workers=%d, params=%d",
            num_batches, games_per_batch, self.num_workers, self.network.param_count(),
        )

    def _load_resume(self, path: str | Path) -> None:
        path = Path(path)
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        self.network.load_state_dict(checkpoint["model_state_dict"])
        meta = checkpoint.get("metadata", {})
        self.start_batch = meta.get("iteration", 0)
        logger.info("Resuming from batch %d (checkpoint: %s)", self.start_batch, path)

    def run(self) -> dict[str, Any]:
        """Execute the full training loop. Returns final metrics."""
        self.is_running = True
        self.is_cancelled = False
        self._update_status("running")

        start_time = time.time()
        best_avg_score = 0.0

        try:
            for batch_idx in range(self.start_batch, self.start_batch + self.num_batches):
                if self.is_cancelled:
                    logger.info("Training cancelled at batch %d", batch_idx)
                    break

                self.current_batch = batch_idx
                batch_start = time.time()

                # Self-play
                network_sd = self.network.state_dict()
                trajectories = parallel_self_play(
                    network_state_dict=network_sd,
                    num_games=self.games_per_batch,
                    num_workers=self.num_workers,
                    temperature=self.temperature,
                    base_seed=batch_idx * 1000,
                )

                # PPO update
                metrics = self.agent.update(trajectories)

                # Compute trajectory stats
                scores = [t.final_score for t in trajectories]
                avg_score = np.mean(scores) if scores else 0
                max_score = max(scores) if scores else 0
                turns = [len(t.transitions) for t in trajectories]
                avg_turns = np.mean(turns) if turns else 0

                batch_time = time.time() - batch_start
                elapsed = time.time() - start_time

                batch_metrics = {
                    "batch": batch_idx,
                    "elapsed_s": round(elapsed, 1),
                    "batch_time_s": round(batch_time, 1),
                    "avg_score": round(float(avg_score), 2),
                    "max_score": int(max_score),
                    "avg_turns": round(float(avg_turns), 1),
                    "num_trajectories": len(trajectories),
                    "policy_loss": round(metrics["policy_loss"], 4),
                    "value_loss": round(metrics["value_loss"], 4),
                    "entropy": round(metrics["entropy"], 4),
                    "batch_size": metrics["batch_size"],
                }
                self.metrics_history.append(batch_metrics)
                self._log_progress(batch_metrics)

                # Periodic logging
                if batch_idx % 10 == 0:
                    logger.info(
                        "Batch %d/%d: avg_score=%.1f, policy_loss=%.4f, "
                        "value_loss=%.4f, entropy=%.4f, time=%.1fs",
                        batch_idx, self.start_batch + self.num_batches,
                        avg_score, metrics["policy_loss"],
                        metrics["value_loss"], metrics["entropy"], batch_time,
                    )

                # Save checkpoints
                if batch_idx > 0 and batch_idx % self.save_interval == 0:
                    self._save_tier_checkpoint(batch_idx, avg_score)

                # Track best
                if avg_score > best_avg_score:
                    best_avg_score = float(avg_score)

                self._update_status("running", batch_idx, elapsed)

            # Final save
            self._save_tier_checkpoint(self.current_batch, best_avg_score)
            self._save_final_checkpoints()

        except Exception:
            logger.exception("Training failed at batch %d", self.current_batch)
            self._update_status("failed")
            raise
        finally:
            self.is_running = False

        total_time = time.time() - start_time
        self._update_status("completed", self.current_batch, total_time)

        return {
            "total_batches": self.current_batch - self.start_batch,
            "total_time_s": round(total_time, 1),
            "best_avg_score": round(best_avg_score, 2),
            "final_batch": self.current_batch,
        }

    def cancel(self) -> None:
        """Request cancellation of the training loop."""
        self.is_cancelled = True
        logger.info("Cancellation requested")

    def get_status(self) -> dict[str, Any]:
        """Get current training status."""
        try:
            if STATUS_FILE.exists():
                return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
        return {
            "status": "running" if self.is_running else "idle",
            "current_batch": self.current_batch,
            "total_batches": self.start_batch + self.num_batches,
        }

    def _save_tier_checkpoint(self, batch_idx: int, avg_score: float) -> None:
        """Save checkpoint with tier mapping."""
        filename = f"checkpoint_{batch_idx:06d}.pt"
        save_checkpoint(
            self.network,
            self.model_dir / filename,
            metadata={
                "iteration": batch_idx,
                "avg_score": round(float(avg_score), 2),
                "games_per_batch": self.games_per_batch,
            },
        )

    def _save_final_checkpoints(self) -> None:
        """Save final model as all difficulty tiers (to be replaced by actual tier checkpoints later)."""
        meta = {
            "iteration": self.current_batch,
            "final": True,
        }
        # Save as each tier — training for different durations produces different tiers
        for tier in ["apprentice", "journeyman", "master"]:
            save_checkpoint(
                self.network,
                self.model_dir / f"{tier}.pt",
                metadata={**meta, "tier": tier},
            )
        logger.info("Saved final tier checkpoints")

    def _log_progress(self, metrics: dict) -> None:
        """Append metrics to JSONL progress file."""
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, "a") as f:
            f.write(json.dumps(metrics) + "\n")

    def _update_status(
        self, status: str, batch: int = 0, elapsed: float = 0
    ) -> None:
        """Update status file for monitoring."""
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "status": status,
            "current_batch": batch,
            "total_batches": self.start_batch + self.num_batches,
            "elapsed_s": round(elapsed, 1),
            "progress_pct": round(
                100 * (batch - self.start_batch) / max(self.num_batches, 1), 1
            ),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        STATUS_FILE.write_text(json.dumps(data, indent=2))


# Global reference for API-triggered training
_active_run: TrainingRun | None = None
_training_thread: threading.Thread | None = None


def start_background_training(**kwargs) -> dict[str, str]:
    """Start training in a background thread (for API endpoint)."""
    global _active_run, _training_thread

    if _active_run and _active_run.is_running:
        return {"status": "error", "message": "Training already in progress"}

    _active_run = TrainingRun(**kwargs)
    _training_thread = threading.Thread(target=_active_run.run, daemon=True)
    _training_thread.start()
    return {"status": "started", "message": f"Training started: {kwargs.get('num_batches', 10000)} batches"}


def cancel_training() -> dict[str, str]:
    """Cancel the active training run."""
    if _active_run and _active_run.is_running:
        _active_run.cancel()
        return {"status": "cancelling", "message": "Cancellation requested"}
    return {"status": "idle", "message": "No active training to cancel"}


def get_training_status() -> dict[str, Any]:
    """Get status of the active or most recent training run."""
    if _active_run:
        return _active_run.get_status()
    # Check status file
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return {"status": "idle"}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Train Everdell RL agent via self-play")
    parser.add_argument("--batches", type=int, default=10000, help="Number of training batches")
    parser.add_argument("--games-per-batch", type=int, default=64, help="Games per batch")
    parser.add_argument("--workers", type=int, default=None, help="Worker processes")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--temperature", type=float, default=1.0, help="Action temperature")
    parser.add_argument("--eval-interval", type=int, default=100, help="Eval every N batches")
    parser.add_argument("--save-interval", type=int, default=1000, help="Save every N batches")
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    parser.add_argument("--model-dir", type=str, default=None, help="Model output directory")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    run = TrainingRun(
        num_batches=args.batches,
        games_per_batch=args.games_per_batch,
        num_workers=args.workers,
        lr=args.lr,
        temperature=args.temperature,
        eval_interval=args.eval_interval,
        save_interval=args.save_interval,
        resume_from=args.resume,
        model_dir=args.model_dir,
    )

    try:
        result = run.run()
        print(f"\nTraining complete: {json.dumps(result, indent=2)}")
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        run.cancel()


if __name__ == "__main__":
    main()
