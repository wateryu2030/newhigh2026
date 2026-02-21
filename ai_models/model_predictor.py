# -*- coding: utf-8 -*-
"""
预测模块：加载训练好的模型，对当前市场股票打分，输出 symbol | score，score 0–1。
"""
from __future__ import annotations
import os
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(_ROOT, "models", "xgb_model.pkl")


class ModelPredictor:
    """加载 XGBoost 模型并对特征矩阵/多标的 K 线打分。"""

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH) -> None:
        self.model_path = model_path
        self._model = None
        self._feature_cols: Optional[List[str]] = None
        self._use_binary = True
        self._backend: str = "xgboost"

    def load_model(self, path: Optional[str] = None) -> "ModelPredictor":
        path = path or self.model_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"model not found: {path}")
        import pickle
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._model = data["model"]
        self._feature_cols = data.get("feature_cols")
        self._use_binary = data.get("use_binary", True)
        self._backend = data.get("backend", "xgboost")
        self.model_path = path
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """返回概率/分数，形状 (n_samples,) 范围 0–1。"""
        if self._model is None:
            raise RuntimeError("call load_model first")
        if self._backend == "xgboost":
            import xgboost as xgb
            d = xgb.DMatrix(X, feature_names=self._feature_cols)
            pred = self._model.predict(d)
        else:
            pred = self._model.predict_proba(X)[:, 1]
        return np.clip(np.asarray(pred).ravel(), 0.0, 1.0)

    def get_feature_cols(self) -> Optional[List[str]]:
        return self._feature_cols

    def score_symbols_from_features(
        self,
        feature_df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        从已构建的因子表对每行打分，按 symbol 聚合（取最新或均值）。
        :return: DataFrame 列 symbol, score
        """
        cols = feature_cols or self._feature_cols
        if not cols:
            from .dataset_builder import get_feature_columns
            cols = get_feature_columns()
        available = [c for c in cols if c in feature_df.columns]
        if not available:
            return pd.DataFrame(columns=["symbol", "score"])

        X = feature_df[available].replace([np.inf, -np.inf], np.nan).fillna(0).values.astype(np.float64)
        scores = self.predict_proba(X)
        out = feature_df[["symbol"]].copy() if "symbol" in feature_df.columns else pd.DataFrame()
        if out.empty:
            out = pd.DataFrame({"symbol": feature_df.index.astype(str) if feature_df.index.name else range(len(feature_df))})
        out["score"] = scores
        # 若同一 symbol 多行（多日），取最后一日或均值
        if "symbol" in out.columns and out["symbol"].nunique() < len(out):
            out = out.groupby("symbol", as_index=False)["score"].mean()
        return out[["symbol", "score"]]
