# -*- coding: utf-8 -*-
"""
因子引擎：调用 Alpha 因子库，输出统一特征矩阵（可含 date 列供对齐）。
"""
from typing import List, Optional
import pandas as pd

from .alpha_factors import add_alpha_factors


# 默认作为特征输出的列（不含 date，供模型使用）
DEFAULT_FEATURE_COLUMNS = [
    "open", "high", "low", "close", "volume",
    "return", "momentum_5", "momentum_20",
    "volatility_10", "volatility_20",
    "volume_ma5", "volume_ratio",
    "trend_strength", "price_bias", "corr_price_volume",
    "skew", "kurt",
]


def build_factor_matrix(
    df: pd.DataFrame,
    feature_columns: Optional[List[str]] = None,
    keep_date: bool = True,
) -> pd.DataFrame:
    """
    构建因子特征矩阵：先叠加 Alpha 因子，再选取特征列。
    :param df: OHLCV DataFrame
    :param feature_columns: 使用的特征列；None 则用 DEFAULT_FEATURE_COLUMNS（仅存在列）
    :param keep_date: 是否保留 date 列
    :return: 特征 DataFrame，索引与 df 一致
    """
    df = add_alpha_factors(df)
    if df is None or len(df) == 0:
        return df
    cols = feature_columns or DEFAULT_FEATURE_COLUMNS
    available = [c for c in cols if c in df.columns]
    out = df[available].copy()
    if keep_date and "date" in df.columns:
        out["date"] = df["date"].values
    return out
