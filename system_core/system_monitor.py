"""
系统监控：汇总 data_status、scanner_status、ai_status、strategy_status，写入 system_status 表。
"""

from __future__ import annotations

from typing import Dict, Any, Optional


def collect_status(
    data_result: Optional[Dict[str, Any]] = None,
    scan_result: Optional[Dict[str, Any]] = None,
    ai_result: Optional[Dict[str, Any]] = None,
    strategy_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """将各编排器结果转为简短状态字符串。"""

    def _summarize(name: str, r: Optional[Dict[str, Any]]) -> str:
        if r is None:
            return "not_run"
        err = r.get("errors") or []
        if err:
            return f"error:{len(err)}"
        if name == "data":
            n = (r.get("stock_list") or 0) + (r.get("limitup") or 0) + (r.get("longhubang") or 0)
            return f"ok:n={n}"
        if name == "scan":
            n = (r.get("limit_up") or 0) + (r.get("sniper") or 0)
            return f"ok:n={n}"
        if name == "ai":
            return f"ok:emotion={r.get('emotion')},hotmoney={r.get('hotmoney')},sector={r.get('sector')}"
        if name == "strategy":
            n = (r.get("fusion") or 0) + (r.get("fallback") or 0)
            return f"ok:signals={n}"
        return "ok"

    return {
        "data_status": _summarize("data", data_result),
        "scanner_status": _summarize("scan", scan_result),
        "ai_status": _summarize("ai", ai_result),
        "strategy_status": _summarize("strategy", strategy_result),
    }


def write_status(
    data_status: str,
    scanner_status: str,
    ai_status: str,
    strategy_status: str,
) -> None:
    """写入 system_status 表；同步写入 OpenClaw 进化任务与 Skill 统计（若表有对应列）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

        conn = get_conn(read_only=False)
        ensure_tables(conn)
        # 尝试读取最新进化任务与 Skill 统计（供 OpenClaw 前端展示）
        ev_task_id, ev_status, ev_result = None, None, None
        skill_count, skill_time = 0, None
        try:
            r = conn.execute(
                "SELECT task_id, status, result FROM evolution_tasks ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if r:
                ev_task_id, ev_status, ev_result = r[0], r[1], r[2]
        except Exception:
            pass
        try:
            r = conn.execute(
                "SELECT call_count, last_call_time FROM skill_stats LIMIT 1"
            ).fetchone()
            if r:
                skill_count, skill_time = int(r[0] or 0), r[1]
        except Exception:
            pass
        try:
            conn.execute(
                """INSERT INTO system_status (
                    data_status, scanner_status, ai_status, strategy_status,
                    evolution_task_id, evolution_status, evolution_result,
                    skill_call_count, skill_last_call_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    data_status,
                    scanner_status,
                    ai_status,
                    strategy_status,
                    ev_task_id,
                    ev_status,
                    ev_result,
                    skill_count,
                    skill_time,
                ],
            )
        except Exception:
            conn.execute(
                """INSERT INTO system_status (data_status, scanner_status, ai_status, strategy_status)
                   VALUES (?, ?, ?, ?)""",
                [data_status, scanner_status, ai_status, strategy_status],
            )
        conn.close()
    except Exception:
        pass


def record(
    data_result: Optional[Dict[str, Any]] = None,
    scan_result: Optional[Dict[str, Any]] = None,
    ai_result: Optional[Dict[str, Any]] = None,
    strategy_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """汇总状态并写入数据库，返回状态 dict。"""
    status = collect_status(data_result, scan_result, ai_result, strategy_result)
    write_status(
        status["data_status"],
        status["scanner_status"],
        status["ai_status"],
        status["strategy_status"],
    )
    return status
