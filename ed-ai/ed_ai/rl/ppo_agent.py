"""PPO agent for Everdell — handles action selection and policy updates."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn as nn

from ed_ai.rl.network import EverdellNetwork


@dataclass
class Transition:
    """Single step of experience."""
    state: np.ndarray
    action: int
    log_prob: float
    value: float
    reward: float
    done: bool
    action_mask: np.ndarray


@dataclass
class Trajectory:
    """Complete trajectory for one player in one game."""
    transitions: list[Transition] = field(default_factory=list)
    final_score: float = 0.0

    def add(self, state: np.ndarray, action: int, log_prob: float,
            value: float, action_mask: np.ndarray) -> None:
        """Add a step (reward/done filled later)."""
        self.transitions.append(Transition(
            state=state, action=action, log_prob=log_prob,
            value=value, reward=0.0, done=False, action_mask=action_mask,
        ))

    def finalize(self, final_score: float, max_possible_score: float = 100.0) -> None:
        """Set terminal reward as normalized final VP score."""
        self.final_score = final_score
        normalized = final_score / max_possible_score
        if self.transitions:
            self.transitions[-1].reward = normalized
            self.transitions[-1].done = True


class PPOAgent:
    """PPO agent with GAE and clipped surrogate objective."""

    def __init__(
        self,
        network: EverdellNetwork,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        ppo_epochs: int = 4,
        minibatch_size: int = 64,
    ):
        self.network = network
        self.optimizer = torch.optim.Adam(network.parameters(), lr=lr)
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.ppo_epochs = ppo_epochs
        self.minibatch_size = minibatch_size
        self.device = next(network.parameters()).device

    def select_action(
        self,
        state: np.ndarray,
        action_mask: np.ndarray,
        temperature: float = 1.0,
        deterministic: bool = False,
    ) -> tuple[int, float, float]:
        """Select action using current policy.

        Returns: (action_idx, log_prob, value)
        """
        state_t = torch.from_numpy(state).float().to(self.device)
        mask_t = torch.from_numpy(action_mask).float().to(self.device)
        return self.network.get_action(state_t, mask_t, temperature, deterministic)

    def update(self, trajectories: list[Trajectory]) -> dict[str, float]:
        """PPO update from collected trajectories.

        Returns dict of training metrics.
        """
        # Flatten all transitions and compute GAE
        states, actions, old_log_probs, returns, advantages, masks = (
            self._prepare_batch(trajectories)
        )

        if len(states) == 0:
            return {"policy_loss": 0, "value_loss": 0, "entropy": 0, "batch_size": 0}

        # Convert to tensors
        states_t = torch.from_numpy(states).float().to(self.device)
        actions_t = torch.from_numpy(actions).long().to(self.device)
        old_log_probs_t = torch.from_numpy(old_log_probs).float().to(self.device)
        returns_t = torch.from_numpy(returns).float().to(self.device)
        advantages_t = torch.from_numpy(advantages).float().to(self.device)
        masks_t = torch.from_numpy(masks).float().to(self.device)

        # Normalize advantages
        if len(advantages_t) > 1:
            advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        num_updates = 0

        for _ in range(self.ppo_epochs):
            # Shuffle and split into minibatches
            indices = np.random.permutation(len(states))
            for start in range(0, len(indices), self.minibatch_size):
                end = start + self.minibatch_size
                mb_idx = indices[start:end]
                mb_idx_t = torch.from_numpy(mb_idx).long().to(self.device)

                mb_states = states_t[mb_idx_t]
                mb_actions = actions_t[mb_idx_t]
                mb_old_log_probs = old_log_probs_t[mb_idx_t]
                mb_returns = returns_t[mb_idx_t]
                mb_advantages = advantages_t[mb_idx_t]
                mb_masks = masks_t[mb_idx_t]

                # Evaluate current policy on old actions
                new_log_probs, values, entropy = self.network.evaluate_actions(
                    mb_states, mb_actions, mb_masks
                )

                # PPO clipped surrogate
                ratio = (new_log_probs - mb_old_log_probs).exp()
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * mb_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss (clipped)
                value_loss = nn.functional.mse_loss(values, mb_returns)

                # Entropy bonus
                entropy_loss = -entropy.mean()

                # Total loss
                loss = (
                    policy_loss
                    + self.value_coef * value_loss
                    + self.entropy_coef * entropy_loss
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += -entropy_loss.item()
                num_updates += 1

        n = max(num_updates, 1)
        return {
            "policy_loss": total_policy_loss / n,
            "value_loss": total_value_loss / n,
            "entropy": total_entropy / n,
            "batch_size": len(states),
        }

    def _prepare_batch(
        self, trajectories: list[Trajectory]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Compute GAE advantages and flatten trajectories into arrays."""
        all_states = []
        all_actions = []
        all_log_probs = []
        all_returns = []
        all_advantages = []
        all_masks = []

        for traj in trajectories:
            if not traj.transitions:
                continue

            T = len(traj.transitions)
            values = np.array([t.value for t in traj.transitions], dtype=np.float32)
            rewards = np.array([t.reward for t in traj.transitions], dtype=np.float32)
            dones = np.array([t.done for t in traj.transitions], dtype=np.float32)

            # GAE computation
            advantages = np.zeros(T, dtype=np.float32)
            last_gae = 0.0
            for t in reversed(range(T)):
                if t == T - 1:
                    next_value = 0.0  # Terminal
                else:
                    next_value = values[t + 1]
                delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
                last_gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * last_gae
                advantages[t] = last_gae

            returns = advantages + values

            for i, t in enumerate(traj.transitions):
                all_states.append(t.state)
                all_actions.append(t.action)
                all_log_probs.append(t.log_prob)
                all_returns.append(returns[i])
                all_advantages.append(advantages[i])
                all_masks.append(t.action_mask)

        if not all_states:
            empty = np.array([], dtype=np.float32)
            return empty, empty, empty, empty, empty, empty

        return (
            np.array(all_states, dtype=np.float32),
            np.array(all_actions, dtype=np.int64),
            np.array(all_log_probs, dtype=np.float32),
            np.array(all_returns, dtype=np.float32),
            np.array(all_advantages, dtype=np.float32),
            np.array(all_masks, dtype=np.float32),
        )
