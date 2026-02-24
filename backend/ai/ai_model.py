# -*- coding: utf-8 -*-
"""
AI 买卖点预测模型：LightGBM 二分类，目标为未来 5 日收益是否 > 3%。
"""
from __future__ import annotations
import os
import pickle
from typing import List, Optional

import pandas as pd
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(_ROOT, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "lgb_model.pkl")

# 训练/预测使用的特征列（与 feature_engineering 输出一致）
FEATURE_COLS = [
    "MA5", "MA10", "MA20", "MA60",
    "MACD", "MACD_signal", "MACD_hist",
    "RSI", "ATR",
    "return_1d", "volatility_20", "volume_pct_change_5",
]


def _get_target(feature_df: pd.DataFrame) -> pd.Series:
    """未来 5 日收益 > 3% 为 1，否则为 0。"""
    if "forward_return_5d" not in feature_df.columns:
        return pd.Series(dtype=int)
    return (feature_df["forward_return_5d"] > 0.03).astype(int)


def train_model(
    feature_df: pd.DataFrame,
    target: Optional[pd.Series] = None,
    **lgb_params,
) -> object:
    """
    训练 LightGBM 二分类模型。
    feature_df: 必须包含 FEATURE_COLS 及 forward_return_5d（用于生成 target）。
    target: 若提供则直接使用，否则 target = (forward_return_5d > 0.03).
    返回训练好的模型对象。
    """
    try:
        import lightgbm as lgb
    except ImportError:
        raise ImportError("请安装 lightgbm: pip install lightgbm")

    available = [c for c in FEATURE_COLS if c in feature_df.columns]
    if len(available) < 5:
        raise ValueError("特征不足，需要至少 MA/MACD/RSI/ATR 等列")

    if target is None:
        target = _get_target(feature_df)
    # 按位置对齐（concat 多只股票后索引可能重复，导致 fit 报错）
    n = len(feature_df)
    X = feature_df[available].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = target.reindex(feature_df.index).fillna(0).astype(int)
    X = X.iloc[:n].reset_index(drop=True)
    y = np.ravel(y.iloc[:n].values)
    if len(y) != len(X):
        y = np.ravel(y)[: len(X)]
    assert len(y) == len(X), "X 与 y 长度不一致"

    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
        **lgb_params,
    )
    X_arr = np.asarray(X, dtype=np.float64)
    model.fit(X_arr, y, feature_name=available)
    return model


def save_model(model: object, path: Optional[str] = None) -> str:
    """序列化模型到 models/lgb_model.pkl。"""
    path = path or MODEL_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    return path


def load_model(path: Optional[str] = None) -> Optional[object]:
    """从 models/lgb_model.pkl 加载模型，不存在则返回 None。"""
    path = path or MODEL_PATH
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)
