"""
模拟盘引擎：消费 trade_signals，生成模拟订单，维护持仓与资金快照。
依赖 DuckDB 表：sim_positions, sim_orders, sim_account_snapshots（由 data_pipeline 的 ensure_tables 创建）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_INITIAL_CASH = 1_000_000.0
DEFAULT_LOT_SIZE = 100
DEFAULT_STUB_PRICE = 10.0


def _get_conn():
    from data_pipeline.storage.duckdb_manager import get_conn, get_db_path, ensure_tables
    import os
    if not os.path.isfile(get_db_path()):
        os.makedirs(os.path.dirname(get_db_path()) or ".", exist_ok=True)
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def _last_cash_and_equity(conn) -> tuple[float, float]:
    """返回 (cash, equity)。若无快照则用默认初始资金，equity=0。"""
    try:
        row = conn.execute("""
            SELECT cash, equity FROM sim_account_snapshots ORDER BY snapshot_time DESC LIMIT 1
        """).fetchone()
        if row:
            return float(row[0]), float(row[1])
    except Exception:
        pass
    return DEFAULT_INITIAL_CASH, 0.0


def _positions_list(conn) -> List[Dict[str, Any]]:
    """当前 sim_positions 列表。"""
    try:
        df = conn.execute("""
            SELECT code, side, qty, avg_price, updated_at FROM sim_positions
        """).fetchdf()
        if df is None or df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        return []


def _next_order_id(conn) -> int:
    r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM sim_orders").fetchone()
    return int(r[0]) if r else 1


def _price_for_code(conn, code: str) -> float:
    """从 a_stock_realtime 或 a_stock_daily 取最新价，否则返回 DEFAULT_STUB_PRICE。"""
    try:
        row = conn.execute("""
            SELECT latest_price FROM a_stock_realtime WHERE code = ? ORDER BY snapshot_time DESC LIMIT 1
        """, [code]).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass
    try:
        row = conn.execute("""
            SELECT close FROM a_stock_daily WHERE code = ? ORDER BY date DESC LIMIT 1
        """, [code]).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception:
        pass
    return DEFAULT_STUB_PRICE


def step_simulated(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    initial_cash: float = DEFAULT_INITIAL_CASH,
    lot_size: int = DEFAULT_LOT_SIZE,
    max_buys: int = 10,
    max_sells: int = 10,
    risk_check: bool = False,
) -> Dict[str, Any]:
    """
    执行一步模拟：从 trade_signals 读取买卖信号，生成 sim_orders，更新 sim_positions 与 sim_account_snapshots。
    risk_check=True 时先做风控评估，不通过则本步不执行并返回 risk_violations。
    返回本步统计：orders_created, cash, equity, total_assets。
    """
    from execution_engine.signal_executor import get_actionable_signals

    conn = _get_conn()
    try:
        cash, equity = _last_cash_and_equity(conn)
        positions = {p["code"]: p for p in _positions_list(conn)}
        total_assets = cash + equity
        if risk_check and total_assets > 0:
            try:
                import sys
                import os
                _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                for _d in ["risk-engine/src", "data-pipeline/src"]:
                    _p = os.path.join(_root, _d)
                    if os.path.isdir(_p) and _p not in sys.path:
                        sys.path.insert(0, _p)
                from risk_engine import evaluate
                pos_list = [{"code": p["code"], "qty": p["qty"], "avg_price": p.get("avg_price") or 0} for p in positions.values()]
                res = evaluate(positions=pos_list, total_assets=total_assets, conn=conn)
                if not res.get("pass"):
                    conn.close()
                    return {"ok": False, "risk_violations": res.get("violations") or [], "orders_created": 0}
            except Exception:
                pass
        buys, sells = get_actionable_signals(
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            limit=max(max_buys, max_sells),
        )
        orders_created = 0
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # 先处理卖出：有持仓则按仓位卖
        for s in sells[:max_sells]:
            code = s.get("code", "")
            if not code:
                continue
            pos = positions.get(code)
            if not pos or float(pos.get("qty") or 0) <= 0:
                continue
            qty = min(lot_size, float(pos["qty"]))
            price = s.get("target_price") or _price_for_code(conn, code)
            if price <= 0:
                price = _price_for_code(conn, code)
            oid = _next_order_id(conn)
            conn.execute("""
                INSERT INTO sim_orders (id, code, side, qty, price, status, created_at, filled_at)
                VALUES (?, ?, 'SELL', ?, ?, 'filled', ?, ?)
            """, [oid, code, qty, price, now, now])
            orders_created += 1
            new_qty = float(pos["qty"]) - qty
            cash += qty * price
            if new_qty <= 0:
                conn.execute("DELETE FROM sim_positions WHERE code = ? AND side = ?", [code, pos.get("side", "LONG")])
                positions.pop(code, None)
            else:
                conn.execute(
                    "UPDATE sim_positions SET qty = ?, updated_at = ? WHERE code = ? AND side = ?",
                    [new_qty, now, code, pos.get("side", "LONG")],
                )
                positions[code] = {**pos, "qty": new_qty}

        # 再处理买入
        for b in buys[:max_buys]:
            code = b.get("code", "")
            if not code:
                continue
            price = b.get("target_price") or _price_for_code(conn, code)
            if price <= 0:
                price = _price_for_code(conn, code)
            cost = lot_size * price
            if cash < cost:
                continue
            oid = _next_order_id(conn)
            conn.execute("""
                INSERT INTO sim_orders (id, code, side, qty, price, status, created_at, filled_at)
                VALUES (?, ?, 'BUY', ?, ?, 'filled', ?, ?)
            """, [oid, code, lot_size, price, now, now])
            orders_created += 1
            cash -= cost
            pos = positions.get(code)
            if pos:
                old_qty, old_avg = float(pos["qty"]), float(pos.get("avg_price") or 0)
                new_qty = old_qty + lot_size
                new_avg = (old_qty * old_avg + cost) / new_qty if new_qty else price
                conn.execute(
                    "UPDATE sim_positions SET qty = ?, avg_price = ?, updated_at = ? WHERE code = ? AND side = ?",
                    [new_qty, new_avg, now, code, pos.get("side", "LONG")],
                )
                positions[code] = {**pos, "qty": new_qty, "avg_price": new_avg}
            else:
                conn.execute("""
                    INSERT INTO sim_positions (code, side, qty, avg_price, updated_at)
                    VALUES (?, 'LONG', ?, ?, ?)
                """, [code, lot_size, price, now])
                positions[code] = {"code": code, "side": "LONG", "qty": lot_size, "avg_price": price}

        # 计算当前权益（持仓市值用 avg_price 近似）
        equity = 0.0
        for p in positions.values():
            equity += float(p["qty"]) * float(p.get("avg_price") or 0)
        total_assets = cash + equity
        conn.execute(
            "INSERT INTO sim_account_snapshots (snapshot_time, cash, equity, total_assets) VALUES (?, ?, ?, ?)",
            [now, cash, equity, total_assets],
        )
        conn.close()
        return {
            "ok": True,
            "orders_created": orders_created,
            "cash": round(cash, 2),
            "equity": round(equity, 2),
            "total_assets": round(total_assets, 2),
        }
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return {"ok": False, "error": str(e), "orders_created": 0}


def get_positions(limit: int = 100) -> List[Dict[str, Any]]:
    """返回当前模拟持仓列表。"""
    conn = _get_conn()
    try:
        df = conn.execute("""
            SELECT code, side, qty, avg_price, updated_at FROM sim_positions ORDER BY updated_at DESC LIMIT ?
        """, [limit]).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []


def get_orders(limit: int = 100, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """返回模拟订单列表；status 可选 'pending'/'filled' 等。"""
    conn = _get_conn()
    try:
        if status:
            df = conn.execute("""
                SELECT id, code, side, qty, price, status, created_at, filled_at
                FROM sim_orders WHERE status = ? ORDER BY created_at DESC LIMIT ?
            """, [status, limit]).fetchdf()
        else:
            df = conn.execute("""
                SELECT id, code, side, qty, price, status, created_at, filled_at
                FROM sim_orders ORDER BY created_at DESC LIMIT ?
            """, [limit]).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []


def get_account_snapshots(limit: int = 100) -> List[Dict[str, Any]]:
    """返回资金快照列表（按时间倒序）。"""
    conn = _get_conn()
    try:
        df = conn.execute("""
            SELECT snapshot_time, cash, equity, total_assets FROM sim_account_snapshots ORDER BY snapshot_time DESC LIMIT ?
        """, [limit]).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return []
