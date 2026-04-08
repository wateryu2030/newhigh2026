"""
纸面委托撮合：将满足行情条件的 pending 标为 filled，并维护卖出成交资金入账。

规则（简化）：
- order_style=market：只要有有效行情价即成交。
- limit + buy：最新价 <= 委托价（买在限价及以下）。
- limit + sell：最新价 >= 委托价（卖在限价及以上）。
- 卖出：同一用户、同一标的在扣减「其他未成交卖单占用」后，可卖数量须 >= 本单数量。

买入：下单时已扣款，成交不再动资金。卖出：成交时 available_cash += 委托价 * 数量（与现价简化一致，避免部分退款复杂度）。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from core.ashare_symbol import normalize_ashare_symbol_bj_display

_log = logging.getLogger(__name__)


def _ex_symbol(code6: str) -> str:
    c = (code6 or "").strip()
    if len(c) < 6:
        c = c.zfill(6) if c.isdigit() else "000001"
    c = "".join(x for x in c if x.isdigit())[:6] or "000001"
    return normalize_ashare_symbol_bj_display(c)


def _last_price_and_name(conn, code6: str) -> tuple[Optional[float], Optional[str]]:
    c6 = "".join(c for c in (code6 or "") if c.isdigit())[:6]
    if not c6:
        return None, None
    ex = _ex_symbol(c6)
    try:
        row = conn.execute(
            """
            SELECT name, latest_price
            FROM a_stock_realtime
            WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
               OR code = ? OR code = ?
            ORDER BY snapshot_time DESC NULLS LAST
            LIMIT 1
            """,
            [c6, c6, ex],
        ).fetchone()
        if row and row[1] is not None:
            return float(row[1]), str(row[0] or "") or None
        row = conn.execute(
            """
            SELECT close
            FROM a_stock_daily
            WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
               OR code = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            [c6, ex],
        ).fetchone()
        if row and row[0] is not None:
            px = float(row[0])
            nm: Optional[str] = None
            try:
                br = conn.execute(
                    """
                    SELECT name FROM a_stock_basic
                    WHERE split_part(upper(trim(cast(code as varchar))), '.', 1) = ?
                    LIMIT 1
                    """,
                    [c6],
                ).fetchone()
                if br and br[0]:
                    nm = str(br[0])
            except Exception:
                pass
            return px, nm
    except Exception:
        _log.debug("last price lookup failed", exc_info=True)
    return None, None


def _price_matches(style: str, side: str, order_price: float, last: float) -> bool:
    st = (style or "limit").strip().lower()
    if st == "market":
        return True
    op = float(order_price or 0)
    if side == "buy":
        return last <= op + 1e-9
    return last >= op - 1e-9


def run_paper_fills(conn, user_id: Optional[str] = None) -> dict[str, Any]:
    """
    扫描 pending 委托并撮合。在同一连接内顺序执行，成交单会更新后续单的可用卖量。
    user_id 若给定，只处理该用户的 pending（持仓/占用仍按该用户维度计算）。
    """
    from data_pipeline.storage.duckdb_manager import ensure_tables

    ensure_tables(conn)

    try:
        rows_pos = conn.execute(
            """
            SELECT user_id, symbol,
                SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'buy'
                    THEN COALESCE(filled_quantity, 0) ELSE 0 END)
              - SUM(CASE WHEN LOWER(CAST(order_type AS VARCHAR)) = 'sell'
                    THEN COALESCE(filled_quantity, 0) ELSE 0 END)
            FROM hongshan_paper_orders
            WHERE LOWER(CAST(status AS VARCHAR)) = 'filled'
            GROUP BY user_id, symbol
            """
        ).fetchall()
    except Exception:
        _log.exception("paper_fill load positions")
        return {"filled": 0, "skipped": 0, "errors": ["aggregate_failed"]}

    pos: dict[tuple[str, str], int] = {}
    for r in rows_pos or []:
        uid, sym, net = r[0], r[1], int(r[2] or 0)
        pos[(str(uid), str(sym))] = net

    try:
        q_pending_sells = """
            SELECT user_id, symbol, COALESCE(order_quantity, 0)
            FROM hongshan_paper_orders
            WHERE LOWER(CAST(status AS VARCHAR)) = 'pending'
              AND LOWER(CAST(order_type AS VARCHAR)) = 'sell'
        """
        ps_args: list[Any] = []
        if user_id:
            q_pending_sells += " AND user_id = ?"
            ps_args.append(str(user_id))
        pend_rows = conn.execute(q_pending_sells, ps_args).fetchall()
    except Exception:
        _log.exception("paper_fill pending sells")
        return {"filled": 0, "skipped": 0, "errors": ["pending_sell_failed"]}

    pend_res: dict[tuple[str, str], int] = defaultdict(int)
    for r in pend_rows or []:
        pend_res[(str(r[0]), str(r[1]))] += int(r[2] or 0)

    try:
        q_po = """
            SELECT id, user_id, symbol, stock_name, order_type, order_style,
                   order_price, order_quantity, order_time
            FROM hongshan_paper_orders
            WHERE LOWER(CAST(status AS VARCHAR)) = 'pending'
            ORDER BY order_time ASC
        """
        po_args: list[Any] = []
        if user_id:
            q_po = q_po.replace("ORDER BY", "AND user_id = ? ORDER BY")
            po_args.append(str(user_id))
        pending_orders = conn.execute(q_po, po_args).fetchall()
    except Exception:
        _log.exception("paper_fill load pending")
        return {"filled": 0, "skipped": 0, "errors": ["pending_load_failed"]}

    filled_n = 0
    skipped_n = 0
    details: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for row in pending_orders or []:
        oid, uid, sym, sname, otype, ostyle, oprice, oqty, _ot = (row + (None,) * 9)[:9]
        uid_s, sym_s = str(uid), str(sym)
        side = str(otype or "").lower().strip()
        qty = int(oqty or 0)
        if qty <= 0:
            skipped_n += 1
            continue

        if side == "sell":
            q_res = pend_res.get((uid_s, sym_s), 0)
            others = q_res - qty
            cur_pos = pos.get((uid_s, sym_s), 0)
            if cur_pos - others < qty:
                skipped_n += 1
                continue

        last, qname = _last_price_and_name(conn, sym_s)
        if last is None:
            skipped_n += 1
            continue

        if not _price_matches(str(ostyle or "limit"), side, float(oprice or 0), last):
            skipped_n += 1
            continue

        try:
            name_update = (qname or "").strip() or None
            if not (sname and str(sname).strip()) and name_update:
                conn.execute(
                    "UPDATE hongshan_paper_orders SET stock_name = ? WHERE id = ?",
                    [name_update, str(oid)],
                )

            ret = conn.execute(
                """
                UPDATE hongshan_paper_orders
                SET status = 'filled',
                    filled_quantity = order_quantity,
                    filled_at = ?
                WHERE id = ? AND LOWER(CAST(status AS VARCHAR)) = 'pending'
                RETURNING id
                """,
                [now, str(oid)],
            ).fetchone()
            if not ret:
                skipped_n += 1
                continue

            if side == "sell":
                proceeds = float(oprice or 0) * qty
                conn.execute(
                    """
                    UPDATE hongshan_accounts
                    SET available_cash = available_cash + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    [proceeds, uid_s],
                )
            elif side == "buy":
                # 下单按限价全额冻结；成交在 last 价，退还 (限价 - 现价) * 量
                op = float(oprice or 0)
                refund = max(0.0, (op - last) * qty)
                if refund > 1e-9:
                    conn.execute(
                        """
                        UPDATE hongshan_accounts
                        SET available_cash = available_cash + ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                        """,
                        [refund, uid_s],
                    )

            if side == "buy":
                pos[(uid_s, sym_s)] = pos.get((uid_s, sym_s), 0) + qty
            else:
                pos[(uid_s, sym_s)] = pos.get((uid_s, sym_s), 0) - qty
                pend_res[(uid_s, sym_s)] = max(0, pend_res.get((uid_s, sym_s), 0) - qty)

            filled_n += 1
            details.append({"id": str(oid), "symbol": sym_s, "side": side, "quantity": qty, "last": last})
        except Exception as e:
            _log.exception("paper_fill order %s", oid)
            details.append({"id": str(oid), "error": str(e)[:120]})

    return {"filled": filled_n, "skipped": skipped_n, "details": details[:50]}
