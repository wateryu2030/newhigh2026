"""
每日亏损限额控制：当日累计亏损超过阈值则停止交易。
从 sim_account_snapshots 读取当日资金变化。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

_log = logging.getLogger(__name__)


def _get_conn():
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return None
        return get_conn(read_only=True)
    except Exception:
        return None


def daily_pnl(conn: Any = None) -> Optional[float]:
    """
    计算当日盈亏 = 当前总资产 - 今日首笔快照的总资产（或前一天最后一笔）。
    若无法计算返回 None。
    """
    close_conn = conn is None
    if conn is None:
        conn = _get_conn()
    if conn is None:
        return None

    try:
        # 今日 UTC 零点
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # 当前总资产
        row = conn.execute(
            "SELECT total_assets FROM sim_account_snapshots ORDER BY snapshot_time DESC LIMIT 1"
        ).fetchone()
        current = float(row[0]) if row and row[0] is not None else None

        # 今日首笔快照
        row = conn.execute(
            """
            SELECT total_assets FROM sim_account_snapshots
            WHERE snapshot_time >= ?
            ORDER BY snapshot_time ASC LIMIT 1
        """,
            [today_start.isoformat().replace("+00:00", "Z")],
        ).fetchone()
        if row and row[0] is not None:
            start_val = float(row[0])
        else:
            # 取今日之前最后一笔
            row = conn.execute(
                """
                SELECT total_assets FROM sim_account_snapshots
                WHERE snapshot_time < ?
                ORDER BY snapshot_time DESC LIMIT 1
            """,
                [today_start.isoformat().replace("+00:00", "Z")],
            ).fetchone()
            start_val = float(row[0]) if row and row[0] is not None else None

        if current is None or start_val is None:
            return None
        return current - start_val
    except Exception:
        _log.exception("Failed to compute daily PnL")
        return None
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def daily_loss_ok(
    max_daily_loss_pct: float = 0.02,
    conn: Any = None,
) -> bool:
    """
    检查当日亏损是否在限额内。
    max_daily_loss_pct: 日亏损上限占初始资金的比例（默认 2%）。
    """
    pnl = daily_pnl(conn=conn)
    if pnl is None or pnl >= 0:
        return True

    # 获取初始资金用于计算百分比
    close_conn = conn is None
    if conn is None:
        conn = _get_conn()
    if conn is None:
        return True

    try:
        row = conn.execute(
            "SELECT cash FROM sim_account_snapshots ORDER BY snapshot_time ASC LIMIT 1"
        ).fetchone()
        initial = float(row[0]) if row and row[0] else 1_000_000.0
        loss_pct = abs(pnl) / initial if initial > 0 else 0
        ok = loss_pct <= max_daily_loss_pct
        if not ok:
            _log.warning(
                "Daily loss limit breached: PnL=%.2f loss_pct=%.4f > limit=%.4f",
                pnl,
                loss_pct,
                max_daily_loss_pct,
            )
        return ok
    except Exception:
        _log.exception("Failed to check daily loss limit")
        return True
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def should_disable_strategy_daily_loss(
    max_daily_loss_pct: float = 0.02,
    conn: Any = None,
) -> bool:
    """当日亏损超限则建议停止策略。"""
    return not daily_loss_ok(max_daily_loss_pct, conn=conn)
