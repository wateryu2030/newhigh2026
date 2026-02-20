# -*- coding: utf-8 -*-
"""
机构级风险预测 AI：用 XGBoost 预测「高回撤/爆仓/亏损」概率，供仓位与风控使用。
"""
import numpy as np
from typing import Optional, Union

try:
    import xgboost as xgb
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False


class RiskModel:
    """
    二分类风险模型：输入特征 X，输出「发生风险」的概率 prob[:,1]。
    可用于：最大回撤超阈值、爆仓、单日亏损超阈值等标签。
    """

    def __init__(self, use_xgb: bool = True):
        if use_xgb and _HAS_XGB:
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42,
            )
        else:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)

    def train(
        self,
        X: Union[np.ndarray, "pd.DataFrame"],
        y: Union[np.ndarray, "pd.Series"],
        **kwargs,
    ) -> "RiskModel":
        X = np.asarray(X)
        y = np.asarray(y).ravel()
        self.model.fit(X, y, **kwargs)
        return self

    def predict(self, X: Union[np.ndarray, "pd.DataFrame"]) -> np.ndarray:
        """返回「风险发生」的概率 P(y=1)。"""
        X = np.asarray(X)
        prob = self.model.predict_proba(X)
        if prob.shape[1] < 2:
            return np.zeros(len(X))
        return prob[:, 1]

    def predict_binary(self, X: Union[np.ndarray, "pd.DataFrame"]) -> np.ndarray:
        return self.model.predict(X)
