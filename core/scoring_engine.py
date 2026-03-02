# -*- coding: utf-8 -*-
"""
统一评分引擎：综合龙头信号、资金强度、情绪与政策，输出 0~100 综合分与龙头池排序。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认权重：龙头/趋势信号 40%，资金 30%，情绪 15%，政策 15%
DEFAULT_WEIGHTS = {"signal": 0.40, "fund": 0.30, "sentiment": 0.15, "policy": 0.15}


def score_candidates(
    candidates: List[Dict[str, Any]],
    fund_scores: Optional[Dict[str, float]] = None,
    sentiment_score: float = 50.0,
    policy_score: float = 50.0,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    对候选标的做综合评分并排序。
    :param candidates: 来自扫描器的列表，每项含 symbol, signal, price, (可选 score/trend)
    :param fund_scores: symbol -> 资金得分 0~100，缺失用 50
    :param sentiment_score: 当前市场情绪得分 0~100
    :param policy_score: 当前政策面得分 0~100
    :param weights: signal/fund/sentiment/policy 权重，默认 DEFAULT_WEIGHTS
    :return: 同结构列表，每项增加 "composite_score"，按该分降序
    """
    w = weights or DEFAULT_WEIGHTS
    fund_scores = fund_scores or {}
    out = []
    for c in candidates:
        sym = (c.get("symbol") or c.get("order_book_id") or "").split(".")[0] or ""
        signal_score = 50.0
        if c.get("signal") in ("BUY", "buy", 1):
            signal_score = 80.0
        elif c.get("signal") in ("SELL", "sell", -1):
            signal_score = 20.0
        if "score" in c and isinstance(c["score"], (int, float)):
            signal_score = float(c["score"])
        fund = float(fund_scores.get(sym, fund_scores.get(c.get("symbol"), 50)))
        composite = (
            signal_score * w.get("signal", 0.4)
            + fund * w.get("fund", 0.3)
            + sentiment_score * w.get("sentiment", 0.15)
            + policy_score * w.get("policy", 0.15)
        )
        r = dict(c)
        r["composite_score"] = round(composite, 2)
        out.append(r)
    out.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    return out


def build_dragon_pool(
    scan_results: List[Dict[str, Any]],
    fund_rank: Optional[List[Dict[str, Any]]] = None,
    sentiment_score: float = 50.0,
    policy_score: float = 50.0,
    top_n: int = 30,
) -> List[str]:
    """
    从扫描结果与资金排名构建龙头池股票代码列表（无交易所后缀）。
    """
    if fund_rank is None:
        fund_rank = []
    fund_map = {str(r.get("symbol", "")).split(".")[0]: float(r.get("score", 50)) for r in fund_rank}
    scored = score_candidates(
        scan_results,
        fund_scores=fund_map,
        sentiment_score=sentiment_score,
        policy_score=policy_score,
    )
    pool: List[str] = []
    seen = set()
    for item in scored[: top_n * 2]:
        sym = (item.get("symbol") or item.get("order_book_id") or "")
        code = sym.split(".")[0] if "." in sym else sym
        if not code or code in seen:
            continue
        seen.add(code)
        pool.append(code)
        if len(pool) >= top_n:
            break
    return pool
