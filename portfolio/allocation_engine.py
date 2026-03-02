# -*- coding: utf-8 -*-
"""
分配引擎：多策略权重分配（dragon 40%、trend 30%、mean_reversion 30%），
与 AI 月度优化后的权重对接。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认策略权重（与文档一致）
DEFAULT_STRATEGY_WEIGHTS = {
    "dragon_strategy": 0.40,
    "trend_strategy": 0.30,
    "mean_reversion": 0.30,
}


def get_weights(custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    返回当前策略权重。若传入 custom_weights（如 AI 优化结果），则归一化后使用。
    """
    if custom_weights:
        total = sum(custom_weights.values())
        if total > 0:
            return {k: v / total for k, v in custom_weights.items()}
    return dict(DEFAULT_STRATEGY_WEIGHTS)


def allocate_signals(
    dragon_signals: List[Dict[str, Any]],
    trend_signals: List[Dict[str, Any]],
    mean_reversion_signals: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    按权重合并多策略信号，去重后按综合得分排序。
    每项含 symbol, signal, score, source 等。
    """
    w = get_weights(weights)
    w_d = w.get("dragon_strategy", 0.4)
    w_t = w.get("trend_strategy", 0.3)
    w_m = w.get("mean_reversion", 0.3)

    by_symbol: Dict[str, Dict[str, Any]] = {}
    for item in dragon_signals:
        sym = (item.get("symbol") or item.get("order_book_id") or "").split(".")[0]
        if not sym:
            continue
        by_symbol[sym] = {
            "symbol": sym,
            "signal": item.get("signal", "BUY"),
            "score": float(item.get("composite_score", item.get("score", 50))) * w_d,
            "sources": ["dragon"],
        }
    for item in trend_signals:
        sym = (item.get("symbol") or item.get("order_book_id") or "").split(".")[0]
        if not sym:
            continue
        sc = float(item.get("confidence", 0.5) or 0.5) * 100 * w_t
        if sym in by_symbol:
            by_symbol[sym]["score"] += sc
            by_symbol[sym]["sources"].append("trend")
        else:
            by_symbol[sym] = {
                "symbol": sym,
                "signal": item.get("signal", "hold"),
                "score": sc,
                "sources": ["trend"],
            }
    for item in mean_reversion_signals:
        sym = (item.get("symbol") or item.get("order_book_id") or "").split(".")[0]
        if not sym:
            continue
        sc = float(item.get("confidence", 0.5) or 0.5) * 100 * w_m
        if sym in by_symbol:
            by_symbol[sym]["score"] += sc
            by_symbol[sym]["sources"].append("mean_reversion")
        else:
            by_symbol[sym] = {
                "symbol": sym,
                "signal": item.get("signal", "hold"),
                "score": sc,
                "sources": ["mean_reversion"],
            }

    out = list(by_symbol.values())
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out
