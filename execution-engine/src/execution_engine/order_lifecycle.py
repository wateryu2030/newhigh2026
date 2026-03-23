"""
订单生命周期：状态机 NEW → SUBMITTED → FILLED / CANCELLED。
与 sim_orders 表配合，供执行引擎与 Gateway 使用。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class OrderState(str, Enum):
    NEW = "new"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"


# 与 sim_orders.status 兼容的取值
STATE_TO_DB = {
    OrderState.NEW: "pending",
    OrderState.SUBMITTED: "submitted",
    OrderState.FILLED: "filled",
    OrderState.CANCELLED: "cancelled",
}
DB_TO_STATE = {v: k for k, v in STATE_TO_DB.items()}


def _get_conn():
    from data_pipeline.storage.duckdb_manager import get_conn, get_db_path, ensure_tables
    import os

    if not os.path.isfile(get_db_path()):
        os.makedirs(os.path.dirname(get_db_path()) or ".", exist_ok=True)
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def transition(
    order_id: int,
    event: str,
    conn: Any = None,
) -> Dict[str, Any]:
    """
    状态转换：根据事件更新订单状态。
    event: 'submit' -> NEW→SUBMITTED; 'fill' -> SUBMITTED→FILLED; 'cancel' -> NEW/SUBMITTED→CANCELLED。
    返回 {"ok": bool, "order_id": int, "state": str, "error": str?}。
    """
    close_conn = conn is None
    if conn is None:
        conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, code, side, qty, price, status FROM sim_orders WHERE id = ?",
            [int(order_id)],
        ).fetchone()
        if not row:
            return {"ok": False, "order_id": order_id, "state": "", "error": "order_not_found"}
        current_db = (row[5] or "pending").strip().lower()
        current = DB_TO_STATE.get(current_db, OrderState.NEW)

        if event == "submit":
            if current == OrderState.NEW:
                conn.execute(
                    "UPDATE sim_orders SET status = ? WHERE id = ?",
                    [STATE_TO_DB[OrderState.SUBMITTED], order_id],
                )
                return {"ok": True, "order_id": order_id, "state": OrderState.SUBMITTED.value}
            return {
                "ok": False,
                "order_id": order_id,
                "state": current.value,
                "error": "invalid_transition",
            }

        if event == "fill":
            if current in (OrderState.NEW, OrderState.SUBMITTED):
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                conn.execute(
                    "UPDATE sim_orders SET status = ?, filled_at = ? WHERE id = ?",
                    [STATE_TO_DB[OrderState.FILLED], now, order_id],
                )
                return {"ok": True, "order_id": order_id, "state": OrderState.FILLED.value}
            return {
                "ok": False,
                "order_id": order_id,
                "state": current.value,
                "error": "invalid_transition",
            }

        if event == "cancel":
            if current in (OrderState.NEW, OrderState.SUBMITTED):
                conn.execute(
                    "UPDATE sim_orders SET status = ? WHERE id = ?",
                    [STATE_TO_DB[OrderState.CANCELLED], order_id],
                )
                return {"ok": True, "order_id": order_id, "state": OrderState.CANCELLED.value}
            return {
                "ok": False,
                "order_id": order_id,
                "state": current.value,
                "error": "invalid_transition",
            }

        return {"ok": False, "order_id": order_id, "state": current.value, "error": "unknown_event"}
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def get_order_state(order_id: int, conn: Any = None) -> Optional[str]:
    """返回订单当前状态（new/submitted/filled/cancelled）。"""
    close_conn = conn is None
    if conn is None:
        conn = _get_conn()
    try:
        row = conn.execute("SELECT status FROM sim_orders WHERE id = ?", [order_id]).fetchone()
        if not row:
            return None
        db_status = (row[0] or "pending").strip().lower()
        return DB_TO_STATE.get(db_status, OrderState.NEW).value
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass
