# -*- coding: utf-8 -*-
"""
Gymnasium 交易环境：状态（价格/技术指标/仓位/资金）、动作（空仓/买/卖）、奖励（收益+风险惩罚）。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    gym = None
    spaces = None


def _compute_indicators(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """在 DataFrame 上计算简单技术指标并归一化。"""
    d = df.copy()
    if "close" not in d.columns and len(d.columns):
        c = "close" if "close" in d.columns else d.columns[d.columns.str.contains("close", case=False)][0] if len(d.columns) else None
        if c is None and len(d.columns) >= 5:
            d["close"] = d.iloc[:, 4]
    close = d["close"] if "close" in d.columns else d.iloc[:, -1]
    d["close"] = close.astype(float)
    d["ret"] = d["close"].pct_change().fillna(0)
    d["ma"] = d["close"].rolling(window, min_periods=1).mean()
    d["price_ratio"] = (d["close"] / d["ma"]).fillna(1.0) - 1.0
    delta = d["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(14, min_periods=1).mean()
    avg_loss = loss.rolling(14, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    d["rsi"] = (100 - (100 / (1 + rs))).fillna(50) / 100.0 - 0.5
    return d


class TradingEnv:
    """
    Gymnasium 兼容环境。
    状态: 价格相对均线、收益率、RSI 归一化、仓位、资金占比 等
    动作: 0=空仓, 1=买入, 2=卖出
    奖励: 收益率 - 回撤惩罚
    """

    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 1e6,
        window: int = 20,
        state_dim: int = 8,
        max_position_pct: float = 1.0,
        seed: Optional[int] = None,
    ):
        if gym is None or spaces is None:
            raise ImportError("请安装 gymnasium: pip install gymnasium")
        self.df = _compute_indicators(df.copy(), window=window)
        self.df = self.df.dropna(subset=["close", "price_ratio", "rsi"]).reset_index(drop=True)
        if len(self.df) < window + 5:
            raise ValueError("数据长度不足，需要至少 window+5 根 K 线")
        self.window = window
        self.state_dim = state_dim
        self.initial_balance = initial_balance
        self.max_position_pct = max_position_pct
        self._seed = seed
        # 动作: 0 hold, 1 buy, 2 sell
        self.action_space = spaces.Discrete(3)
        # 状态: 归一化到约 [-1,1]
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(state_dim,),
            dtype=np.float32,
        )
        self._pos = 0.0
        self._cash = initial_balance
        self._step = 0
        self._peak = initial_balance
        self._history: list = []

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        if seed is not None:
            np.random.seed(seed)
        self._step = self.window
        self._cash = self.initial_balance
        self._pos = 0.0
        self._peak = self.initial_balance
        self._history = []
        obs = self._get_obs()
        info = {"balance": self._cash, "position": self._pos}
        return obs, info

    def _get_obs(self) -> np.ndarray:
        row = self.df.iloc[self._step]
        price = float(row["close"])
        ret = float(row.get("ret", 0))
        price_ratio = float(row.get("price_ratio", 0))
        rsi = float(row.get("rsi", 0))
        pos_pct = self._pos * price / (self._cash + self._pos * price) if (self._cash + self._pos * price) > 0 else 0.0
        pos_pct = max(0, min(1, pos_pct / self.max_position_pct))
        cash_pct = self._cash / (self._cash + self._pos * price) if (self._cash + self._pos * price) > 0 else 0.5
        # 过去几根 ret 的均值/波动
        start = max(0, self._step - 5)
        recent = self.df.iloc[start : self._step + 1]["ret"].astype(float)
        mean_ret = recent.mean() if len(recent) else 0.0
        std_ret = recent.std() if len(recent) and recent.std() > 0 else 1e-6
        obs = np.array([
            np.clip(price_ratio, -1, 1),
            np.clip(rsi, -0.5, 0.5),
            np.clip(ret * 100, -0.1, 0.1),
            pos_pct * 2 - 1,
            cash_pct * 2 - 1,
            np.clip(mean_ret * 100, -0.05, 0.05),
            np.clip(std_ret * 100, 0, 0.1),
            (self._step - self.window) / max(1, len(self.df) - self.window) * 2 - 1,
        ], dtype=np.float32)
        if self.state_dim > 8:
            obs = np.resize(obs, self.state_dim)
        return obs

    def step(
        self,
        action: int,
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        price = float(self.df.iloc[self._step]["close"])
        prev_value = self._cash + self._pos * price
        # 简化：按固定比例调仓
        target_pct = 0.0
        if action == 1:
            target_pct = self.max_position_pct
        elif action == 2:
            target_pct = 0.0
        else:
            target_pct = self._pos * price / prev_value if prev_value > 0 else 0.0
        target_value = prev_value * target_pct
        self._pos = target_value / price if price > 0 else 0.0
        self._cash = prev_value - self._pos * price
        self._step += 1
        if self._step >= len(self.df) - 1:
            next_price = float(self.df.iloc[-1]["close"])
        else:
            next_price = float(self.df.iloc[self._step]["close"])
        new_value = self._cash + self._pos * next_price
        ret = (new_value - prev_value) / prev_value if prev_value > 0 else 0.0
        self._peak = max(self._peak, new_value)
        dd = (self._peak - new_value) / self._peak if self._peak > 0 else 0.0
        reward = ret - 0.5 * dd
        self._history.append({
            "step": self._step,
            "action": action,
            "price": next_price,
            "value": new_value,
            "return": ret,
            "reward": reward,
        })
        terminated = self._step >= len(self.df) - 1
        truncated = False
        obs = self._get_obs() if not terminated else self._get_obs()
        info = {
            "balance": self._cash,
            "position": self._pos,
            "value": new_value,
            "return": ret,
            "reward": reward,
        }
        return obs, float(reward), terminated, truncated, info

    def get_history(self) -> list:
        return list(self._history)
