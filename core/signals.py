# -*- coding: utf-8 -*-
"""
标准化买卖信号生成模块。
基于 OHLC 与技术指标（如 MA5/MA20）生成 BUY/SELL 信号，供回测结果与前端展示。
"""
from typing import List, Dict, Any
import pandas as pd


def generate_signals(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    根据 K 线及均线生成买入、卖出信号。

    输入：
        df: 至少包含 date, close，以及 ma5, ma20（若无则自动计算）的 DataFrame。
            date 可为索引或列，需能转为 YYYY-MM-DD 字符串。

    输出：
        signals: 列表，每项为 {"date": str, "type": "BUY"|"SELL", "price": float, "reason": str}
        所有数值为 float，无 NaN；日期统一 YYYY-MM-DD。
    """
    if df is None or len(df) < 21:
        return []

    df = df.copy()
    if "date" not in df.columns and df.index is not None:
        df["date"] = df.index.astype(str).str[:10]
    if "ma5" not in df.columns and "close" in df.columns:
        df["ma5"] = df["close"].rolling(5, min_periods=1).mean()
    if "ma20" not in df.columns and "close" in df.columns:
        df["ma20"] = df["close"].rolling(20, min_periods=1).mean()

    df = df.dropna(subset=["ma5", "ma20", "close"])
    if len(df) < 2:
        return []

    signals: List[Dict[str, Any]] = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        date_str = str(row.get("date", df.index[i]))[:10]
        close = float(row["close"])
        if close != close:  # NaN
            continue

        # MA 金叉：买入
        if (float(row["ma5"]) > float(row["ma20"]) and
                float(prev["ma5"]) <= float(prev["ma20"])):
            signals.append({
                "date": date_str,
                "type": "BUY",
                "price": close,
                "reason": "MA5 上穿 MA20（金叉）",
            })

        # MA 死叉：卖出
        if (float(row["ma5"]) < float(row["ma20"]) and
                float(prev["ma5"]) >= float(prev["ma20"])):
            signals.append({
                "date": date_str,
                "type": "SELL",
                "price": close,
                "reason": "MA5 下穿 MA20（死叉）",
            })

    return signals
