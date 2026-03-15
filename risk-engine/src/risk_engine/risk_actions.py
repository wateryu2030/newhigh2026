"""
风控动作：根据违规类型执行 reject_order、reduce_position、alert。
与 execution_engine 联动（拒绝下单、触发减仓）；alert 可写审计或发告警。
"""

from __future__ import annotations

from typing import Any, Dict, List


def execute_action(
    violation: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    对单条违规执行建议动作。
    violation: { "rule_type": str, "value": float, "message": str }
    context: { "order_id": int?, "positions": list?, "dry_run": bool? }
    返回: { "action": "reject_order"|"reduce_position"|"alert"|"none", "done": bool, "message": str }
    """
    rule_type = (violation.get("rule_type") or "").lower()
    dry_run = context.get("dry_run", True)

    if "single" in rule_type or "position" in rule_type:
        if dry_run:
            return {
                "action": "reduce_position",
                "done": False,
                "message": "dry_run: would reduce position",
            }
        # 实际减仓需调用 execution_engine 的平仓接口，此处仅返回建议
        return {
            "action": "reduce_position",
            "done": False,
            "message": "trigger reduce_position via execution",
        }

    if "drawdown" in rule_type or "loss" in rule_type:
        _emit_alert(violation, context)
        return {"action": "alert", "done": True, "message": "alert emitted"}

    if context.get("order_id") is not None:
        if dry_run:
            return {
                "action": "reject_order",
                "done": False,
                "message": "dry_run: would reject order",
            }
        return {
            "action": "reject_order",
            "done": True,
            "message": "order should be rejected by caller",
        }

    _emit_alert(violation, context)
    return {"action": "alert", "done": True, "message": "alert emitted"}


def _emit_alert(violation: Dict[str, Any], context: Dict[str, Any]) -> None:
    """写审计日志或发告警（占位：可接 Prometheus/Webhook）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path, ensure_tables
        import os

        if not os.path.isfile(get_db_path()):
            return
        conn = get_conn(read_only=False)
        ensure_tables(conn)
        conn.execute(
            """INSERT INTO audit_log (id, method, path, client_host, created_at)
               SELECT COALESCE(MAX(id), 0) + 1, 'RISK_ALERT', ?, ?, CURRENT_TIMESTAMP FROM audit_log
            """,
            [violation.get("message", ""), context.get("client_host", "")],
        )
        conn.close()
    except Exception:
        pass


def apply_risk_actions(
    violations: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """对多条违规依次执行动作，返回每条的执行结果。"""
    return [execute_action(v, context) for v in violations]
