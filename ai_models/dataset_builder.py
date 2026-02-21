# -*- coding: utf-8 -*-
"""
数据集构建：从因子表生成 X, y，支持滚动窗口与多股票合并。
"""
from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

from .feature_engineering import build_features_multi

# 默认用于训练的因子列（不含 date, symbol, label）
DEFAULT_FEATURE_COLS = [
    "ma5", "ma10", "ma20", "ma60",
    "return_1d", "volatility_20", "atr_14", "rsi_14", "macd_hist",
    "volume_change_5", "high_dist_20", "ma_alignment",
    "return_5d", "return_20d", "return_60d", "max_drawdown_20",
]


def get_feature_columns() -> List[str]:
    return list(DEFAULT_FEATURE_COLS)


def build_dataset(
    feature_df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    label_col: str = "label",
    binary_label_threshold: float = 0.0,
    use_binary_label: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    从因子 DataFrame 构建 X, y。
    :param feature_df: 含 date, symbol, 各因子, label
    :param feature_cols: 使用的特征列，默认 DEFAULT_FEATURE_COLS
    :param label_col: 标签列名
    :param binary_label_threshold: 二分类时，收益超过此阈值为 1
    :param use_binary_label: True 时 y 为 0/1，否则为连续收益
    :return: X (n_samples, n_features), y (n_samples,)
    """
    cols = feature_cols or get_feature_columns()
    available = [c for c in cols if c in feature_df.columns]
    if not available:
        raise ValueError(f"no feature columns found in df; have {list(feature_df.columns)}")

    X = feature_df[available].replace([np.inf, -np.inf], np.nan).fillna(0).values.astype(np.float64)
    y_raw = feature_df[label_col].values.astype(np.float64)

    if use_binary_label:
        y = (y_raw > binary_label_threshold).astype(np.float64)
    else:
        y = y_raw

    return X, y


def build_dataset_from_market_data(
    market_data: dict[str, pd.DataFrame],
    label_forward_days: int = 5,
    feature_cols: Optional[List[str]] = None,
    use_binary_label: bool = True,
    binary_label_threshold: float = 0.0,
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    从多标的 K 线一步生成因子表与 X, y。
    :return: feature_df, X, y
    """
    feature_df = build_features_multi(market_data, label_forward_days=label_forward_days)
    if feature_df.empty or len(feature_df) < 50:
        return feature_df, np.array([]), np.array([])
    X, y = build_dataset(
        feature_df,
        feature_cols=feature_cols,
        use_binary_label=use_binary_label,
        binary_label_threshold=binary_label_threshold,
    )
    return feature_df, X, y
