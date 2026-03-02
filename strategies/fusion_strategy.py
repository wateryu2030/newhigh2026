# -*- coding: utf-8 -*-
"""
游资+趋势融合策略：龙虎榜信号 + 趋势过滤 + 情绪匹配 + 动态仓位，统一评分 final_score > 75 才买入。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

import pandas as pd

from strategies.trend_filter import trend_score_and_pass
from strategies.yz_strategy import yz_signal_for_date, yz_signal_for_symbol_date


# 情绪匹配得分：启动/加速=100，其余=0 或低分
EMOTION_MATCH_SCORE = {"启动": 100, "加速": 100, "冰点": 20, "高潮": 30, "极致高潮": 20, "退潮": 0}

# 仓位：加速 0.6，启动 0.4，其余 0.2
POSITION_BY_EMOTION = {"加速": 0.6, "启动": 0.4, "冰点": 0.2, "高潮": 0.2, "极致高潮": 0.2, "退潮": 0.1}


def position_by_emotion(emotion_cycle: Optional[str]) -> float:
    if not emotion_cycle:
        return 0.2
    return POSITION_BY_EMOTION.get(emotion_cycle, 0.2)


def emotion_match_score(emotion_cycle: Optional[str]) -> float:
    if not emotion_cycle:
        return 0.0
    return float(EMOTION_MATCH_SCORE.get(emotion_cycle, 0))


def fusion_score(
    fund_score: float,
    lhb_score: float,
    trend_score: float,
    emotion_match: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    final_score = 0.4*fund_score + 0.3*lhb_score + 0.2*trend_score + 0.1*emotion_match
    各分 0-100。
    """
    w = weights or {"fund": 0.4, "lhb": 0.3, "trend": 0.2, "emotion": 0.1}
    return (
        w.get("fund", 0.4) * min(100, max(0, fund_score))
        + w.get("lhb", 0.3) * min(100, max(0, lhb_score))
        + w.get("trend", 0.2) * min(100, max(0, trend_score))
        + w.get("emotion", 0.1) * min(100, max(0, emotion_match))
    )


def fusion_signal(
    date_ymd: str,
    symbol: Optional[str],
    bars_df: Optional[pd.DataFrame],
    emotion_cycle: Optional[str],
    score_threshold: float = 75.0,
) -> Dict[str, Any]:
    """
    融合信号：游资 + 趋势 + 情绪，仅当 final_score > score_threshold 且情绪为启动/加速时允许买入。
    :param date_ymd: YYYYMMDD
    :param symbol: 股票代码（可选）
    :param bars_df: 该股或指数 K 线，用于趋势过滤
    :param emotion_cycle: 当日情绪周期
    :param score_threshold: 最终得分阈值
    :return: {"allow_buy", "final_score", "position", "fund_score", "lhb_score", "trend_score", "emotion_match"}
    """
    yz = yz_signal_for_date(date_ymd, symbol=symbol, emotion_cycle=emotion_cycle)
    fund_score = yz.get("fund_score", 0) or 0
    lhb_score = yz.get("lhb_score", 0) or 0
    trend_score = 0.0
    if bars_df is not None and len(bars_df) > 0:
        trend_result = trend_score_and_pass(bars_df)
        trend_score = trend_result.get("trend_score", 0) or 0
    emotion_match = emotion_match_score(emotion_cycle)
    final = fusion_score(fund_score, lhb_score, trend_score, emotion_match)
    position = position_by_emotion(emotion_cycle)
    emotion_ok = emotion_cycle in ("启动", "加速")
    allow_buy = final >= score_threshold and emotion_ok
    return {
        "allow_buy": allow_buy,
        "final_score": round(final, 2),
        "position": position,
        "fund_score": fund_score,
        "lhb_score": lhb_score,
        "trend_score": trend_score,
        "emotion_match": emotion_match,
    }


class FusionStrategy:
    """可接入回测的融合策略：需注入每日情绪与 LHB 数据（或使用当日接口）。"""

    def __init__(self, score_threshold: float = 75.0):
        self.score_threshold = score_threshold

    def generate_signals(
        self,
        df: pd.DataFrame,
        emotion_cycle_by_date: Optional[Dict[str, str]] = None,
        date_ymd: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据 K 线生成信号。若提供 emotion_cycle_by_date 则按日取情绪；否则用 date_ymd 或最后一天。
        """
        if df is None or len(df) < 30:
            return []
        signals = []
        # 按最后一根 K 线做一次融合判断
        last_date = df.index[-1] if hasattr(df.index, "__getitem__") else None
        if last_date is not None:
            dt_str = str(last_date)[:10].replace("/", "-")
            ymd = dt_str.replace("-", "")
            emotion = (emotion_cycle_by_date or {}).get(dt_str) or (emotion_cycle_by_date or {}).get(ymd)
            if date_ymd:
                emotion = (emotion_cycle_by_date or {}).get(date_ymd[:4] + "-" + date_ymd[4:6] + "-" + date_ymd[6:8]) or emotion
            res = fusion_signal(ymd, None, df, emotion, score_threshold=self.score_threshold)
            if res.get("allow_buy"):
                close = df["close"] if "close" in df.columns else df["收盘"]
                price = float(close.iloc[-1])
                signals.append({
                    "date": dt_str,
                    "type": "BUY",
                    "price": price,
                    "reason": "fusion_score={}".format(res.get("final_score")),
                })
        return signals
