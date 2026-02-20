# -*- coding: utf-8 -*-
"""
RL 交易环境：状态 = 价格/技术指标/仓位，动作 = 空仓/买入/卖出，奖励 = 收益 - 风险惩罚。
使用 gymnasium，与 stable-baselines3 兼容。
"""
import gymnasium as gym
import numpy as np
from typing import Any, Tuple, Optional


class TradingEnv(gym.Env):
    """
    状态：价格 + 技术指标 + 仓位（共 obs_dim 维）
    动作：0 空仓 1 买入 2 卖出
    奖励：收益 - 风险惩罚（可配置）
    """

    def __init__(
        self,
        data: np.ndarray,
        obs_dim: int = 10,
        reward_scale: float = 1.0,
        risk_penalty: float = 0.1,
    ):
        """
        :param data: 价格序列，或 (T, obs_dim) 特征矩阵；若 1维则自动构造简单观测
        :param obs_dim: 观测空间维度
        :param reward_scale: 收益缩放
        :param risk_penalty: 仓位/波动惩罚系数
        """
        super().__init__()
        self._raw = np.asarray(data, dtype=np.float64)
        if self._raw.ndim == 1:
            self._raw = self._raw.reshape(-1, 1)
        self.obs_dim = obs_dim
        self.reward_scale = reward_scale
        self.risk_penalty = risk_penalty
        self.action_space = gym.spaces.Discrete(3)  # 0 空仓 1 买 2 卖
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float64,
        )
        self.step_index = 0
        self.position = 0
        self._entry_price: Optional[float] = None

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.step_index = 0
        self.position = 0
        self._entry_price = None
        return self._get_obs(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        price = self._get_price()
        reward = 0.0
        if action == 1:
            self.position = 1
            self._entry_price = price
        elif action == 2:
            if self.position == 1 and self._entry_price is not None:
                reward = self.reward_scale * (price - self._entry_price) / (self._entry_price or 1e-8)
            self.position = 0
            self._entry_price = None
        if self.position != 0 and self._entry_price is not None:
            reward = self.reward_scale * (price - self._entry_price) / (self._entry_price or 1e-8)
        reward -= self.risk_penalty * abs(self.position)
        self.step_index += 1
        terminated = self.step_index >= len(self._raw) - 1
        truncated = False
        return self._get_obs(), float(reward), terminated, truncated, {}

    def _get_price(self) -> float:
        row = self._raw[min(self.step_index, len(self._raw) - 1)]
        return float(row[0] if row.size else 0.0)

    def _get_obs(self) -> np.ndarray:
        idx = min(self.step_index, len(self._raw) - 1)
        row = self._raw[idx]
        n = min(self.obs_dim - 1, row.size)
        out = np.zeros(self.obs_dim, dtype=np.float64)
        out[:n] = row[:n]
        out[-1] = float(self.position)
        return out
