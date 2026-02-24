# -*- coding: utf-8 -*-
"""
AI/ML 策略：调用 Alpha 模型预测收益，正预测 buy、负预测 sell。
"""
from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd

from .base_strategy import BaseStrategy


class AIMLStrategy(BaseStrategy):
    name = "AI预测"
    strategy_id = "ai_ml"

    def generate_signals(self, data: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(data, dict) or len(data) == 0:
            return out
        try:
            from backend.ai.feature_engineer import build_features
            from backend.ai.alpha_model import predict, load_model
        except Exception:
            return out
        model = load_model()
        if model is None:
            return out
        for symbol, df in data.items():
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 60:
                continue
            try:
                feats = build_features(df)
                if feats is None or len(feats) < 1:
                    continue
                last = feats.drop(columns=["forward_return_5d"], errors="ignore").tail(1)
                if len(last) == 0:
                    continue
                pred = predict(last, model)
                if pred is None or len(pred) == 0:
                    continue
                ret = float(pred.ravel()[0])
                if ret > 0.02:
                    out.append({"symbol": symbol, "signal": "buy", "confidence": min(0.95, 0.5 + ret)})
                elif ret < -0.02:
                    out.append({"symbol": symbol, "signal": "sell", "confidence": min(0.8, 0.5 - ret)})
                else:
                    out.append({"symbol": symbol, "signal": "hold", "confidence": 0.5})
            except Exception:
                continue
        return out
