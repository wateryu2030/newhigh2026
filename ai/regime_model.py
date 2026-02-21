# -*- coding: utf-8 -*-
"""
市场状态识别：BULL / BEAR / NEUTRAL。
优先使用 strategies_pro.MarketRegimeDetector（均线规则）；可选 RandomForest 增强。
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd


class RegimeModel:
    """
    识别市场状态，供组合权重与风控使用。
    - rule_based: 使用 strategies_pro 均线规则（指数 vs MA20/MA60）
    - model_based: 可选，用近期收益/波动等特征训练 RandomForest 分类
    """

    def __init__(self, use_sklearn: bool = False):
        self.use_sklearn = use_sklearn
        self._clf = None

    def detect(self, index_df: pd.DataFrame) -> str:
        """
        :param index_df: 指数 K 线，含 close
        :return: "BULL" | "BEAR" | "NEUTRAL"
        """
        try:
            from strategies_pro.market_regime import MarketRegimeDetector
            det = MarketRegimeDetector()
            r = det.detect(index_df)
            return r.value
        except Exception:
            return "NEUTRAL"

    def detect_with_model(self, index_df: pd.DataFrame) -> str:
        """
        若已训练 sklearn 模型，用特征预测；否则退回 rule_based。
        """
        if self._clf is not None and index_df is not None and len(index_df) >= 30:
            try:
                X = self._extract_features(index_df)
                if X is not None:
                    pred = self._clf.predict(X.reshape(1, -1))[0]
                    return ["BULL", "BEAR", "NEUTRAL"][int(pred)]
            except Exception:
                pass
        return self.detect(index_df)

    def _extract_features(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        """近期收益、波动等。"""
        if "close" not in df.columns or len(df) < 20:
            return None
        close = df["close"].astype(float)
        ret_5 = (close.iloc[-1] / close.iloc[-6] - 1) if len(close) >= 6 else 0
        ret_20 = (close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else 0
        vol = close.pct_change().tail(20).std()
        vol = vol if pd.notna(vol) else 0
        return np.array([ret_5, ret_20, vol])

    def fit(self, index_series: pd.DataFrame, labels: Optional[np.ndarray] = None) -> "RegimeModel":
        """
        用历史指数与标签训练 RandomForest（可选）。
        labels: 0=BULL, 1=BEAR, 2=NEUTRAL；若 None 则用均线规则生成。
        """
        if index_series is None or len(index_series) < 60:
            return self
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            return self
        if labels is None:
            from strategies_pro.market_regime import MarketRegimeDetector
            det = MarketRegimeDetector()
            lab = []
            for i in range(60, len(index_series)):
                r = det.detect(index_series.iloc[: i + 1])
                lab.append(0 if r.value == "BULL" else (1 if r.value == "BEAR" else 2))
            labels = np.array(lab)
        X_list = []
        for i in range(60, len(index_series)):
            f = self._extract_features(index_series.iloc[: i + 1])
            if f is not None:
                X_list.append(f)
        if not X_list or len(X_list) != len(labels):
            return self
        X = np.vstack(X_list)
        self._clf = RandomForestClassifier(n_estimators=50, random_state=42)
        self._clf.fit(X, labels[: len(X)])
        self.use_sklearn = True
        return self
