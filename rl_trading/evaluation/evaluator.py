# -*- coding: utf-8 -*-
"""
评估模块：回测 RL 策略，输出收益曲线、夏普、回撤等，供 UI 展示。
"""
from __future__ import annotations
import json
import logging
import math
import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

MODEL_SAVE_PATH = os.path.join(_ROOT, "models", "rl_trader.zip")
PERF_LOG_PATH = os.path.join(_ROOT, "output", "rl_training", "performance.json")


def evaluate_rl_model(
    symbol: str = "000001",
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
    model_path: Optional[str] = None,
    window: int = 20,
) -> Dict[str, Any]:
    """
    在指定区间用已训练模型回测，返回净值曲线、夏普、最大回撤、交易统计。
    """
    model_path = model_path or MODEL_SAVE_PATH
    if not os.path.exists(model_path):
        return {"error": "模型文件不存在", "curve": [], "sharpe": 0, "max_drawdown": 0, "total_return": 0}

    try:
        from data.data_loader import load_kline
        from rl_trading.env.trading_env import TradingEnv
        from rl_trading.models.rl_model import RLModelWrapper
    except ImportError as e:
        return {"error": str(e), "curve": [], "sharpe": 0, "max_drawdown": 0, "total_return": 0}

    df = load_kline(symbol, start_date, end_date, source="database")
    if df is None or len(df) < 100:
        return {"error": "K 线数据不足", "curve": [], "sharpe": 0, "max_drawdown": 0, "total_return": 0}

    df = df.rename(columns={c: c.lower() for c in df.columns if isinstance(c, str)})
    if "close" not in df.columns and "收盘" in df.columns:
        df["close"] = df["收盘"]
    if "date" not in df.columns and df.index is not None:
        df["date"] = df.index.astype(str).str[:10]

    try:
        env = TradingEnv(df, window=window)
        wrapper = RLModelWrapper(model_path=model_path)
        obs, info = env.reset()
        curve = [{"step": 0, "date": str(df.iloc[env.window]["date"])[:10], "value": 1.0, "action": 0}]
        actions_count = {0: 0, 1: 0, 2: 0}
        initial_value = info.get("balance", 1e6) + info.get("position", 0) * float(df.iloc[env.window]["close"])
        while True:
            action, _ = wrapper.predict(obs)
            actions_count[action] = actions_count.get(action, 0) + 1
            obs, reward, term, trunc, info = env.step(action)
            value = info.get("value", initial_value)
            step = env._step
            if step < len(df):
                d = str(df.iloc[step]["date"])[:10]
            else:
                d = str(df.iloc[-1]["date"])[:10]
            curve.append({"step": step, "date": d, "value": value / initial_value, "action": action})
            if term or trunc:
                break
    except Exception as e:
        logger.exception("evaluate_rl_model: %s", e)
        return {"error": str(e), "curve": [], "sharpe": 0, "max_drawdown": 0, "total_return": 0}

    values = [c["value"] for c in curve]
    returns = [0.0] + [(values[i] - values[i - 1]) / values[i - 1] if values[i - 1] else 0 for i in range(1, len(values))]
    total_return = values[-1] / values[0] - 1.0 if values[0] else 0.0
    mean_ret = np.mean(returns)
    std_ret = np.std(returns)
    sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

    out = {
        "curve": curve,
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "total_return": round(total_return, 4),
        "actions": actions_count,
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "error": None,
    }
    try:
        os.makedirs(os.path.dirname(PERF_LOG_PATH) or ".", exist_ok=True)
        with open(PERF_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("写入 performance.json 失败: %s", e)
    return out
