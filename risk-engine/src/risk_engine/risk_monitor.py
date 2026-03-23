"""
风控监控：定时或按请求评估当前持仓与资金曲线，返回 violations 与建议动作。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_conn():
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return None
        return get_conn(read_only=False)
    except Exception:
        return None


def evaluate_current(
    positions: Optional[List[Dict[str, Any]]] = None,
    total_assets: Optional[float] = None,
    equity_curve: Optional[List[float]] = None,
    conn: Any = None,
) -> Dict[str, Any]:
    """
    评估当前状态是否满足风控规则。
    positions: 若为 None 则从 sim_positions 读取。
    total_assets: 若为 None 则从最新 sim_account_snapshots 读取。
    equity_curve: 可选，用于回撤类规则。
    返回: { "pass": bool, "violations": [...], "recommended_actions": ["reject_order"|"reduce_position"|"alert", ...] }
    """
    from .rules import evaluate

    close_conn = conn is None
    if conn is None:
        conn = _get_conn()
    if conn is None:
        return {"pass": True, "violations": [], "recommended_actions": []}

    if positions is None or total_assets is None:
        try:
            if positions is None:
                df = conn.execute("SELECT code, side, qty, avg_price FROM sim_positions").fetchdf()
                positions = []
                if df is not None and not df.empty:
                    for _, r in df.iterrows():
                        positions.append(
                            {
                                "code": r.get("code"),
                                "qty": r.get("qty"),
                                "avg_price": r.get("avg_price") or 0,
                            }
                        )
            if total_assets is None:
                row = conn.execute(
                    "SELECT total_assets FROM sim_account_snapshots ORDER BY snapshot_time DESC LIMIT 1"
                ).fetchone()
                total_assets = float(row[0]) if row and row[0] is not None else 0.0
        except Exception:
            positions = positions or []
            total_assets = total_assets or 0.0

    res = evaluate(
        positions=positions, total_assets=total_assets, equity_curve=equity_curve, conn=conn
    )
    violations = res.get("violations") or []
    recommended = []
    for v in violations:
        rule_type = (v.get("rule_type") or "").lower()
        if "position" in rule_type or "single" in rule_type:
            recommended.append("reduce_position")
        elif "drawdown" in rule_type or "loss" in rule_type:
            recommended.append("reduce_position")
            recommended.append("alert")
        else:
            recommended.append("alert")
    if violations:
        recommended.append("reject_order")
    if close_conn and conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    return {
        "pass": res.get("pass", True),
        "violations": violations,
        "recommended_actions": list(dict.fromkeys(recommended)),
    }
