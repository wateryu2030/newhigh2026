"""strategy_market 与回测任务错误写入（供 Gateway、Celery worker 共用，避免 duplicated SQL）。"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def upsert_strategy_market_from_backtest(
    strategy_id: str,
    name: str,
    result: Dict[str, Any],
) -> bool:
    """与 gateway._save_backtest_to_strategy_market 相同契约。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        tr = result.get("total_return")
        return_pct = float(tr * 100) if tr is not None else None
        sharpe = result.get("sharpe_ratio")
        max_dd = result.get("max_drawdown")
        conn.execute(
            """
            INSERT INTO strategy_market (strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            ON CONFLICT (strategy_id) DO UPDATE SET
            name=EXCLUDED.name, return_pct=EXCLUDED.return_pct, sharpe_ratio=EXCLUDED.sharpe_ratio,
            max_drawdown=EXCLUDED.max_drawdown, status=EXCLUDED.status, updated_at=CURRENT_TIMESTAMP
            """,
            [
                strategy_id,
                name or strategy_id.replace("_", " ").title(),
                return_pct,
                sharpe,
                max_dd,
            ],
        )
        conn.close()
        return True
    except Exception:
        return False


def log_backtest_task_error(
    task_name: str,
    payload_json: str,
    error_message: str,
    strategy_id: Optional[str] = None,
) -> None:
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM backtest_task_errors").fetchone()
        nid = int(r[0]) if r else 1
        conn.execute(
            """
            INSERT INTO backtest_task_errors (id, task_name, strategy_id, payload_json, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [nid, task_name[:200], (strategy_id or "")[:128], payload_json[:8000], error_message[:4000]],
        )
        conn.close()
    except Exception:
        pass


def record_pipeline_meta(key: str, value: Any) -> None:
    """写入 pipeline_meta（k/v JSON 字符串）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        conn.execute(
            """
            INSERT INTO pipeline_meta (k, v, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = CURRENT_TIMESTAMP
            """,
            [key[:200], s[:65000]],
        )
        conn.close()
    except Exception:
        pass
