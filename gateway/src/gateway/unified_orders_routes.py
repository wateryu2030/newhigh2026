"""
Hongshan /api/orders/* 兼容：纸面委托写入 DuckDB（hongshan_paper_orders），资金扣减 hongshan_accounts。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .paper_fill_engine import run_paper_fills

_log = logging.getLogger(__name__)


class OrderCreate(BaseModel):
    symbol: str = Field(..., min_length=1)
    order_type: str = Field(..., description="buy / sell")
    order_style: str = Field(default="limit")
    order_price: float = Field(..., ge=0)
    order_quantity: int = Field(..., gt=0)
    # Vue / 模拟盘在 JSON body 中传 user_id；亦兼容 Query
    user_id: Optional[str] = Field(default=None, max_length=128)


def _open():
    import os

    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    if not os.path.isfile(get_db_path()):
        return None
    c = get_conn(read_only=False)
    ensure_tables(c)
    return c


def _row_to_response(row: tuple) -> dict[str, Any]:
    oid, uid, sym, sname, otype, ostyle, price, qty, filled, status, ot = (row + (None,) * 11)[:11]
    fq = int(filled or 0)
    op = float(price or 0)
    return {
        "id": str(oid),
        "symbol": str(sym),
        "stock_name": str(sname or "") or None,
        "order_type": str(otype),
        "order_style": str(ostyle or "limit"),
        "order_price": op,
        "order_quantity": int(qty or 0),
        "filled_quantity": fq,
        "filled_amount": round(op * fq, 4),
        "status": str(status or "pending"),
        "order_time": ot,
    }


def build_unified_orders_routes_router() -> APIRouter:
    r = APIRouter(prefix="/orders", tags=["orders-unified"])

    @r.post("/orders")
    def create_order(
        order_data: OrderCreate,
        user_id: Optional[str] = Query(None, description="用户 ID（可与 body.user_id 二选一）"),
    ) -> dict:
        uid = (order_data.user_id or user_id or "").strip()
        if not uid:
            raise HTTPException(status_code=422, detail="缺少 user_id（请放在 Query 或 JSON body）")
        conn = _open()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            acc = conn.execute(
                "SELECT available_cash FROM hongshan_accounts WHERE user_id = ?",
                [uid],
            ).fetchone()
            if not acc and uid == "demo-user":
                try:
                    conn.execute(
                        """
                        INSERT INTO hongshan_accounts (user_id, available_cash, frozen_cash, total_assets, updated_at)
                        VALUES (?, 500000, 0, 500000, CURRENT_TIMESTAMP)
                        """,
                        [uid],
                    )
                except Exception:
                    pass
                acc = conn.execute(
                    "SELECT available_cash FROM hongshan_accounts WHERE user_id = ?",
                    [uid],
                ).fetchone()
            if not acc:
                raise HTTPException(status_code=404, detail="用户账户不存在")
            cash = float(acc[0] or 0)
            need = float(order_data.order_price) * int(order_data.order_quantity)
            ot = order_data.order_type.lower().strip()
            if ot == "buy":
                if cash < need:
                    raise HTTPException(
                        status_code=400,
                        detail=f"资金不足，需要 {need:.2f}，可用 {cash:.2f}",
                    )
                conn.execute(
                    """
                    UPDATE hongshan_accounts
                    SET available_cash = available_cash - ?,
                        total_assets = total_assets,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    [need, uid],
                )
            elif ot != "sell":
                raise HTTPException(status_code=400, detail="order_type 须为 buy 或 sell")
            oid = str(uuid.uuid4())
            c6 = "".join(c for c in order_data.symbol if c.isdigit())[:6] or order_data.symbol
            now = datetime.now(timezone.utc)
            conn.execute(
                """
                INSERT INTO hongshan_paper_orders (
                    id, user_id, symbol, stock_name, order_type, order_style,
                    order_price, order_quantity, filled_quantity, status, order_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'pending', ?)
                """,
                [
                    oid,
                    uid,
                    c6,
                    None,
                    ot,
                    order_data.order_style,
                    float(order_data.order_price),
                    int(order_data.order_quantity),
                    now,
                ],
            )
            out = _row_to_response(
                (
                    oid,
                    uid,
                    c6,
                    None,
                    ot,
                    order_data.order_style,
                    order_data.order_price,
                    order_data.order_quantity,
                    0,
                    "pending",
                    now,
                )
            )
            try:
                fr = run_paper_fills(conn)
                if fr.get("filled"):
                    row2 = conn.execute(
                        """
                        SELECT id, user_id, symbol, stock_name, order_type, order_style,
                               order_price, order_quantity, filled_quantity, status, order_time
                        FROM hongshan_paper_orders WHERE id = ?
                        """,
                        [oid],
                    ).fetchone()
                    if row2:
                        out = _row_to_response(row2)
            except Exception:
                _log.debug("paper fill after create failed", exc_info=True)
            return out
        except HTTPException:
            raise
        except Exception as e:
            _log.exception("create_order")
            raise HTTPException(status_code=500, detail=str(e)[:200]) from e
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @r.get("/orders")
    def list_orders(
        user_id: str = Query(...),
        limit: int = Query(100, le=500),
        status: Optional[str] = Query(None, description="可选：pending / filled / cancelled"),
    ) -> list:
        conn = _open()
        if not conn:
            return []
        try:
            st = (status or "").strip().lower() or None
            if st:
                rows = conn.execute(
                    """
                    SELECT id, user_id, symbol, stock_name, order_type, order_style,
                           order_price, order_quantity, filled_quantity, status, order_time
                    FROM hongshan_paper_orders
                    WHERE user_id = ? AND LOWER(CAST(status AS VARCHAR)) = ?
                    ORDER BY order_time DESC
                    LIMIT ?
                    """,
                    [user_id, st, limit],
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, user_id, symbol, stock_name, order_type, order_style,
                           order_price, order_quantity, filled_quantity, status, order_time
                    FROM hongshan_paper_orders
                    WHERE user_id = ?
                    ORDER BY order_time DESC
                    LIMIT ?
                    """,
                    [user_id, limit],
                ).fetchall()
            return [_row_to_response(t) for t in (rows or [])]
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @r.get("/orders/{order_id}")
    def get_order(order_id: str, user_id: str = Query(...)) -> dict:
        conn = _open()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            row = conn.execute(
                """
                SELECT id, user_id, symbol, stock_name, order_type, order_style,
                       order_price, order_quantity, filled_quantity, status, order_time
                FROM hongshan_paper_orders
                WHERE id = ? AND user_id = ?
                """,
                [order_id, user_id],
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="委托不存在")
            return _row_to_response(row)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @r.post("/orders/{order_id}/cancel")
    def cancel_order(order_id: str, user_id: str = Query(...)) -> dict:
        conn = _open()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            row = conn.execute(
                """
                SELECT id, order_type, order_price, order_quantity, status
                FROM hongshan_paper_orders WHERE id = ? AND user_id = ?
                """,
                [order_id, user_id],
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="委托不存在")
            st = str(row[4] or "")
            if st != "pending":
                raise HTTPException(status_code=400, detail="当前状态不可撤单")
            otype = str(row[1] or "")
            price = float(row[2] or 0)
            qty = int(row[3] or 0)
            if otype == "buy":
                refund = price * qty
                conn.execute(
                    """
                    UPDATE hongshan_accounts
                    SET available_cash = available_cash + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    [refund, user_id],
                )
            conn.execute(
                "UPDATE hongshan_paper_orders SET status = 'cancelled' WHERE id = ?",
                [order_id],
            )
            return {"ok": True, "id": order_id, "status": "cancelled"}
        except HTTPException:
            raise
        except Exception as e:
            _log.exception("cancel_order")
            raise HTTPException(status_code=500, detail=str(e)[:200]) from e
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @r.post("/fill-run")
    def trigger_paper_fill_run(user_id: Optional[str] = Query(None, description="仅撮合该用户，缺省为全量")) -> dict:
        conn = _open()
        if not conn:
            raise HTTPException(status_code=503, detail="数据库不可用")
        try:
            return run_paper_fills(conn, user_id=user_id)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return r
