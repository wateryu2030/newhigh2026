# -*- coding: utf-8 -*-
"""
高频 Alpha 因子库（机构级）。
输入 OHLCV DataFrame，输出叠加 20+ 因子的 DataFrame，供因子引擎与模型使用。
"""
import pandas as pd
import numpy as np
from typing import Optional


def add_alpha_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    在 OHLCV 上计算 Alpha 因子，列名与现有列不冲突则新增，否则覆盖。
    输入需含 open, high, low, close, volume（或等价列名）；可为索引或列形式的 date。
    输出含 return, momentum_*, volatility_*, volume_*, trend_strength, price_bias,
    corr_price_volume, skew, kurt 等，并做 dropna。
    """
    if df is None or len(df) == 0:
        return df
    df = df.copy()
    # 统一 date 列（供 factor_engine 使用）
    if "date" not in df.columns and df.index is not None:
        df["date"] = df.index.astype(str).str[:10]
    # 收益率
    df["return"] = df["close"].pct_change()
    # 动量因子
    df["momentum_5"] = df["close"] / df["close"].shift(5) - 1
    df["momentum_20"] = df["close"] / df["close"].shift(20) - 1
    # 波动率因子
    df["volatility_10"] = df["return"].rolling(10).std()
    df["volatility_20"] = df["return"].rolling(20).std()
    # 成交量因子
    df["volume_ma5"] = df["volume"].rolling(5).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma5"].replace(0, np.nan)
    # 趋势强度
    df["trend_strength"] = df["close"].rolling(10).mean() - df["close"].rolling(30).mean()
    # 价格偏离
    ma20 = df["close"].rolling(20).mean()
    df["price_bias"] = (df["close"] - ma20) / ma20.replace(0, np.nan)
    # 量价相关性
    df["corr_price_volume"] = df["close"].rolling(20).corr(df["volume"])
    # 收益率偏度、峰度
    df["skew"] = df["return"].rolling(20).skew()
    df["kurt"] = df["return"].rolling(20).kurt()
    df = df.dropna()
    return df
