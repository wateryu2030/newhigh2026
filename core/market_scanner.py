# -*- coding: utf-8 -*-
"""
机构级市场扫描器：统一入口，委托 scanner 全市场扫描，支持多策略与龙头池输出。
目标：扫描时间 < 10 分钟，支持 100 万以上资金管理。
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def run_scan(
    strategy_id: str = "breakout",
    timeframe: str = "D",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    运行市场扫描，返回最新 K 线有信号的标的列表。
    :param strategy_id: ma_cross, rsi, macd, breakout, swing_newhigh 或 ev_* 自进化
    :param timeframe: D / W / M
    :param limit: 全市场扫描时限制股票数量，None 表示不限制（可能较慢）
    :return: [{"symbol", "name", "signal", "price", "date", "reason", "trend"}, ...]
    """
    try:
        from scanner.scanner import scan_market, scan_market_evolution
    except ImportError:
        logger.warning("scanner.scanner not found, returning []")
        return []

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

    if (strategy_id or "").startswith("ev_"):
        return scan_market_evolution(
            ev_id=strategy_id,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            limit=limit,
        )
    return scan_market(
        strategy_id=strategy_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        stock_list=stock_list,
        limit=limit,
    )


def run_portfolio_scan(
    strategies: List[Dict[str, Any]],
    timeframe: str = "D",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    多策略组合扫描，仅保留组合信号为 BUY/SELL 的标的。
    :param strategies: [{"strategy_id": "ma_cross", "weight": 0.5}, ...]
    """
    try:
        from scanner.scanner import scan_market_portfolio
    except ImportError:
        logger.warning("scanner.scanner.scan_market_portfolio not found")
        return []

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
    return scan_market_portfolio(
        strategies=strategies,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        stock_list=stock_list,
        limit=limit,
    )
