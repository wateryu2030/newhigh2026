# -*- coding: utf-8 -*-
"""
训练模块：封装 train_rl_model()，保存到 models/rl_trader.zip；记录 reward/loss 供 UI。
"""
from __future__ import annotations
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

# 训练曲线记录（供 /api/rl/performance 等读取）
TRAIN_LOG_DIR = os.path.join(_ROOT, "output", "rl_training")
TRAIN_LOG_JSON = os.path.join(TRAIN_LOG_DIR, "train_log.json")
MODEL_SAVE_PATH = os.path.join(_ROOT, "models", "rl_trader.zip")


def train_rl_model(
    symbol: str = "000001",
    start_date: str = "2023-01-01",
    end_date: str = "2024-12-31",
    total_timesteps: int = 30_000,
    save_path: Optional[str] = None,
    window: int = 20,
) -> Dict[str, Any]:
    """
    单只股票日线训练 PPO，保存模型与训练曲线。
    :return: {"success", "model_path", "total_timesteps", "train_log_path", "error"}
    """
    save_path = save_path or MODEL_SAVE_PATH
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    os.makedirs(TRAIN_LOG_DIR, exist_ok=True)

    try:
        from data.data_loader import load_kline
        from database.duckdb_backend import get_db_backend
        from rl_trading.env.trading_env import TradingEnv
        from rl_trading.models.rl_model import RLModelWrapper
        from stable_baselines3.common.vec_env import DummyVecEnv
        from stable_baselines3.common.callbacks import BaseCallback
    except ImportError as e:
        logger.exception("依赖缺失: %s", e)
        return {"success": False, "error": str(e), "model_path": None}

    df = load_kline(symbol, start_date, end_date, source="database")
    if df is None or len(df) < 100:
        return {"success": False, "error": "K 线数据不足或未找到", "model_path": None}

    if "date" not in df.columns and df.index is not None:
        df["date"] = df.index.astype(str).str[:10]
    df = df.rename(columns={c: c.lower() for c in df.columns if isinstance(c, str)})
    if "close" not in df.columns and "收盘" in df.columns:
        df["close"] = df["收盘"]

    rewards: List[float] = []
    episodes: List[int] = []

    class LogCallback(BaseCallback):
        def _on_step(self) -> bool:
            if "reward" in self.locals and self.locals.get("reward") is not None:
                rewards.append(float(self.locals["reward"]))
            return True

    try:
        env = TradingEnv(df, window=window)
        env = DummyVecEnv([lambda: env])
        wrapper = RLModelWrapper(total_timesteps=total_timesteps)
        callback = LogCallback()
        wrapper.train(env, total_timesteps=total_timesteps, save_path=save_path, callback=callback)
    except Exception as e:
        logger.exception("训练失败: %s", e)
        return {"success": False, "error": str(e), "model_path": None}

    # 写入训练曲线（简化：按步记录 reward）
    log_data = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "total_timesteps": total_timesteps,
        "rewards": rewards[-5000:] if len(rewards) > 5000 else rewards,
        "episodes": list(range(len(rewards))),
    }
    try:
        with open(TRAIN_LOG_JSON, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("写入 train_log 失败: %s", e)

    return {
        "success": True,
        "model_path": save_path,
        "total_timesteps": total_timesteps,
        "train_log_path": TRAIN_LOG_JSON,
        "error": None,
    }
