"""
Hongshan /api/stocks/* 兼容路由：数据取自 DuckDB（a_stock_realtime / a_stock_daily / a_stock_basic），与主行情栈一致。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.ashare_symbol import normalize_ashare_symbol_bj_display

_log = logging.getLogger(__name__)


def _code6(symbol: str) -> str:
    raw = (symbol or "").strip().upper().split(".", 1)[0]
    return "".join(c for c in raw if c.isdigit())[:6]


def _to_exchange_symbol(code6: str) -> str:
    if not code6 or len(code6) < 6:
        return "000001.SZ"
    return normalize_ashare_symbol_bj_display(code6)


def _open():
    import os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    if not os.path.isfile(get_db_path()):
        return None
    c = get_conn(read_only=False)
    ensure_tables(c)
    return c


def _get_quote_core(symbol: str) -> dict:
    c6 = _code6(symbol)
    if not c6:
        raise HTTPException(status_code=400, detail="无效代码")
    ex = _to_exchange_symbol(c6)
    conn = _open()
    if not conn:
        raise HTTPException(status_code=503, detail="无数据库")
    try:
        row = conn.execute(
            """
            SELECT code, name, latest_price, change_pct, volume, amount, snapshot_time
            FROM a_stock_realtime
            WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
               OR code = ? OR code = ?
            ORDER BY snapshot_time DESC NULLS LAST
            LIMIT 1
            """,
            [c6, c6, ex],
        ).fetchone()
        if not row:
            drow = conn.execute(
                """
                SELECT code, close, NULL::DOUBLE, volume, amount, NULL::TIMESTAMP
                FROM a_stock_daily
                WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
                   OR code = ?
                ORDER BY date DESC
                LIMIT 1
                """,
                [c6, ex],
            ).fetchone()
            if drow:
                code_d, price, chg, vol, amt, snap = (
                    drow[0],
                    drow[1],
                    drow[2],
                    drow[3],
                    drow[4],
                    drow[5],
                )
                name = ""
                try:
                    br = conn.execute(
                        """
                        SELECT name FROM a_stock_basic
                        WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
                        LIMIT 1
                        """,
                        [c6],
                    ).fetchone()
                    if br:
                        name = str(br[0] or "")
                except Exception:
                    pass
                row = (code_d, name, price, chg, vol, amt, snap)
        if not row:
            raise HTTPException(status_code=404, detail="股票未找到")
        code, name, price, chg, vol, amt, snap = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
        )
        price_f = float(price or 0)
        chg_f = float(chg) if chg is not None else 0.0
        return {
            "symbol": c6,
            "name": str(name or ""),
            "current_price": price_f,
            "change": 0.0,
            "change_percent": chg_f,
            "open": price_f,
            "high": price_f,
            "low": price_f,
            "pre_close": price_f / (1 + chg_f / 100.0) if chg_f and chg_f != -100 else price_f,
            "volume": int(vol or 0),
            "amount": float(amt or 0),
            "timestamp": datetime_iso(snap),
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def datetime_iso(snap: Any) -> str:
    if snap is None:
        return datetime_now_iso()
    try:
        return snap.isoformat()
    except Exception:
        return str(snap)


def datetime_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def build_unified_stocks_router() -> APIRouter:
    r = APIRouter(prefix="/stocks", tags=["stocks-unified"])

    @r.get("/search")
    def search_stocks(keyword: str = Query(..., min_length=1)) -> dict:
        kw = f"%{keyword.strip()}%"
        conn = _open()
        if not conn:
            return {"data": [], "count": 0}
        try:
            rows = conn.execute(
                """
                SELECT code, name FROM a_stock_basic
                WHERE CAST(code AS VARCHAR) LIKE ? OR CAST(name AS VARCHAR) LIKE ?
                LIMIT 30
                """,
                [kw, kw],
            ).fetchall()
            data = []
            for row in rows or []:
                c, n = row[0], row[1]
                c6b = _code6(str(c))
                if c6b:
                    data.append({"symbol": c6b, "name": str(n or "")})
            return {"data": data, "count": len(data)}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @r.get("/quotes")
    def get_quotes(symbols: str = Query(..., description="逗号分隔代码")) -> dict:
        sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
        quotes: list[dict] = []
        for s in sym_list:
            try:
                quotes.append(_get_quote_core(s))
            except HTTPException:
                continue
        return {"quotes": quotes, "count": len(quotes)}

    @r.get("/quote/{symbol}")
    def get_quote(symbol: str) -> dict:
        return _get_quote_core(symbol)

    @r.get("/{symbol}/history")
    def get_history(
        symbol: str,
        start_date: date = Query(..., description="开始 YYYY-MM-DD"),
        end_date: date = Query(..., description="结束 YYYY-MM-DD"),
        adjust: str = Query("qfq"),
    ) -> dict:
        c6 = _code6(symbol)
        if not c6:
            raise HTTPException(status_code=400, detail="无效代码")
        ex_sym = _to_exchange_symbol(c6)
        conn = _open()
        if not conn:
            return {"data": [], "count": 0}
        try:
            rows = conn.execute(
                """
                SELECT date, open, high, low, close, volume, amount
                FROM a_stock_daily
                WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
                  AND date >= ? AND date <= ?
                ORDER BY date ASC
                """,
                [c6, start_date, end_date],
            ).fetchall()
            if not rows:
                rows = conn.execute(
                    """
                    SELECT date, open, high, low, close, volume, amount
                    FROM a_stock_daily
                    WHERE code = ? AND date >= ? AND date <= ?
                    ORDER BY date ASC
                    """,
                    [ex_sym, start_date, end_date],
                ).fetchall()
            data = []
            prev_c: float | None = None
            for row in rows or []:
                d, o, h, l, c, v, amt = (row + (None,) * 7)[:7]
                close_f = float(c or 0)
                chgp = 0.0
                if prev_c is not None and prev_c > 0:
                    chgp = (close_f - prev_c) / prev_c * 100.0
                prev_c = close_f
                data.append(
                    {
                        "date": str(d)[:10],
                        "open": float(o or 0),
                        "high": float(h or 0),
                        "low": float(l or 0),
                        "close": close_f,
                        "volume": int(v or 0),
                        "amount": float(amt or 0),
                        "change_percent": chgp,
                    }
                )
            return {"data": data, "count": len(data)}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @r.get("/{symbol}/kline")
    def get_kline(
        symbol: str,
        period: str = Query("daily"),
        limit: int = Query(100, le=1000),
    ) -> dict:
        sym = _to_exchange_symbol(_code6(symbol))
        try:
            from .endpoints import get_klines

            raw = get_klines(symbol=sym, interval="1d", limit=limit)
        except Exception as e:
            _log.exception("kline compat")
            raise HTTPException(status_code=500, detail=str(e)[:120]) from e
        payload: Any = raw
        if isinstance(raw, dict) and raw.get("ok") and isinstance(raw.get("data"), dict):
            payload = raw["data"]
        if not isinstance(payload, dict):
            return {"data": [], "count": 0}
        bars = payload.get("data") or []
        kline_data = []
        for b in bars:
            if not isinstance(b, dict):
                continue
            ts = b.get("t") or b.get("time")
            kline_data.append(
                {
                    "time": str(ts)[:10] if ts else "",
                    "open": float(b.get("o") or b.get("open") or 0),
                    "high": float(b.get("h") or b.get("high") or 0),
                    "low": float(b.get("l") or b.get("low") or 0),
                    "close": float(b.get("c") or b.get("close") or 0),
                    "volume": int(float(b.get("v") or b.get("volume") or 0)),
                }
            )
        return {"data": kline_data, "count": len(kline_data)}

    @r.get("/{symbol}/info")
    def get_info(symbol: str) -> dict:
        c6 = _code6(symbol)
        if not c6:
            raise HTTPException(status_code=400, detail="无效代码")
        conn = _open()
        if not conn:
            raise HTTPException(status_code=503, detail="无数据库")
        try:
            row = conn.execute(
                """
                SELECT code, name, sector FROM a_stock_basic
                WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
                LIMIT 1
                """,
                [c6],
            ).fetchone()
            name = str(row[1] or "") if row else ""
            sector = str(row[2] or "") if row and len(row) > 2 else ""
            q = _get_quote_core(symbol)
            return {
                "symbol": c6,
                "name": q.get("name") or name,
                "exchange": "SH" if c6.startswith("6") else "SZ",
                "industry": sector,
                "sector": sector,
                "list_date": "",
                "total_shares": "",
                "circulating_shares": "",
                "pe_ratio": "",
                "pb_ratio": "",
                "current_price": q.get("current_price"),
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return r
