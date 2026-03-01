# -*- coding: utf-8 -*-
"""
AI 基金经理：市场状态判断、策略组合权重、仓位与风控。
机构级核心：AI = 组合经理。
"""
from __future__ import annotations
from typing import Any, Dict

try:
    from backend.ai.market_regime import detect_regime, RegimeType
except Exception:
    RegimeType = str
    def detect_regime(df):  # type: ignore
        return "sideways"


class AIFundManager:
    """
    AI 基金经理职责：
    1 市场状态判断
    2 选择策略组合权重
    3 调整仓位（现金比例）
    4 控制风险（委托 risk 模块）
    5 可解释决策
    """

    def __init__(self):
        self._last_regime: str = "sideways"
        self._last_weights: Dict[str, float] = {}

    def detect_market_regime(self, market: Dict[str, Any]) -> str:
        """
        判断市场状态。market 可含：
        - index_ma20, index_ma60：指数均线
        - 或 df：DataFrame(close, volume)，用 detect_regime(df)
        """
        if market.get("index_ma20") is not None and market.get("index_ma60") is not None:
            if market["index_ma20"] > market["index_ma60"]:
                self._last_regime = "bull"
                return "bull"
            self._last_regime = "bear"
            return "bear"
        if "df" in market:
            import pandas as pd
            df = market["df"]
            if isinstance(df, pd.DataFrame) and len(df) >= 20:
                self._last_regime = detect_regime(df)
                return self._last_regime
        return self._last_regime

    def decide(self, market: Dict[str, Any]) -> Dict[str, float]:
        """
        根据市场状态返回策略组合权重。
        返回例：{"dragon": 0.5, "trend": 0.3, "mean": 0.1, "cash": 0.1}
        """
        regime = self.detect_market_regime(market)
        return self.decide_weights(regime)

    def decide_weights(self, regime: str) -> Dict[str, float]:
        """
        生产级：按牛熊分配龙头/趋势/均值/现金。
        龙头 40%、趋势 30%、均值 20%、现金 10% 可调。
        """
        if regime == "bull":
            w = {"dragon": 0.5, "trend": 0.3, "mean": 0.1, "cash": 0.1}
        elif regime == "bear":
            w = {"dragon": 0.2, "trend": 0.2, "mean": 0.2, "cash": 0.4}
        else:
            w = {"dragon": 0.4, "trend": 0.3, "mean": 0.2, "cash": 0.1}
        self._last_weights = w
        return w

    def get_last_weights(self) -> Dict[str, float]:
        return dict(self._last_weights)

    def get_last_regime(self) -> str:
        return self._last_regime

    def get_position_scale(self, state: Dict[str, Any] | None = None) -> float:
        """
        私募级：择时 + RL 仓位模型 对总仓位的缩放 [0, 1]。
        state: { equity_curve?, volatility?, df?, close? } 供择时/RL；可选。
        未配置时返回 1.0。
        """
        scale = 1.0
        try:
            from backend.ai.timing_model import get_timing_model
            import numpy as np
            tm = get_timing_model("rule")
            st = state or {}
            close = None
            if "df" in st and st["df"] is not None:
                df = st["df"]
                if hasattr(df, "columns") and "close" in df.columns:
                    close = np.asarray(df["close"].values, dtype=float)
                elif hasattr(df, "iloc"):
                    close = np.asarray(df.iloc[:, -1].values, dtype=float)
            elif "close" in st:
                close = np.asarray(st["close"], dtype=float)
            if close is not None and len(close) >= 20:
                scale = tm.predict_position_pct(close.reshape(-1, 1))
        except Exception:
            pass
        try:
            from backend.ai.rl_position_model import get_rl_position_model
            rl = get_rl_position_model(use_rl=False)
            scale_rl = rl.predict(state or {})
            scale = min(scale, scale_rl)
        except Exception:
            pass
        return max(0.0, min(1.0, float(scale)))
