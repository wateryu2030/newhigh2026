# -*- coding: utf-8 -*-
"""
市场 API：K 线、板块强度、资金排名等，供前端与 OpenClaw 调用。
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_kline(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeframe: str = "D",
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """获取 K 线数据，返回 [{"date","open","high","low","close","volume"}, ...]。"""
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        if db is None:
            return []
        ob_id = symbol if "." in symbol else f"{symbol}.XSHG"
        if not db.get_daily_bars(ob_id, "2000-01-01", "2099-12-31"):
            ob_id = f"{symbol}.XSHE"
        df = db.get_daily_bars(ob_id, start_date or "2000-01-01", end_date or datetime.now().strftime("%Y-%m-%d"))
        if df is None or len(df) == 0:
            return []
        df = df.tail(limit)
        out = []
        for _, row in df.iterrows():
            d = row.get("date") or row.get("datetime")
            if hasattr(d, "strftime"):
                d = d.strftime("%Y-%m-%d")
            out.append({
                "date": str(d)[:10],
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": float(row.get("volume", 0)),
            })
        return out
    except Exception as e:
        logger.debug("market_api get_kline %s: %s", symbol, e)
        return []


def get_sector_strength(top_n: int = 30) -> List[Dict[str, Any]]:
    """板块强度排行。"""
    try:
        from core.fund_engine import get_sector_strength as _get
        return _get(top_n=top_n)
    except Exception:
        return []


def get_fund_rank(indicator: str = "今日", top_n: int = 20) -> List[Dict[str, Any]]:
    """板块资金流向排名。"""
    try:
        from core.fund_engine import get_sector_fund_rank
        return get_sector_fund_rank(indicator=indicator, top_n=top_n)
    except Exception:
        return []


def get_emotion_dashboard() -> Dict[str, Any]:
    """情绪仪表盘：当前情绪周期与建议仓位（生产级：涨停家数/连板高度/炸板率/成交额）。"""
    try:
        from core.sentiment_engine import get_emotion_state
        return get_emotion_state(market_data=None)
    except Exception as e:
        logger.debug("get_emotion_dashboard: %s", e)
        return {"emotion_cycle": "启动", "suggested_position_pct": 0.4, "description": "—", "emotion_score": 50}


def get_dragon_lhb_pool(emotion_cycle: Optional[str] = None, date_ymd: Optional[str] = None) -> Dict[str, Any]:
    """龙虎榜游资龙头池：游资打分+共振列表；仅在启动/加速期返回共振股。"""
    try:
        from core.lhb_engine import get_dragon_lhb_pool as _get
        return _get(date_ymd=date_ymd, emotion_cycle=emotion_cycle, only_when_emotion_ok=True)
    except Exception as e:
        logger.debug("get_dragon_lhb_pool: %s", e)
        return {"date": "", "lhb_score": 0, "resonance_list": [], "resonance_count": 0, "emotion_ok": False, "reason": str(e)}
