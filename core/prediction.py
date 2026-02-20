# -*- coding: utf-8 -*-
"""
未来趋势判断模块。
基于近期 K 线与均线给出趋势方向与置信度，供前端展示（概率展示，非点预测）。
"""
from typing import Dict, Any
import pandas as pd


def predict_trend(df: pd.DataFrame) -> Dict[str, Any]:
    """
    根据最近 K 线与均线计算趋势方向与得分。

    输入：
        df: 至少包含 close，以及 ma5, ma20（若无则自动计算）的 DataFrame。

    输出：
        {"trend": "UP"|"DOWN"|"SIDEWAYS", "score": float}
        数值为 float，无 NaN；score 约在 [-0.3, 0.7] 区间。
    """
    if df is None or len(df) < 5:
        return {"trend": "SIDEWAYS", "score": 0.0}

    df = df.copy()
    if "ma5" not in df.columns and "close" in df.columns:
        df["ma5"] = df["close"].rolling(5, min_periods=1).mean()
    if "ma20" not in df.columns and "close" in df.columns:
        df["ma20"] = df["close"].rolling(20, min_periods=1).mean()

    df = df.dropna(subset=["ma5", "ma20", "close"])
    if len(df) < 5:
        return {"trend": "SIDEWAYS", "score": 0.0}

    ma5 = float(df["ma5"].iloc[-1])
    ma20 = float(df["ma20"].iloc[-1])
    close = float(df["close"].iloc[-1])
    close_5 = float(df["close"].iloc[-5])

    trend_score = 0.0
    if ma5 > ma20:
        trend_score += 0.4
    if close > ma5:
        trend_score += 0.3
    if close_5 != 0:
        momentum = (close - close_5) / close_5
        momentum = max(-0.3, min(0.3, momentum))
        trend_score += momentum

    if trend_score > 0.5:
        trend = "UP"
    elif trend_score < -0.2:
        trend = "DOWN"
    else:
        trend = "SIDEWAYS"

    return {
        "trend": trend,
        "score": round(float(trend_score), 2),
    }
