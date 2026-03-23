# Load/save strategy population from strategy_market
from __future__ import annotations

import os
from typing import List

from .gene import StrategyGene


def _get_conn():
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path  # pylint: disable=import-outside-toplevel

        if not os.path.isfile(get_db_path()):
            return None
        return get_conn(read_only=False)
    except (ImportError, ModuleNotFoundError, OSError):
        return None


def load_population_from_market(limit: int = 20) -> List[StrategyGene]:
    conn = _get_conn()
    if conn is None:
        return []
    try:
        df = conn.execute(
            "SELECT strategy_id, name FROM strategy_market ORDER BY updated_at DESC LIMIT ?",
            [limit],
        ).fetchdf()
        if df is None or df.empty:
            return []
        genes = []
        for _, row in df.iterrows():
            sid = str(row.get("strategy_id") or "")
            if sid:
                genes.append(
                    StrategyGene(
                        rule_tree={}, params={"name": str(row.get("name") or sid)}, strategy_id=sid
                    )
                )
        return genes
    except (ValueError, TypeError, AttributeError):
        return []
    finally:
        if conn:
            try:
                conn.close()
            except (ValueError, TypeError, OSError):
                pass


def save_gene_to_market(
    gene: StrategyGene,
    name: str = "",
    return_pct: float = None,
    sharpe_ratio: float = None,
    max_drawdown: float = None,
    status: str = "active",
) -> bool:
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables  # pylint: disable=import-outside-toplevel

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        sid = gene.strategy_id or "openclaw_1"
        name = name or gene.params.get("name") or sid
        conn.execute(
            """
            INSERT INTO strategy_market (strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (strategy_id) DO UPDATE SET
            name=EXCLUDED.name, return_pct=EXCLUDED.return_pct, sharpe_ratio=EXCLUDED.sharpe_ratio,
            max_drawdown=EXCLUDED.max_drawdown, status=EXCLUDED.status, updated_at=CURRENT_TIMESTAMP
        """,
            [sid, name, return_pct, sharpe_ratio, max_drawdown, status],
        )
        conn.close()
        return True
    except (ImportError, ModuleNotFoundError, ValueError, TypeError, OSError):
        return False
