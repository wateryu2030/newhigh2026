"""Market API endpoints."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py (keep signature compatible) ---

from .endpoints import (  # noqa: E402
    _is_ashare_symbol,
    _pipeline_code_variants,
    _row_date_to_utc_iso,
    _normalize_sym_show,
    _fetch_klines_from_a_stock_daily,
    _fetch_klines_akshare_daily,
    _fetch_klines_stooq_daily,
    _fetch_klines_binance_usdt,
    _stooq_daily_symbol_map,
    _short_ts_for_signal,
    _optional_price,
    _optional_pct,
    _market_db_query,
    _safe_lhb_date_str,
    _safe_net_buy,
    _sniper_candidates_minimal,
)


# --- Market Routes ---


@router.get("/market/klines")
def get_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """K 线：daily_bars → a_stock_daily → 可选 akshare；空数据仍 200，避免误报 503。"""
    empty_payload = {"symbol": symbol, "interval": interval, "limit": 0, "data": []}
    if _is_ashare_symbol(symbol):
        rows: List[Any] = []
        try:
            from data_engine import get_astock_duckdb_available, fetch_klines_from_astock_duckdb

            if get_astock_duckdb_available():
                try:
                    rows = fetch_klines_from_astock_duckdb(
                        symbol,
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit,
                        recent_first=True,
                    )
                except Exception:
                    _log.exception("fetch_klines_from_astock_duckdb failed: %s", symbol)
                    rows = []
        except ImportError:
            _log.warning("data_engine not importable; skip daily_bars klines for %s", symbol)

        if rows:
            data = [
                {
                    "t": r.timestamp.isoformat(),
                    "o": r.open,
                    "h": r.high,
                    "l": r.low,
                    "c": r.close,
                    "close": r.close,
                    "v": r.volume,
                }
                for r in rows
            ]
            return json_ok(
                {
                    "symbol": rows[0].symbol,
                    "interval": "1d",
                    "limit": len(data),
                    "data": data,
                },
                source="duckdb",
            )

        try:
            pipe = _fetch_klines_from_a_stock_daily(symbol, limit=limit)
        except Exception:
            _log.exception("pipeline daily klines failed: %s", symbol)
            pipe = None
        if pipe:
            return json_ok(pipe, source="duckdb_pipeline")

        try:
            ak_payload = _fetch_klines_akshare_daily(symbol, limit=limit)
        except Exception:
            _log.exception("akshare klines failed: %s", symbol)
            ak_payload = None
        if ak_payload:
            return json_ok(ak_payload, source="akshare")

        return json_ok({**empty_payload, "limit": limit}, source="none")

    sym_u = (symbol or "").strip().upper()

    if sym_u.endswith("USDT"):
        bn = _fetch_klines_binance_usdt(sym_u, interval, limit)
        if bn:
            return json_ok(bn, source="binance")

    stq = _stooq_daily_symbol_map(sym_u)
    if stq:
        sq = _fetch_klines_stooq_daily(stq, limit)
        if sq:
            return json_ok(sq, source="stooq")

    return json_ok({**empty_payload, "limit": limit}, source="stub")


@router.get("/market/ashare/stocks")
def get_ashare_stocks() -> dict:
    """A 股标的列表（来自 newhigh 本地 DuckDB），供前端 Market 页标的选择与 K 线请求。"""
    try:
        from data_engine import get_astock_duckdb_available, get_stocks_for_api

        if get_astock_duckdb_available():
            stocks = get_stocks_for_api()
            return {"stocks": stocks, "source": "duckdb"}
    except Exception:
        _log.error("Import failed", exc_info=True)
    return {"stocks": [], "source": None}


@router.get("/stocks")
def get_stocks(limit: int = 200) -> list:
    """A 股股票列表，供前端 Stocks 页表格。优先 stocks 表，空时回退 a_stock_basic。"""
    try:
        from core.data_service import get_stock_list

        out = get_stock_list(limit=limit)
        if out:
            return out
    except Exception:
        _log.error("Import failed", exc_info=True)
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            try:
                df = conn.execute(
                    "SELECT code, name FROM a_stock_basic ORDER BY code LIMIT ?",
                    [limit],
                ).fetchdf()
                if df is not None and not df.empty:
                    return [
                        {
                            "ts_code": str(row.get("code", "")),
                            "name": str(row.get("name") or row.get("code") or ""),
                            "industry": "",
                        }
                        for _, row in df.iterrows()
                    ]
            finally:
                conn.close()
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return []


@router.get("/market/summary")
def get_market_summary() -> dict:
    """市场概览：标的数、日线条数、日期范围，供 Dashboard 与前端。"""
    try:
        from core.data_service import get_market_summary as svc_summary

        return svc_summary()
    except Exception:
        return {
            "total_stocks": 0,
            "market": "A-share",
            "daily_bars": 0,
            "date_min": None,
            "date_max": None,
        }


@router.get("/market/realtime")
def get_market_realtime(limit: int = 100) -> list:
    """实时行情快照（数据管道 a_stock_realtime），按成交额降序。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT code, name, latest_price, change_pct, volume, amount, snapshot_time FROM a_stock_realtime ORDER BY amount DESC NULLS LAST LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/limitup")
def get_market_limitup(limit: int = 100) -> list:
    """涨停池：按 code 去重、补名称/现价/涨跌、缩略时间（无原始微秒 timestamp）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 100), 500))
        df = conn.execute(
            """
            WITH ranked AS (
                SELECT u.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY u.code
                        ORDER BY u.snapshot_time DESC NULLS LAST, u.limit_up_times DESC NULLS LAST
                    ) AS rn
                FROM a_stock_limitup u
            )
            SELECT
                r.code,
                COALESCE(NULLIF(TRIM(CAST(r.name AS VARCHAR)), ''), b.name, '') AS stock_name,
                COALESCE(rt.latest_price, r.price, ld.c) AS last_price,
                COALESCE(rt.change_pct, r.change_pct) AS change_pct,
                r.limit_up_times,
                r.snapshot_time
            FROM ranked r
            LEFT JOIN a_stock_basic b ON b.code = r.code
            LEFT JOIN a_stock_realtime rt ON rt.code = r.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = r.code AND ld.rn = 1
            WHERE r.rn = 1
            ORDER BY r.limit_up_times DESC NULLS LAST, r.code
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "limit_up_times": int(row["limit_up_times"])
                    if row.get("limit_up_times") is not None
                    else None,
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/longhubang")
def get_market_longhubang(limit: int = 100) -> list:
    """
    龙虎榜明细：过滤无交易日、按 (code,lhb_date) 去重，补名称/现价/涨跌。
    历史任务曾写入 lhb_date 为空的重复行，会在 SQL 层剔除，避免「同代码刷屏 + NaT」的演示感。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 100), 500))
        df = conn.execute(
            """
            WITH cleaned AS (
                SELECT l.*
                FROM a_stock_longhubang l
                WHERE l.code IS NOT NULL
                  AND LENGTH(TRIM(CAST(l.code AS VARCHAR))) >= 4
                  AND l.lhb_date IS NOT NULL
            ),
            ranked AS (
                SELECT c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.code, c.lhb_date
                        ORDER BY c.snapshot_time DESC NULLS LAST
                    ) AS rn
                FROM cleaned c
            )
            SELECT
                r.code,
                COALESCE(NULLIF(TRIM(CAST(r.name AS VARCHAR)), ''), b.name, '') AS stock_name,
                r.lhb_date,
                r.net_buy,
                COALESCE(rt.latest_price, ld.c) AS last_price,
                rt.change_pct AS change_pct,
                r.snapshot_time
            FROM ranked r
            LEFT JOIN a_stock_basic b ON b.code = r.code
            LEFT JOIN a_stock_realtime rt ON rt.code = r.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = r.code AND ld.rn = 1
            WHERE r.rn = 1
            ORDER BY r.lhb_date DESC NULLS LAST, r.net_buy DESC NULLS LAST, r.code
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            lhb = _safe_lhb_date_str(row.get("lhb_date"))
            if not lhb:
                continue
            nb = _safe_net_buy(row.get("net_buy"))
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "lhb_date": lhb,
                    "net_buy": nb,
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/fundflow")
def get_market_fundflow(limit: int = 100) -> list:
    """资金流：按 code 取最新一条，补名称/现价/涨跌、缩略时间。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 100), 500))
        df = conn.execute(
            """
            WITH ranked AS (
                SELECT f.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.code
                        ORDER BY f.snapshot_time DESC NULLS LAST, f.snapshot_date DESC NULLS LAST
                    ) AS rn
                FROM a_stock_fundflow f
            )
            SELECT
                r.code,
                COALESCE(NULLIF(TRIM(CAST(r.name AS VARCHAR)), ''), b.name, '') AS stock_name,
                r.main_net_inflow,
                r.snapshot_date,
                r.snapshot_time,
                COALESCE(rt.latest_price, ld.c) AS last_price,
                rt.change_pct AS change_pct
            FROM ranked r
            LEFT JOIN a_stock_basic b ON b.code = r.code
            LEFT JOIN a_stock_realtime rt ON rt.code = r.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = r.code AND ld.rn = 1
            WHERE r.rn = 1
            ORDER BY r.main_net_inflow DESC NULLS LAST
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            sd = row.get("snapshot_date")
            m = row.get("main_net_inflow")
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "main_net_inflow": round(float(m), 4) if m is not None else None,
                    "snapshot_date": str(sd)[:10] if sd is not None else None,
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/emotion")
def get_market_emotion() -> dict:
    """情绪周期状态：优先 market_emotion（每日指标+状态），否则 market_emotion_state。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {
                "state": "unknown",
                "stage": "—",
                "limit_up_count": 0,
                "score": 0,
                "trade_date": None,
                "max_height": 0,
                "market_volume": 0,
            }
        conn = get_conn(read_only=False)
        row = conn.execute(
            "SELECT trade_date, limitup_count, max_height, market_volume, emotion_state FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
        ).fetchone()
        if row:
            conn.close()
            return {
                "state": row[4] or "—",
                "stage": row[4] or "—",
                "limit_up_count": int(row[1] or 0),
                "score": 50.0,
                "trade_date": str(row[0]) if row[0] else None,
                "max_height": int(row[2] or 0),
                "market_volume": float(row[3] or 0),
            }
        row = conn.execute(
            "SELECT state, stage, limit_up_count, score FROM market_emotion_state ORDER BY snapshot_time DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return {
                "state": row[0],
                "stage": row[1],
                "limit_up_count": row[2] or 0,
                "score": float(row[3] or 0),
                "trade_date": None,
                "max_height": 0,
                "market_volume": 0,
            }
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return {
        "state": "unknown",
        "stage": "—",
        "limit_up_count": 0,
        "score": 0,
        "trade_date": None,
        "max_height": 0,
        "market_volume": 0,
    }


@router.get("/market/sentiment-7d")
async def get_market_sentiment_7d() -> dict:
    """
    全市场 7 维情绪评分（对齐 ClawHub A Stock Monitor 思路，本仓库安全实现）。
    数据：优先 a_stock_realtime / 日 K；弱网 AkShare 可能极慢，本路由带硬超时以免客户端 0 字节挂死。
    """
    from data_pipeline.sentiment_7d import get_market_sentiment_7d as _compute

    sec = float(os.environ.get("SENTIMENT_7D_ENDPOINT_TIMEOUT_SEC", "45"))
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_compute, True),
            timeout=max(5.0, sec),
        )
    except asyncio.TimeoutError:
        _log.warning("sentiment-7d exceeded %.1fs (SENTIMENT_7D_ENDPOINT_TIMEOUT_SEC)", sec)
        return {
            "error": "gateway_timeout",
            "detail": (
                f"情绪计算超过 {sec:.0f}s 已中断；请关 SENTIMENT_7D_AKSHARE_ENABLE、确认 DuckDB 路径一致，"
                "或增大 SENTIMENT_7D_ENDPOINT_TIMEOUT_SEC。"
            ),
            "score": 0,
            "level": "未知",
            "emoji": "❓",
        }
    except Exception as e:
        return {"error": str(e), "score": 0, "level": "未知", "emoji": "❓"}


@router.get("/market/hotmoney")
def get_market_hotmoney(limit: int = 50) -> list:
    """游资席位胜率：缩略时间，不含原始微秒 timestamp。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT seat_name, trade_count, win_rate, avg_return, snapshot_time FROM top_hotmoney_seats ORDER BY win_rate DESC NULLS LAST LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "seat_name": str(row.get("seat_name") or ""),
                    "trade_count": int(row["trade_count"] or 0)
                    if row.get("trade_count") is not None
                    else 0,
                    "win_rate": float(row["win_rate"]) if row.get("win_rate") is not None else 0.0,
                    "avg_return": float(row["avg_return"]) if row.get("avg_return") is not None else 0.0,
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/main-themes")
def get_market_main_themes(limit: int = 10) -> list:
    """主线题材：缩略时间。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT sector, total_volume, rank, snapshot_time FROM main_themes ORDER BY rank LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "sector": str(row.get("sector") or ""),
                    "total_volume": float(row["total_volume"])
                    if row.get("total_volume") is not None
                    else 0.0,
                    "rank": int(row["rank"] or 0) if row.get("rank") is not None else 0,
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/market/sniper-candidates")
def get_sniper_candidates(limit: int = 50) -> list:
    """狙击候选：按 code 去重保留最高分；补名称/现价/涨跌（实时→涨停池→日K两日）；题材用 sector/industry 回填「未分类」。"""
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
        except Exception:
            _log.exception("ensure_tables before sniper_candidates")
        lim = max(1, min(int(limit or 50), 500))
        try:
            res = conn.execute(
                """
                WITH ranked AS (
                    SELECT s.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY s.code
                            ORDER BY s.sniper_score DESC NULLS LAST, s.snapshot_time DESC NULLS LAST
                        ) AS rn
                    FROM sniper_candidates s
                ),
                daily_rn AS (
                    SELECT
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        date,
                        CAST(close AS DOUBLE) AS close,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY date DESC
                        ) AS rn
                    FROM a_stock_daily
                ),
                d1 AS (SELECT code6, close AS c1 FROM daily_rn WHERE rn = 1),
                d2 AS (SELECT code6, close AS c2 FROM daily_rn WHERE rn = 2),
                basic_rn AS (
                    SELECT
                        name,
                        sector,
                        industry,
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY CAST(code AS VARCHAR) DESC
                        ) AS rn
                    FROM a_stock_basic
                ),
                limup_rn AS (
                    SELECT
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        change_pct,
                        snapshot_time,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY snapshot_time DESC NULLS LAST
                        ) AS rn
                    FROM a_stock_limitup
                ),
                rt_rn AS (
                    SELECT
                        split_part(CAST(code AS VARCHAR), '.', 1) AS code6,
                        latest_price,
                        change_pct,
                        ROW_NUMBER() OVER (
                            PARTITION BY split_part(CAST(code AS VARCHAR), '.', 1)
                            ORDER BY snapshot_time DESC NULLS LAST
                        ) AS rn
                    FROM a_stock_realtime
                )
                SELECT
                    r.code,
                    COALESCE(b.name, '') AS stock_name,
                    CASE
                        WHEN r.theme IS NULL OR TRIM(CAST(r.theme AS VARCHAR)) = ''
                            OR TRIM(CAST(r.theme AS VARCHAR)) = '未分类'
                        THEN COALESCE(
                            NULLIF(TRIM(CAST(b.sector AS VARCHAR)), ''),
                            NULLIF(TRIM(CAST(b.industry AS VARCHAR)), ''),
                            '—'
                        )
                        ELSE TRIM(CAST(r.theme AS VARCHAR))
                    END AS theme,
                    r.sniper_score,
                    r.confidence,
                    COALESCE(rt.latest_price, d1.c1) AS last_price,
                    COALESCE(
                        rt.change_pct,
                        lu.change_pct,
                        CASE
                            WHEN d2.c2 IS NOT NULL AND d2.c2 > 0
                            THEN (d1.c1 - d2.c2) / d2.c2 * 100.0
                            ELSE NULL
                        END
                    ) AS change_pct,
                    CASE
                        WHEN lu.snapshot_time IS NOT NULL
                            AND (r.snapshot_time IS NULL OR lu.snapshot_time > r.snapshot_time)
                        THEN lu.snapshot_time
                        ELSE r.snapshot_time
                    END AS snapshot_time
                FROM ranked r
                LEFT JOIN basic_rn b
                    ON b.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1) AND b.rn = 1
                LEFT JOIN rt_rn rt
                    ON rt.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1) AND rt.rn = 1
                LEFT JOIN d1 ON d1.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1)
                LEFT JOIN d2 ON d2.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1)
                LEFT JOIN limup_rn lu
                    ON lu.code6 = split_part(CAST(r.code AS VARCHAR), '.', 1) AND lu.rn = 1
                WHERE r.rn = 1
                ORDER BY r.sniper_score DESC NULLS LAST, r.code
                LIMIT ?
                """,
                [lim],
            )
            rows = res.fetchall() or []
            out: list = []
            for row in rows:
                (
                    code,
                    stock_name,
                    theme,
                    ss,
                    cf,
                    last_price,
                    change_pct,
                    snap,
                ) = (row + (None,) * 8)[:8]
                out.append(
                    {
                        "code": str(code or ""),
                        "stock_name": str(stock_name or "").strip(),
                        "theme": str(theme or "").strip() or "—",
                        "sniper_score": float(ss) if ss is not None else None,
                        "confidence": float(cf) if cf is not None else None,
                        "last_price": _optional_price(last_price),
                        "change_pct": _optional_pct(change_pct),
                        "updated_at": _short_ts_for_signal(snap),
                    }
                )
            return out
        except Exception:
            _log.exception("get_sniper_candidates full query failed")
            try:
                return _sniper_candidates_minimal(conn, lim)
            except Exception:
                _log.exception("get_sniper_candidates minimal failed")
                return []
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
    except Exception:
        return []
