"""Skills API endpoints."""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py ---

from .endpoints import (  # noqa: E402
    _ashare_skill,
    _record_skill_call,
)


# --- Skills Routes ---


@router.get("/skill/ashare/stock-basic")
def skill_ashare_stock_basic(ts_code: Optional[str] = None, name: Optional[str] = None) -> Any:
    """A股股票基本信息（代码、名称、行业、上市日期）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_stock_basic(ts_code=ts_code, name=name)


@router.get("/skill/ashare/daily")
def skill_ashare_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """A股日线行情（开高低收、成交量、涨跌幅）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_daily_price(
        ts_code=ts_code, start_date=start_date, end_date=end_date
    )


@router.get("/skill/ashare/tech-indicator")
def skill_ashare_tech_indicator(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """A股技术指标（MA5、MA10、MACD）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_tech_indicator(
        ts_code=ts_code, start_date=start_date, end_date=end_date
    )


@router.get("/skill/ashare/finance-indicator")
def skill_ashare_finance_indicator(ts_code: str, year: Optional[int] = None) -> Any:
    """A股财务指标（PE、PB、ROE、毛利率）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_finance_indicator(ts_code=ts_code, year=year)


@router.get("/skill/ashare/limit-up-down")
def skill_ashare_limit_up_down(trade_date: Optional[str] = None) -> Any:
    """A股涨停/跌停股票列表。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_limit_up_down(trade_date=trade_date)


@router.get("/skill/ashare/industry-ranking")
def skill_ashare_industry_ranking(trade_date: Optional[str] = None, top_n: int = 10) -> Any:
    """A股行业涨幅排行。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_industry_ranking(trade_date=trade_date, top_n=top_n)


@router.get("/skill/ashare/market-overview")
def skill_ashare_market_overview(trade_date: Optional[str] = None) -> Any:
    """A股市场概览数据。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_market_overview(trade_date=trade_date)


@router.get("/skill/stats")
def get_skill_stats() -> dict:
    """Skill 调用统计：总次数、最近调用时间，供系统监控页展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"call_count": 0, "last_call_time": None}
        conn = get_conn(read_only=False)
        row = conn.execute("SELECT call_count, last_call_time FROM skill_stats LIMIT 1").fetchone()
        conn.close()
        if not row:
            return {"call_count": 0, "last_call_time": None}
        last_ts = row[1]
        if hasattr(last_ts, "isoformat"):
            last_call_time = last_ts.isoformat()
        else:
            last_call_time = str(last_ts) if last_ts else None
        return {"call_count": int(row[0] or 0), "last_call_time": last_call_time}
    except Exception:
        return {"call_count": 0, "last_call_time": None}
