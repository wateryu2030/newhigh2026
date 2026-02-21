# -*- coding: utf-8 -*-
"""
策略池：管理 MA/RSI/MACD/KDJ/Breakout 等多策略，输出统一信号格式。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
import pandas as pd


@dataclass
class StrategyWeight:
    """策略及权重。"""
    strategy_id: str
    weight: float = 0.0


class SignalStrategy(Protocol):
    """信号策略协议。"""
    name: str

    def generate_signals(self, df: pd.DataFrame, **kwargs: Any) -> List[Dict[str, Any]]:
        ...


class StrategyPool:
    """
    策略池：加载多策略，按权重聚合信号。
    支持 ma_cross, rsi, macd, kdj, breakout。
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self._strategies: Dict[str, SignalStrategy] = {}
        self._weights = weights or {
            "ma_cross": 0.25,
            "rsi": 0.20,
            "macd": 0.25,
            "kdj": 0.15,
            "breakout": 0.15,
        }
        self._load_strategies()

    def _load_strategies(self) -> None:
        """加载插件策略。"""
        try:
            from strategies import get_plugin_strategy
            for sid, w in self._weights.items():
                s = get_plugin_strategy(sid)
                if s is not None:
                    self._strategies[sid] = s
        except ImportError:
            pass

    def get_weights(self) -> Dict[str, float]:
        """归一化权重。"""
        if not self._weights:
            return {}
        total = sum(self._weights.values())
        return {k: v / total for k, v in self._weights.items()} if total > 0 else self._weights

    def run_all(self, df: pd.DataFrame, **kwargs: Any) -> Dict[str, List[Dict[str, Any]]]:
        """
        运行所有策略，返回 { strategy_id: signals }。
        """
        out: Dict[str, List[Dict[str, Any]]] = {}
        for sid, s in self._strategies.items():
            try:
                sigs = s.generate_signals(df, **kwargs)
                out[sid] = sigs if sigs else []
            except Exception:
                out[sid] = []
        return out

    def aggregate_signals(
        self,
        strategy_signals: Dict[str, List[Dict[str, Any]]],
        mode: str = "weighted",
    ) -> List[Dict[str, Any]]:
        """
        聚合多策略信号。
        mode: weighted（加权多数）、majority（多数）、any_buy（任意 BUY 即 BUY）
        """
        if not strategy_signals:
            return []
        weights = self.get_weights()
        date_scores: Dict[str, float] = {}
        for sid, sigs in strategy_signals.items():
            w = weights.get(sid, 0.0)
            for s in sigs:
                d = str(s.get("date", ""))[:10]
                t = str(s.get("type", "")).upper()
                if t == "BUY":
                    date_scores[d] = date_scores.get(d, 0) + w
                elif t == "SELL":
                    date_scores[d] = date_scores.get(d, 0) - w
        out: List[Dict[str, Any]] = []
        for d, score in date_scores.items():
            if score > 0.3:
                out.append({"date": d, "type": "BUY", "price": 0.0, "reason": "组合信号"})
            elif score < -0.3:
                out.append({"date": d, "type": "SELL", "price": 0.0, "reason": "组合信号"})
        return sorted(out, key=lambda x: x["date"])
