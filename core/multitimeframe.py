# -*- coding: utf-8 -*-
"""
多周期共振：日线趋势 + 30m 回调结束 + 5m 突破 → 买点质量高。
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np


def multi_tf_signal(
    daily: pd.DataFrame,
    m30: Optional[pd.DataFrame] = None,
    m5: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    多周期共振信号。
    逻辑：日线趋势向上 + （30m 回调结束 / RSI<40 后回升）+ （5m 突破 / 收盘>MA20）
    :param daily: 日线 OHLCV，需含 close
    :param m30: 30 分钟 K 线（可选）
    :param m5: 5 分钟 K 线（可选）
    :return: {"trigger": bool, "trend_ok": bool, "pullback_ok": bool, "trigger_ok": bool, "reason": str}
    """
    if daily is None or len(daily) < 60:
        return {"trigger": False, "trend_ok": False, "pullback_ok": False, "trigger_ok": False, "reason": "日线数据不足"}
    d = daily.copy()
    if "close" not in d.columns:
        return {"trigger": False, "trend_ok": False, "pullback_ok": False, "trigger_ok": False, "reason": "无 close"}
    d["ma20"] = d["close"].rolling(20, min_periods=1).mean()
    d["ma60"] = d["close"].rolling(60, min_periods=1).mean()
    trend_ok = bool(d["ma20"].iloc[-1] > d["ma60"].iloc[-1])

    pullback_ok = True
    if m30 is not None and len(m30) >= 14:
        m = m30.copy()
        delta = m["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(14, min_periods=1).mean()
        avg_loss = loss.rolling(14, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        # 回调结束：RSI 曾<40 且当前回升
        rsi_low = rsi.rolling(5).min()
        pullback_ok = bool(rsi_low.iloc[-2] <= 40 and rsi.iloc[-1] > rsi.iloc[-2])

    trigger_ok = True
    if m5 is not None and len(m5) >= 20:
        m = m5.copy()
        m["ma20"] = m["close"].rolling(20, min_periods=1).mean()
        trigger_ok = bool(m["close"].iloc[-1] > m["ma20"].iloc[-1])

    trigger = trend_ok and pullback_ok and trigger_ok
    reason = []
    if trend_ok:
        reason.append("日线趋势向上")
    else:
        reason.append("日线趋势向下")
    if pullback_ok:
        reason.append("30m回调结束")
    else:
        reason.append("30m未回调/未结束")
    if trigger_ok:
        reason.append("5m突破")
    else:
        reason.append("5m未突破")
    return {
        "trigger": trigger,
        "trend_ok": trend_ok,
        "pullback_ok": pullback_ok,
        "trigger_ok": trigger_ok,
        "reason": " | ".join(reason),
    }
