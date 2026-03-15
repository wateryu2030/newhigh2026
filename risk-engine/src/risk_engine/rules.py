"""
可配置风控规则：从 risk_rules 表加载，在信号执行前评估。
规则类型：single_position_pct_max, max_drawdown_pct, max_exposure_pct。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .drawdown_control import current_drawdown, drawdown_ok
from .exposure_limit import total_exposure_notional


def _get_conn():
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return None
        return get_conn(read_only=True)
    except Exception:
        return None


def load_rules(conn: Any) -> List[Dict[str, Any]]:
    """从 risk_rules 表读取已启用的规则。"""
    try:
        df = conn.execute(
            "SELECT id, rule_type, value, enabled FROM risk_rules WHERE enabled = true ORDER BY id"
        ).fetchdf()
        if df is None or df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        return []


def evaluate(
    positions: List[Dict[str, Any]],
    total_assets: float,
    equity_curve: Optional[List[float]] = None,
    conn: Any = None,
) -> Dict[str, Any]:
    """
    根据 risk_rules 评估当前持仓与资金是否通过风控。
    positions: [{"code": str, "qty": float, "avg_price": float}, ...]
    total_assets: 总资产（现金+持仓市值）
    equity_curve: 可选，资金曲线用于回撤检查
    返回: { "pass": bool, "violations": [{"rule_type": str, "value": float, "message": str}, ...] }
    """
    violations: List[Dict[str, str]] = []
    close_conn = False
    if conn is None:
        conn = _get_conn()
        close_conn = True
    if conn is None:
        return {"pass": True, "violations": []}
    try:
        rules = load_rules(conn)
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    if not rules:
        return {"pass": True, "violations": []}
    pos_notional = sum(float(p.get("qty") or 0) * float(p.get("avg_price") or 0) for p in positions)
    prices = {p.get("code"): float(p.get("avg_price") or 0) for p in positions}
    positions_dict = {p.get("code"): float(p.get("qty") or 0) for p in positions}
    for r in rules:
        rule_type = str(r.get("rule_type") or "")
        value = float(r.get("value") or 0)
        if rule_type == "single_position_pct_max":
            if total_assets <= 0:
                continue
            for code, qty in positions_dict.items():
                notional = qty * prices.get(code, 0)
                pct = notional / total_assets
                if pct > value:
                    violations.append(
                        {
                            "rule_type": rule_type,
                            "value": value,
                            "message": f"single_position_pct {code} {pct:.2%} > {value:.2%}",
                        }
                    )
        elif rule_type == "max_drawdown_pct" and equity_curve:
            if not drawdown_ok(equity_curve, max_drawdown_pct=value):
                dd = current_drawdown(equity_curve)
                violations.append(
                    {
                        "rule_type": rule_type,
                        "value": value,
                        "message": f"current_drawdown {dd:.2%} > {value:.2%}",
                    }
                )
        elif rule_type == "max_exposure_pct" and total_assets > 0:
            exposure_pct = pos_notional / total_assets
            if exposure_pct > value:
                violations.append(
                    {
                        "rule_type": rule_type,
                        "value": value,
                        "message": f"exposure_pct {exposure_pct:.2%} > {value:.2%}",
                    }
                )
    return {"pass": len(violations) == 0, "violations": violations}


def save_rule(
    rule_type: str, value: float, enabled: bool = True, rule_id: Optional[int] = None
) -> bool:
    """写入或更新一条风控规则。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        if rule_id is not None:
            conn.execute(
                "UPDATE risk_rules SET rule_type=?, value=?, enabled=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                [rule_type, value, enabled, rule_id],
            )
        else:
            r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM risk_rules").fetchone()
            nid = int(r[0]) if r else 1
            conn.execute(
                "INSERT INTO risk_rules (id, rule_type, value, enabled, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                [nid, rule_type, value, enabled],
            )
        conn.close()
        return True
    except Exception:
        return False
