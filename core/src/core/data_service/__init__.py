# Data Service Layer: DuckDB -> API 的稳定数据通道，不暴露 SQL 给 Gateway。
from .db import get_conn
from .market_service import get_stock_list, get_market_summary
from .strategy_service import get_strategies_summary
from .portfolio_service import get_portfolio_summary

__all__ = [
    "get_conn",
    "get_stock_list",
    "get_market_summary",
    "get_strategies_summary",
    "get_portfolio_summary",
]
