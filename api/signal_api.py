# -*- coding: utf-8 -*-
"""
信号 API：龙头池、综合评分、买卖列表结构，供前端与 OpenClaw 每日报告使用。
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_dragon_pool(
    strategy_id: str = "breakout",
    top_n: int = 30,
    emotion_cycle: Optional[str] = None,
    policy_score: float = 50.0,
) -> List[Dict[str, Any]]:
    """
    获取龙头池：扫描 + 资金强度 + 综合评分，返回带 composite_score 的列表。
    """
    try:
        from core.market_scanner import run_scan
        from core.fund_engine import rank_by_fund
        from core.scoring_engine import score_candidates, build_dragon_pool
        from core.sentiment_engine import get_emotion_state
    except ImportError as e:
        logger.warning("signal_api get_dragon_pool import: %s", e)
        return []

    scan_results = run_scan(strategy_id=strategy_id, limit=500)
    if not scan_results:
        return []
    symbols = [r.get("symbol") or (r.get("order_book_id") or "").split(".")[0] for r in scan_results]
    fund_rank = rank_by_fund(symbols, days=5)
    state = get_emotion_state() if emotion_cycle is None else {"emotion_cycle": emotion_cycle}
    sentiment_score = 50.0
    if state.get("emotion_cycle") == "加速期":
        sentiment_score = 70.0
    elif state.get("emotion_cycle") in ("冰点", "退潮"):
        sentiment_score = 35.0
    fund_map = {r["symbol"]: r["score"] for r in fund_rank}
    scored = score_candidates(
        scan_results,
        fund_scores=fund_map,
        sentiment_score=sentiment_score,
        policy_score=policy_score,
    )
    return scored[:top_n]


def get_signal_structure(
    buy_list: List[str],
    sell_list: List[str],
    dragon_pool: List[str],
    emotion_cycle: str,
    risk_level: str,
) -> Dict[str, Any]:
    """
    返回与 daily_report.json 一致的信号结构，供 API 响应。
    """
    return {
        "emotion_cycle": emotion_cycle,
        "dragon_pool": dragon_pool,
        "buy_list": list(buy_list),
        "sell_list": list(sell_list),
        "risk_level": risk_level,
        "updated_at": datetime.now().isoformat(),
    }
