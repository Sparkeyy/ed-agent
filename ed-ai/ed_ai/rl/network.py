"""Actor-critic MLP network for Everdell RL agent.

~350K parameters, designed for fast CPU inference (<1ms).
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from ed_ai.rl.state_encoder import STATE_SIZE
from ed_ai.rl.action_encoder import ACTION_SPACE_SIZE


class EverdellNetwork(nn.Module):
    """Actor-critic network with action masking.

    Architecture:
        Input(STATE_SIZE) → 512 → 256 → policy head (ACTION_SPACE_SIZE) + value head (1)
    """

    def __init__(self, state_size: int = STATE_SIZE, action_size: int = ACTION_SPACE_SIZE):
        super().__init__()
        self.state_size = state_size
        self.action_size = action_size

        # Shared backbone
        self.fc1 = nn.Linear(state_size, 512)
        self.ln1 = nn.LayerNorm(512)
        self.fc2 = nn.Linear(512, 256)
        self.ln2 = nn.LayerNorm(256)

        # Policy head
        self.policy_head = nn.Linear(256, action_size)

        # Value head
        self.value_head = nn.Linear(256, 1)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        for m in [self.fc1, self.fc2]:
            nn.init.orthogonal_(m.weight, gain=2**0.5)
            nn.init.zeros_(m.bias)
        nn.init.orthogonal_(self.policy_head.weight, gain=0.01)
        nn.init.zeros_(self.policy_head.bias)
        nn.init.orthogonal_(self.value_head.weight, gain=1.0)
        nn.init.zeros_(self.value_head.bias)

    def forward(
        self, state: torch.Tensor, action_mask: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass.

        Args:
            state: (batch, STATE_SIZE) float tensor
            action_mask: (batch, ACTION_SPACE_SIZE) binary mask (1=valid, 0=invalid)

        Returns:
            log_probs: (batch, ACTION_SPACE_SIZE) log probabilities
            value: (batch, 1) state value estimate
        """
        x = F.relu(self.ln1(self.fc1(state)))
        x = F.relu(self.ln2(self.fc2(x)))

        # Policy
        logits = self.policy_head(x)
        if action_mask is not None:
            # Set invalid actions to very negative logit
            logits = logits.masked_fill(action_mask == 0, -1e8)
        log_probs = F.log_softmax(logits, dim=-1)

        # Value
        value = self.value_head(x)

        return log_probs, value

    def get_action(
        self,
        state: torch.Tensor,
        action_mask: torch.Tensor,
        temperature: float = 1.0,
        deterministic: bool = False,
    ) -> tuple[int, float, float]:
        """Select an action given state and mask.

        Args:
            state: (STATE_SIZE,) tensor (unbatched)
            action_mask: (ACTION_SPACE_SIZE,) binary mask
            temperature: Softmax temperature (lower = greedier)
            deterministic: If True, always pick highest prob action

        Returns:
            action_idx: Selected action index
            log_prob: Log probability of selected action
            value: State value estimate
        """
        with torch.no_grad():
            state_batch = state.unsqueeze(0)
            mask_batch = action_mask.unsqueeze(0)

            log_probs, value = self.forward(state_batch, mask_batch)

            if temperature != 1.0:
                logits = self.policy_head(
                    F.relu(self.ln2(self.fc2(
                        F.relu(self.ln1(self.fc1(state_batch)))
                    )))
                )
                logits = logits.masked_fill(mask_batch == 0, -1e8)
                logits = logits / temperature
                log_probs = F.log_softmax(logits, dim=-1)

            probs = log_probs.exp().squeeze(0)

            if deterministic:
                action_idx = probs.argmax().item()
            else:
                action_idx = torch.multinomial(probs, 1).item()

            return action_idx, log_probs[0, action_idx].item(), value.item()

    def evaluate_actions(
        self,
        states: torch.Tensor,
        actions: torch.Tensor,
        action_masks: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate actions for PPO update.

        Args:
            states: (batch, STATE_SIZE)
            actions: (batch,) long tensor of action indices
            action_masks: (batch, ACTION_SPACE_SIZE) binary masks

        Returns:
            log_probs: (batch,) log probs of the taken actions
            values: (batch,) value estimates
            entropy: (batch,) policy entropy
        """
        all_log_probs, values = self.forward(states, action_masks)

        # Log prob of taken action
        log_probs = all_log_probs.gather(1, actions.unsqueeze(1)).squeeze(1)

        # Entropy of the distribution
        probs = all_log_probs.exp()
        # Only compute entropy over valid actions
        entropy = -(probs * all_log_probs).sum(dim=-1)

        return log_probs, values.squeeze(-1), entropy

    def param_count(self) -> int:
        return sum(p.numel() for p in self.parameters())
