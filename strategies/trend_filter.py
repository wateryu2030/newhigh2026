# -*- coding: utf-8 -*-
"""
趋势过滤：价格 > MA20、MA20 上行、MACD 不死叉，用于过滤低质量游资信号。
"""
from __future__ import annotations
from typing import Any, Dict, Optional

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    macd = (dif - dea) * 2
    return dif, dea, macd


def ma20_rising(close: pd.Series, window: int = 20) -> bool:
    """MA20 是否在上升（当前 MA20 > 前一根 MA20）。"""
    if len(close) < window + 1:
        return False
    ma = close.ewm(span=window, adjust=False).mean()
    return float(ma.iloc[-1]) > float(ma.iloc[-2])


def price_above_ma20(close: pd.Series, window: int = 20) -> bool:
    """当前价是否在 MA20 上方。"""
    if len(close) < window:
        return False
    ma = close.ewm(span=window, adjust=False).mean()
    return float(close.iloc[-1]) >= float(ma.iloc[-1])


def macd_not_dead_cross(dif: pd.Series, dea: pd.Series) -> bool:
    """MACD 不死叉：当前 DIF >= DEA（或至少未明显死叉）。"""
    if len(dif) < 2 or len(dea) < 2:
        return True
    return float(dif.iloc[-1]) >= float(dea.iloc[-1])


def trend_score_and_pass(
    bars: pd.DataFrame,
    close_col: str = "close",
    ma_window: int = 20,
) -> Dict[str, Any]:
    """
    计算趋势得分与是否通过过滤。
    :param bars: 至少含 close（或 close_col），index 为日期
    :return: {"passed": bool, "trend_score": 0-100, "price_above_ma20", "ma20_rising", "macd_ok"}
    """
    if bars is None or len(bars) < 30:
        return {"passed": False, "trend_score": 0, "price_above_ma20": False, "ma20_rising": False, "macd_ok": False}
    close = bars[close_col] if close_col in bars.columns else bars["收盘"]
    close = close.astype(float)
    price_ok = price_above_ma20(close, ma_window)
    ma_ok = ma20_rising(close, ma_window)
    dif, dea, _ = _macd(close)
    macd_ok = macd_not_dead_cross(dif, dea)
    score = 0
    if price_ok:
        score += 40
    if ma_ok:
        score += 30
    if macd_ok:
        score += 30
    passed = price_ok and ma_ok and macd_ok
    return {
        "passed": passed,
        "trend_score": min(100, score),
        "price_above_ma20": price_ok,
        "ma20_rising": ma_ok,
        "macd_ok": macd_ok,
    }
