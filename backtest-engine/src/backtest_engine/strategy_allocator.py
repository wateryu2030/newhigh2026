"""
策略资金分配：输入策略 ID 列表与可选权重，输出 (strategy_id, weight) 列表。
等权时 weight_i = 1/n；否则按传入 weights 归一化。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def allocate_weights(
    strategy_ids: List[str],
    weights: Optional[List[float]] = None,
) -> List[Tuple[str, float]]:
    """
    分配各策略权重。
    strategy_ids: 策略 ID 列表（与 strategy_market 或 trade_signals 对应）。
    weights: 可选，与 strategy_ids 等长；若为 None 则等权。
    返回 [(strategy_id, weight), ...]，weight 和为 1.0。
    """
    if not strategy_ids:
        return []
    n = len(strategy_ids)
    if weights is not None and len(weights) == n:
        total = sum(w for w in weights if w is not None)
        if total and total > 0:
            return [(sid, (w or 0) / total) for sid, w in zip(strategy_ids, weights)]
    # 等权
    w = 1.0 / n
    return [(sid, w) for sid in strategy_ids]


def get_symbols_for_strategy(strategy_id: str, conn: Any = None) -> List[str]:
    """
    从 trade_signals 表查询该策略有信号的标的列表（去重）。
    """
    close_conn = False
    if conn is None:
        try:
            from data_pipeline.storage.duckdb_manager import get_conn
            conn = get_conn(read_only=True)
            close_conn = True
        except Exception:
            return []
    try:
        df = conn.execute(
            "SELECT DISTINCT code FROM trade_signals WHERE strategy_id = ? ORDER BY code",
            [str(strategy_id)],
        ).fetchdf()
        if df is None or df.empty:
            if close_conn and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            return []
        out = [str(row["code"]).strip() for _, row in df.iterrows() if row.get("code")]
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        return out
    except Exception:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        return []
