"""
Hongshan /api/positions/* 兼容：账户取自 hongshan_accounts；持仓在有 status=filled 成交记录时按标的聚合，否则空列表。
"""

from __future__ import annotations

import logging
from typing import Any, List

from fastapi import APIRouter, HTTPException, Query

_log = logging.getLogger(__name__)


def _open():
    import os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    if not os.path.isfile(get_db_path()):
        return None
    c = get_conn(read_only=False)
    ensure_tables(c)
    return c


def _code_daily_param(code6: str) -> str:
    if not code6:
        return "000001.SZ"
    if code6.startswith("6"):
        return f"{code6}.SH"
    if code6.startswith(("4", "8")):
        return f"{code6}.BJ"
    return f"{code6}.SZ"


def _seed_demo_account(conn, user_id: str) -> None:
    if user_id != "demo-user":
        return
    try:
        conn.execute(
            """
            INSERT INTO hongshan_accounts (user_id, available_cash, frozen_cash, total_assets, updated_at)
            VALUES (?, 500000, 0, 500000, CURRENT_TIMESTAMP)
            """,
            [user_id],
        )
    except Exception:
        pass


def _position_rows(user_id: str):
    conn = _open()
    if not conn:
        return None, []
    try:
        rows = conn.execute(
            """
            SELECT symbol,
                SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'buy'
                    THEN COALESCE(filled_quantity, order_quantity) ELSE 0 END) AS buy_filled,
                SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'sell'
                    THEN COALESCE(filled_quantity, order_quantity) ELSE 0 END) AS sell_filled,
                SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'buy'
                    THEN order_price * COALESCE(NULLIF(filled_quantity, 0), order_quantity) ELSE 0 END)
                / NULLIF(SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'buy'
                    THEN COALESCE(NULLIF(filled_quantity, 0), order_quantity) ELSE 0 END), 0) AS avg_cost
            FROM hongshan_paper_orders
            WHERE user_id = ? AND LOWER(CAST(status AS VARCHAR)) = 'filled'
            GROUP BY symbol
            HAVING SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'buy'
                    THEN COALESCE(filled_quantity, order_quantity) ELSE 0 END)
                > SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'sell'
                    THEN COALESCE(filled_quantity, order_quantity) ELSE 0 END)
            """,
            [user_id],
        ).fetchall()
        return conn, list(rows or [])
    except Exception:
        _log.exception("position aggregate")
        try:
            conn.close()
        except Exception:
            pass
        return None, []


def _build_position_items(rows: list) -> List[dict[str, Any]]:
    out: List[dict[str, Any]] = []
    for row in rows:
        sym, bf, sf, avg_c = (row + (None,) * 4)[:4]
        buy_n = int(bf or 0)
        sell_n = int(sf or 0)
        qty = buy_n - sell_n
        if qty <= 0:
            continue
        code6 = "".join(c for c in str(sym) if c.isdigit())[:6] or str(sym)
        cost = float(avg_c or 0)
        cur = cost
        name = ""
        c2 = _open()
        if c2:
            try:
                one = c2.execute(
                    """
                    SELECT name, latest_price FROM a_stock_realtime
                    WHERE REPLACE(REPLACE(CAST(code AS VARCHAR), '.SZ', ''), '.SH', '') = ?
                    LIMIT 1
                    """,
                    [code6],
                ).fetchone()
                if one:
                    name = str(one[0] or "")
                    if one[1] is not None:
                        cur = float(one[1])
                else:
                    drow = c2.execute(
                        """
                        SELECT close FROM a_stock_daily
                        WHERE code = ? ORDER BY date DESC LIMIT 1
                        """,
                        [_code_daily_param(code6)],
                    ).fetchone()
                    if drow and drow[0] is not None:
                        cur = float(drow[0])
                        nb = c2.execute(
                            """
                            SELECT name FROM a_stock_basic
                            WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
                            LIMIT 1
                            """,
                            [code6],
                        ).fetchone()
                        if nb:
                            name = str(nb[0] or "")
            except Exception:
                _log.debug("position price lookup skip", exc_info=True)
            finally:
                try:
                    c2.close()
                except Exception:
                    pass
        mv = cur * qty
        profit = (cur - cost) * qty
        pr = round(100.0 * (cur - cost) / cost, 2) if cost > 1e-9 else 0.0
        out.append(
            {
                "symbol": code6,
                "stock_name": name or None,
                "cost_price": round(cost, 4),
                "current_price": round(cur, 4),
                "quantity": qty,
                "market_value": round(mv, 4),
                "profit": round(profit, 4),
                "profit_rate": pr,
            }
        )
    return out


def positions_for_user(user_id: str) -> List[dict[str, Any]]:
    conn, rows = _position_rows(user_id)
    if conn:
        try:
            conn.close()
        except Exception:
            pass
    return _build_position_items(rows)


def build_unified_positions_router() -> APIRouter:
    r = APIRouter(prefix="/positions", tags=["positions-unified"])

    @r.get("/positions")
    def list_positions(
        user_id: str = Query(...),
        show_closed: bool = Query(False),
    ) -> List[dict[str, Any]]:
        _ = show_closed
        return positions_for_user(user_id)

    @r.get("/account")
    def get_account(user_id: str = Query(...)) -> dict[str, Any]:
        conn = _open()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            row = conn.execute(
                """
                SELECT available_cash, frozen_cash, total_assets
                FROM hongshan_accounts WHERE user_id = ?
                """,
                [user_id],
            ).fetchone()
            if not row:
                _seed_demo_account(conn, user_id)
                row = conn.execute(
                    """
                    SELECT available_cash, frozen_cash, total_assets
                    FROM hongshan_accounts WHERE user_id = ?
                    """,
                    [user_id],
                ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="用户账户不存在")
            cash = float(row[0] or 0)
            frozen = float(row[1] or 0)
            total_row = float(row[2] or 0)
        finally:
            try:
                conn.close()
            except Exception:
                pass

        pos = positions_for_user(user_id)
        mv = sum(float(p.get("market_value") or 0) for p in pos)
        total_assets = max(total_row, cash + frozen + mv)
        return {
            "available_cash": cash,
            "frozen_cash": frozen,
            "market_value": round(mv, 4),
            "total_assets": round(total_assets, 4),
            "total_profit": round(sum(float(p.get("profit") or 0) for p in pos), 4),
            "total_profit_rate": 0.0,
        }

    return r
