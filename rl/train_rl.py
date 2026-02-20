# -*- coding: utf-8 -*-
"""
RL 交易智能体训练：使用 stable-baselines3 PPO 在 TradingEnv 上训练。
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

import numpy as np
from rl.env_trading import TradingEnv


def train(
    data: np.ndarray = None,
    total_timesteps: int = 10_000,
    save_path: str = "rl_trader",
    seed: int = 42,
):
    try:
        from stable_baselines3 import PPO
    except ImportError:
        raise ImportError("需要安装: pip install stable-baselines3")

    if data is None:
        data = np.cumsum(np.random.randn(1000) * 0.01) + 100
    env = TradingEnv(data)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        seed=seed,
    )
    model.learn(total_timesteps=total_timesteps)
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    model.save(save_path)
    print(f"Model saved: {save_path}")
    return model


if __name__ == "__main__":
    train()
