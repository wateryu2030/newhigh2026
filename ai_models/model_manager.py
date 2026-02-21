# -*- coding: utf-8 -*-
"""
模型管理器：训练、预测、定期更新。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .dataset_builder import build_dataset_from_market_data, get_feature_columns
from .feature_engineering import build_features_for_symbol, build_features_multi
from .model_trainer import ModelTrainer, DEFAULT_MODEL_PATH as TRAINER_MODEL_PATH
from .model_predictor import ModelPredictor, DEFAULT_MODEL_PATH as PREDICTOR_MODEL_PATH


class ModelManager:
    """AI 选股模型训练、预测与更新。"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        feature_cols: Optional[List[str]] = None,
    ) -> None:
        self.model_path = model_path
        self.feature_cols = feature_cols or get_feature_columns()
        self._trainer: Optional[ModelTrainer] = None
        self._predictor: Optional[ModelPredictor] = None

    def train_models(
        self,
        market_data: Dict[str, pd.DataFrame],
        label_forward_days: int = 5,
        use_binary: bool = True,
        binary_threshold: float = 0.0,
        eval_frac: float = 0.2,
    ) -> Dict[str, Any]:
        """
        从多标的 K 线训练模型并保存。
        :return: 含 metrics, model_path 等
        """
        feature_df, X, y = build_dataset_from_market_data(
            market_data,
            label_forward_days=label_forward_days,
            feature_cols=self.feature_cols,
            use_binary_label=use_binary,
            binary_label_threshold=binary_threshold,
        )
        if X.size == 0 or y.size == 0:
            return {"ok": False, "reason": "insufficient data", "metrics": {}}

        n = len(y)
        idx = np.random.permutation(n) if n > 20 else np.arange(n)
        split = int(n * (1 - eval_frac))
        X_train, X_eval = X[idx[:split]], X[idx[split:]]
        y_train, y_eval = y[idx[:split]], y[idx[split:]]
        eval_set = (X_eval, y_eval) if len(y_eval) > 5 else None

        trainer = ModelTrainer(
            model_path=self.model_path or TRAINER_MODEL_PATH,
            feature_cols=self.feature_cols,
            use_binary=use_binary,
            binary_threshold=binary_threshold,
        )
        trainer.train(X_train, y_train, eval_set=eval_set)
        eval_df = feature_df.iloc[idx[split:]].reset_index(drop=True) if split < n else None
        metrics = trainer.evaluate(X_eval, y_eval, feature_df=eval_df)
        path = trainer.save_model()
        self._trainer = trainer
        self._predictor = None  # 下次 predict 时重新 load
        return {"ok": True, "metrics": metrics, "model_path": path, "n_samples": n}

    def predict(
        self,
        market_data: Dict[str, pd.DataFrame],
        model_path: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        对当前市场数据生成因子并打分。
        :return: DataFrame 列 symbol, score (0–1)
        """
        feature_df = build_features_multi(market_data, label_forward_days=1)
        if feature_df.empty:
            return pd.DataFrame(columns=["symbol", "score"])
        # 每个 symbol 取最近一行（最新日）
        if "date" in feature_df.columns:
            last_dates = feature_df.groupby("symbol")["date"].transform("max")
            feature_df = feature_df[feature_df["date"] == last_dates]
        pred = ModelPredictor(model_path or self.model_path or PREDICTOR_MODEL_PATH)
        try:
            pred.load_model()
        except FileNotFoundError:
            return pd.DataFrame(columns=["symbol", "score"])
        return pred.score_symbols_from_features(feature_df, feature_cols=self.feature_cols)

    def update_models(
        self,
        market_data: Dict[str, pd.DataFrame],
        **train_kw: Any,
    ) -> Dict[str, Any]:
        """定期重新训练。"""
        return self.train_models(market_data, **train_kw)
