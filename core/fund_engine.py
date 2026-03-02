# -*- coding: utf-8 -*-
"""
资金引擎：主力资金流向、板块资金强度，为龙头池与仓位提供资金面依据。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_stock_fund_score(symbol: str, days: int = 5) -> Dict[str, Any]:
    """
    个股资金强度：主力净流入等，返回 score 0~100。
    """
    try:
        from market.money_flow import get_stock_money_flow
        return get_stock_money_flow(symbol=symbol, days=days)
    except Exception as e:
        logger.debug("fund_engine get_stock_fund_score %s: %s", symbol, e)
        return {"net_main": 0, "score": 50}


def get_sector_fund_rank(indicator: str = "今日", top_n: int = 20) -> List[Dict[str, Any]]:
    """
    板块资金流向排名，用于资金强度排行与热点判断。
    """
    try:
        from market.money_flow import get_sector_fund_flow_rank
        return get_sector_fund_flow_rank(indicator=indicator, top_n=top_n)
    except Exception as e:
        logger.debug("fund_engine get_sector_fund_rank: %s", e)
        return []


def get_sector_strength(top_n: int = 30) -> List[Dict[str, Any]]:
    """
    板块强度（涨幅、涨跌家数），用于龙头池所在板块过滤。
    """
    try:
        from market.sector_strength import get_sector_strength as _get
        return _get(top_n=top_n)
    except Exception as e:
        logger.debug("fund_engine get_sector_strength: %s", e)
        return []


def rank_by_fund(symbols: List[str], days: int = 5) -> List[Dict[str, Any]]:
    """
    对股票列表按资金强度排序，返回 [{"symbol", "net_main", "score"}, ...] 降序。
    """
    out: List[Dict[str, Any]] = []
    for sym in symbols:
        code = sym.split(".")[0] if "." in sym else sym
        r = get_stock_fund_score(code, days=days)
        out.append({
            "symbol": code,
            "net_main": r.get("net_main", 0),
            "score": r.get("score", 50),
        })
    out.sort(key=lambda x: (x.get("score", 0), x.get("net_main", 0)), reverse=True)
    return out
