"""
Simulation World — 市场模拟环境
Compatible with RL training (PPO, SAC). API: reset(), step(), reward.
"""
import random
from typing import Any, Dict, List, Tuple

import numpy as np


class MarketSimEnv:
    """
    Simple market simulation for RL. State: price/features; action: -1/0/1 (sell/hold/buy);
    reward: PnL or Sharpe-like.
    """

    def __init__(
        self,
        max_steps: int = 252,
        initial_balance: float = 10000.0,
        reward_type: str = "returns",
    ):
        self.max_steps = max_steps
        self.initial_balance = initial_balance
        self.reward_type = reward_type
        self._step = 0
        self._balance = initial_balance
        self._position = 0.0
        self._price_history: List[float] = []
        self._returns_history: List[float] = []

    def reset(
        self,
        *,
        seed: int | None = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset env. Returns (observation, info)."""
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        self._step = 0
        self._balance = self.initial_balance
        self._position = 0.0
        self._price_history = [100.0]
        self._returns_history = []
        obs = self._get_obs()
        info = {"balance": self._balance, "position": self._position}
        return obs, info

    def _get_obs(self) -> np.ndarray:
        """Observation: recent returns + position norm."""
        if len(self._returns_history) < 5:
            rets = np.zeros(5)
            rets[: len(self._returns_history)] = self._returns_history
        else:
            rets = np.array(self._returns_history[-5:], dtype=np.float32)
        pos = np.array([self._position / max(self._balance, 1)], dtype=np.float32)
        return np.concatenate([rets, pos])

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        action: -1 sell, 0 hold, 1 buy (discrete). Returns (obs, reward, terminated, truncated, info).
        """
        price = self._price_history[-1]
        ret = np.random.randn() * 0.02
        new_price = price * (1 + ret)
        self._price_history.append(new_price)
        self._returns_history.append(ret)
        if action == 1 and self._balance >= price:
            self._position += price
            self._balance -= price
        elif action == -1 and self._position > 0:
            self._balance += self._position
            self._position = 0.0
        self._step += 1
        reward = ret if self.reward_type == "returns" else 0.0
        if self.reward_type == "pnl" and self._position != 0:
            reward = ret * (self._position / price)
        obs = self._get_obs()
        terminated = self._step >= self.max_steps
        truncated = False
        info = {
            "balance": self._balance,
            "position": self._position,
            "price": new_price,
            "step": self._step,
        }
        return obs, reward, terminated, truncated, info

    @property
    def observation_space(self) -> Dict[str, Any]:
        return {"shape": (6,)}

    @property
    def action_space(self) -> Dict[str, Any]:
        return {"n": 3}


def make_env(max_steps: int = 252, reward_type: str = "returns") -> MarketSimEnv:
    """Factory for RL compatibility."""
    return MarketSimEnv(max_steps=max_steps, reward_type=reward_type)
