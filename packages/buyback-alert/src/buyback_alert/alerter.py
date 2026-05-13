"""
alerter.py — Cross-analysis: consecutive drops + buyback events -> alerts.

Takes a list of stocks with consecutive drops (from detector), cross-references
with the buyback_events table for matching stocks that have active buyback/acquisition
announcements during or right after the drop period.

Alert types:
  - '连跌+回购'   (consecutive drop + stock repurchase)
  - '连跌+增持'   (consecutive drop + shareholding increase)
  - '连跌+溢价收购' (consecutive drop + premium acquisition/block trade)

Writes to `alerts` table.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import duckdb
from tqdm import tqdm


def _ensure_alerts_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create alerts table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY,
            alert_type VARCHAR,
            stock_code VARCHAR,
            stock_name VARCHAR,
            trigger_reason VARCHAR,
            consecutive_drop_days INTEGER,
            total_drop_pct DOUBLE,
            related_event_id INTEGER,
            related_event_type VARCHAR,
            details VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _next_alert_id(conn: duckdb.DuckDBPyConnection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM alerts").fetchone()
    return int(row[0]) if row else 1


# Map buyback_events.event_type -> alert_type
_EVENT_TO_ALERT = {
    "回购": "连跌+回购",
    "增持": "连跌+增持",
    "要约收购": "连跌+溢价收购",
    "溢价收购": "连跌+溢价收购",
}


def cross_reference(
    conn: duckdb.DuckDBPyConnection,
    drops: List[Dict[str, Any]],
    *,
    dry_run: bool = False,
    lookahead_days: int = 5,
    lookback_days: int = 30,
) -> List[Dict[str, Any]]:
    """Cross-reference consecutive drop stocks with buyback_events.

    Parameters
    ----------
    conn : DuckDB connection.
    drops : list from detector.detect_consecutive_drops().
    dry_run : if True, print alerts without writing.
    lookahead_days : days after drop end to consider events (default 5).
    lookback_days : days before drop start to consider events (default 30).

    Returns
    -------
    List of alert dicts written (or previewed).
    """
    _ensure_alerts_table(conn)
    alerts_written: List[Dict[str, Any]] = []
    next_pk = _next_alert_id(conn)

    print(f"[alerter] 交叉分析: {len(drops)} 只连跌股票 vs buyback_events 表")
    print(f"          lookback={lookback_days}d, lookahead={lookahead_days}d")

    for drop in tqdm(drops, desc="交叉分析"):
        stock_code = drop["stock_code"]
        stock_name = drop["stock_name"]
        end_date_str = drop["end_date"]
        start_date_str = drop["start_date"]

        # Compute the query window: from start-lookback to end+lookahead
        try:
            end_dt = date.fromisoformat(end_date_str) if isinstance(end_date_str, str) else end_date_str
            start_dt = date.fromisoformat(start_date_str) if isinstance(start_date_str, str) else start_date_str
        except (ValueError, TypeError):
            # Try parsing
            try:
                end_dt = datetime.strptime(str(end_date_str)[:10], "%Y-%m-%d").date()
                start_dt = datetime.strptime(str(start_date_str)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                print(f"  [alerter] 跳过 {stock_code}: 无法解析日期 {end_date_str}")
                continue

        window_start = (start_dt - timedelta(days=lookback_days)).isoformat()
        window_end = (end_dt + timedelta(days=lookahead_days)).isoformat()

        # Query buyback_events for this stock in the window
        events = conn.execute(
            """SELECT id, stock_code, event_type, announcement_date, summary
               FROM buyback_events
               WHERE stock_code=? AND announcement_date >= ? AND announcement_date <= ?
               ORDER BY announcement_date DESC""",
            [stock_code, window_start, window_end],
        ).fetchall()

        if not events:
            continue

        for evt in events:
            evt_id, evt_code, evt_type, ann_date, summary = evt
            ann_date_str = ann_date.isoformat() if hasattr(ann_date, "isoformat") else str(ann_date)[:10]

            alert_type = _EVENT_TO_ALERT.get(str(evt_type))
            if not alert_type:
                continue

            # Build trigger reason
            trigger = (
                f"{stock_name}({stock_code})连跌{drop['consecutive_drop_days']}天"
                f"({drop['total_drop_pct']:.2f}%), "
                f"期间匹配到{evt_type}事件: {summary or ann_date_str}"
            )

            details_json = json.dumps(
                {
                    "drop_start": drop["start_date"],
                    "drop_end": drop["end_date"],
                    "consecutive_drop_days": drop["consecutive_drop_days"],
                    "total_drop_pct": drop["total_drop_pct"],
                    "event_announcement_date": ann_date_str,
                    "event_summary": summary or "",
                    "alert_type": alert_type,
                },
                ensure_ascii=False,
            )

            alert = {
                "id": next_pk,
                "alert_type": alert_type,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "trigger_reason": trigger,
                "consecutive_drop_days": drop["consecutive_drop_days"],
                "total_drop_pct": drop["total_drop_pct"],
                "related_event_id": int(evt_id),
                "related_event_type": str(evt_type),
                "details": details_json,
            }

            if dry_run:
                print(
                    f"  [DRY-RUN] [{alert_type}] {stock_code} {stock_name}: "
                    f"连跌{drop['consecutive_drop_days']}日{drop['total_drop_pct']:.2f}% "
                    f"→ {evt_type}事件(id={evt_id}) on {ann_date_str}"
                )
            else:
                # Check for duplicate
                existing = conn.execute(
                    """SELECT id FROM alerts
                       WHERE stock_code=? AND alert_type=? AND related_event_id=?
                         AND consecutive_drop_days=?""",
                    [stock_code, alert_type, int(evt_id), drop["consecutive_drop_days"]],
                ).fetchone()

                if existing:
                    continue

                conn.execute(
                    """INSERT INTO alerts
                       (id, alert_type, stock_code, stock_name, trigger_reason,
                        consecutive_drop_days, total_drop_pct,
                        related_event_id, related_event_type, details)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        alert["id"],
                        alert["alert_type"],
                        alert["stock_code"],
                        alert["stock_name"],
                        alert["trigger_reason"],
                        alert["consecutive_drop_days"],
                        alert["total_drop_pct"],
                        alert["related_event_id"],
                        alert["related_event_type"],
                        alert["details"],
                    ],
                )
                next_pk += 1

            alerts_written.append(alert)

    if not dry_run:
        conn.commit()

    print(f"[alerter] 完成: 生成 {len(alerts_written)} 条预警")
    return alerts_written
