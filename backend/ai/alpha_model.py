# -*- coding: utf-8 -*-
"""
AI 选股模型：LightGBM 回归，预测未来 5 日收益率。
生产级，可训练与预测。
"""
from __future__ import annotations
import os
import pickle
from typing import List, Optional

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(_ROOT, "models")
ALPHA_MODEL_PATH = os.path.join(MODEL_DIR, "lgb_alpha.pkl")

FEATURE_COLS = [
    "MA5", "MA10", "MA20", "MACD", "MACD_signal", "MACD_hist",
    "RSI", "ATR", "Momentum", "Volume_Ratio", "return_1d", "volatility_20",
]


def train_model(df: pd.DataFrame, target_col: str = "forward_return_5d", **kwargs) -> object:
    """
    训练 LightGBM 回归模型，目标为未来 5 日收益率。
    df: 必须包含 FEATURE_COLS 及 target_col。
    """
    try:
        import lightgbm as lgb
    except ImportError:
        raise ImportError("请安装 lightgbm: pip install lightgbm")
    available = [c for c in FEATURE_COLS if c in df.columns]
    if len(available) < 5:
        raise ValueError("特征不足")
    if target_col not in df.columns:
        raise ValueError(f"缺少目标列 {target_col}")
    df = df.dropna(subset=[target_col])
    X = df[available].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = np.ravel(df[target_col].values)
    X = X.reset_index(drop=True)
    y = y[: len(X)]
    if len(y) != len(X):
        y = np.ravel(y)[: len(X)]
    X_arr = np.asarray(X, dtype=np.float64)
    model = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
        **kwargs,
    )
    model.fit(X_arr, y, feature_name=available)
    return model


def predict(df: pd.DataFrame, model: Optional[object] = None) -> np.ndarray:
    """
    对特征表做收益预测。若未传 model 则从默认路径加载。
    """
    if model is None:
        model = load_model()
    if model is None:
        return np.zeros(len(df))
    available = [c for c in FEATURE_COLS if c in df.columns]
    if not available:
        return np.zeros(len(df))
    X = df[available].replace([np.inf, -np.inf], np.nan).fillna(0)
    return np.ravel(model.predict(X))


def save_model(model: object, path: Optional[str] = None) -> str:
    path = path or ALPHA_MODEL_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    return path


def load_model(path: Optional[str] = None) -> Optional[object]:
    path = path or ALPHA_MODEL_PATH
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)
