# -*- coding: utf-8 -*-
"""
实盘/模拟：加载 RL 模型，根据当前状态生成交易信号与 AI 解释。
"""
from __future__ import annotations
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

MODEL_SAVE_PATH = os.path.join(_ROOT, "models", "rl_trader.zip")


class RLLiveTrader:
    """加载模型，对当前 K 线状态生成信号：decision, confidence, reason, suggested_position_pct。"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or MODEL_SAVE_PATH
        self._wrapper = None
        if os.path.exists(self.model_path):
            try:
                from rl_trading.models.rl_model import RLModelWrapper
                self._wrapper = RLModelWrapper(model_path=self.model_path)
            except Exception as e:
                logger.warning("RL 模型加载失败: %s", e)

    def get_signal(
        self,
        symbol: str,
        lookback_days: int = 60,
        current_position_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        根据最近 lookback_days 的 K 线计算状态，返回 AI 决策。
        :return: {"decision": "BUY"|"SELL"|"HOLD", "confidence": 0.82, "reason": [...], "suggested_position_pct": 0.6, "state_summary": "趋势上涨"}
        """
        if self._wrapper is None:
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reason": ["模型未加载或不存在"],
                "suggested_position_pct": 0.0,
                "state_summary": "未就绪",
            }
        try:
            from data.data_loader import load_kline
            from datetime import datetime, timedelta
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            df = load_kline(symbol, start, end, source="database")
            if df is None or len(df) < 30:
                return {
                    "decision": "HOLD",
                    "confidence": 0.0,
                    "reason": ["K 线数据不足"],
                    "suggested_position_pct": 0.0,
                    "state_summary": "数据不足",
                }
            df = df.rename(columns={c: c.lower() for c in df.columns if isinstance(c, str)})
            if "close" not in df.columns:
                df["close"] = df.get("收盘", df.iloc[:, -1])
            from rl_trading.env.trading_env import TradingEnv, _compute_indicators
            df = _compute_indicators(df, window=20)
            df = df.dropna(subset=["close", "price_ratio", "rsi"]).reset_index(drop=True)
            if len(df) < 25:
                return {"decision": "HOLD", "confidence": 0.0, "reason": ["数据不足"], "suggested_position_pct": 0.0, "state_summary": "数据不足"}
            env = TradingEnv(df, window=20)
            env._step = len(df) - 1
            env._cash = 1e6 * (1 - current_position_pct)
            env._pos = (1e6 * current_position_pct) / float(df.iloc[-1]["close"]) if float(df.iloc[-1]["close"]) > 0 else 0
            obs = env._get_obs()
            action, confidence, reasons = self._wrapper.predict_with_confidence(obs)
            decision = "BUY" if action == 1 else "SELL" if action == 2 else "HOLD"
            suggested_pct = 0.6 if action == 1 else 0.0 if action == 2 else current_position_pct
            row = df.iloc[-1]
            price_ratio, rsi = float(row.get("price_ratio", 0)), float(row.get("rsi", 0))
            if price_ratio > 0.05 and rsi > 0.05:
                state_summary = "趋势上涨"
            elif price_ratio < -0.05 and rsi < -0.05:
                state_summary = "趋势下跌"
            else:
                state_summary = "震荡"
            return {
                "decision": decision,
                "confidence": round(confidence, 2),
                "reason": reasons,
                "suggested_position_pct": round(suggested_pct * 100, 1),
                "state_summary": state_summary,
            }
        except Exception as e:
            logger.exception("get_signal: %s", e)
            return {
                "decision": "HOLD",
                "confidence": 0.0,
                "reason": [str(e)],
                "suggested_position_pct": 0.0,
                "state_summary": "异常",
            }
