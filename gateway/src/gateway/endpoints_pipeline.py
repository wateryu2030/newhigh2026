"""
对外开放策略流水线：已登录用户提交 → operator/admin 审批 → 写入 strategy_market。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Header, HTTPException
from pydantic import BaseModel, Field

from .auth.jwt_auth import is_admin, resolve_effective_role, verify_token
from .response_utils import json_fail, json_ok

_log = logging.getLogger(__name__)

MAX_STAGED = 50


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _ensure_paths():
    root = _repo_root()
    if root not in __import__("sys").path:
        __import__("sys").path.insert(0, root)
    for d in ("data-pipeline/src", "backtest-engine/src", "core/src", "openclaw_engine"):
        p = os.path.join(root, d)
        if os.path.isdir(p) and p not in __import__("sys").path:
            __import__("sys").path.insert(0, p)


def _get_conn():
    _ensure_paths()
    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

    if not os.path.isfile(get_db_path()):
        return None
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    return conn


def _auth_payload(authorization: Optional[str]) -> dict:
    if not authorization or "Bearer " not in authorization:
        raise HTTPException(status_code=401, detail="需要登录后提交策略流水线")
    payload = verify_token(authorization.replace("Bearer ", "").strip())
    if not payload:
        raise HTTPException(status_code=401, detail="无效或过期的 token")
    return payload


def _check_approve_key(x_pipeline_approve_key: Optional[str]) -> None:
    expected = os.environ.get("PIPELINE_APPROVE_API_KEY", "").strip()
    if not expected:
        return
    if (x_pipeline_approve_key or "").strip() != expected:
        raise HTTPException(status_code=403, detail="审批密钥无效或未提供 X-Pipeline-Approve-Key")


class EvolutionParams(BaseModel):
    population_limit: int = Field(10, ge=2, le=200)
    symbol: str = "000001.SZ"
    offspring_size: int = Field(4, ge=1, le=50)
    mutation_rate: float = Field(0.1, ge=0, le=1)
    elite_size: int = Field(2, ge=1, le=20)


class BacktestSpec(BaseModel):
    strategy_id: str = Field(..., min_length=1, max_length=128)
    name: Optional[str] = None
    symbol: str = "000001.SZ"
    start_date: str = ""
    end_date: str = ""
    signal_source: str = "trade_signals"
    strategy_id_filter: Optional[str] = None
    init_cash: float = Field(10000.0, gt=0)
    fees: float = Field(0.001, ge=0, le=0.2)
    slippage: float = Field(0.0, ge=0, le=0.2)


class GateParams(BaseModel):
    min_sharpe: Optional[float] = None
    max_drawdown_abs: Optional[float] = None


class BacktestBlock(BaseModel):
    specs: List[BacktestSpec] = Field(default_factory=list)


class PipelineRunBody(BaseModel):
    request_id: Optional[str] = Field(None, max_length=128)
    mode: Literal["evolve_then_backtest", "backtest_only", "evolve_only"]
    evolution: Optional[EvolutionParams] = None
    backtest: Optional[BacktestBlock] = None
    gates: Optional[GateParams] = None


class ApprovePipelineBody(BaseModel):
    """仅 admin 上架；可选仅批准部分 strategy_id（须在本次 staged 列表内）。"""

    strategy_ids: Optional[List[str]] = Field(
        None,
        description="若为空则上架全部候选；否则仅上架交集",
    )


def _passes_gates(c: Dict[str, Any], gates: Optional[GateParams]) -> bool:
    if not gates:
        return True
    if gates.min_sharpe is not None:
        sr = c.get("sharpe_ratio")
        try:
            if sr is None or float(sr) < float(gates.min_sharpe):
                return False
        except (TypeError, ValueError):
            return False
    if gates.max_drawdown_abs is not None:
        md = c.get("max_drawdown")
        try:
            if md is not None and abs(float(md)) > float(gates.max_drawdown_abs):
                return False
        except (TypeError, ValueError):
            return False
    return True


def _candidate_from_backtest(name: Optional[str], strategy_id: str, out: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if out.get("error"):
        return None
    tr = out.get("total_return")
    return {
        "strategy_id": strategy_id,
        "name": (name or strategy_id)[:256],
        "return_pct": float(tr * 100) if tr is not None else None,
        "sharpe_ratio": out.get("sharpe_ratio"),
        "max_drawdown": out.get("max_drawdown"),
        "status": "pending_publish",
        "source": "backtest",
    }


def _merge_staged(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for c in raw[: MAX_STAGED * 2]:
        sid = c.get("strategy_id")
        if sid:
            merged[str(sid)] = c
    return list(merged.values())[:MAX_STAGED]


def _run_pipeline_job(job_id: str) -> None:
    _ensure_paths()
    conn = _get_conn()
    if not conn:
        return
    try:
        row = conn.execute(
            "SELECT payload_json FROM pipeline_jobs WHERE job_id = ?", [job_id]
        ).fetchone()
        if not row:
            conn.close()
            return
        payload = json.loads(row[0])
        mode = payload.get("mode")
        gates_dict = payload.get("gates") or {}
        gates = GateParams(**gates_dict) if gates_dict else None

        result_parts: Dict[str, Any] = {}
        all_staged: List[Dict[str, Any]] = []

        if mode in ("evolve_then_backtest", "evolve_only"):
            from openclaw_engine.evolution_orchestrator import run_evolution_cycle

            evp = payload.get("evolution") or {}
            ep = EvolutionParams(**{k: v for k, v in evp.items() if k in EvolutionParams.model_fields})
            r = run_evolution_cycle(
                population_limit=ep.population_limit,
                elite_size=ep.elite_size,
                offspring_size=ep.offspring_size,
                mutation_rate=ep.mutation_rate,
                symbol=ep.symbol,
                persist_to_market=False,
            )
            result_parts["evolution"] = r
            for s in r.get("staged") or []:
                if isinstance(s, dict) and _passes_gates(s, gates):
                    all_staged.append(s)

        if mode in ("evolve_then_backtest", "backtest_only"):
            from backtest_engine.run_with_db import run_backtest_from_db

            bt = payload.get("backtest") or {}
            specs = bt.get("specs") or []
            for sp in specs:
                try:
                    b = BacktestSpec(**sp)
                except Exception as e:
                    result_parts.setdefault("backtest_errors", []).append(str(e)[:200])
                    continue
                out = run_backtest_from_db(
                    symbol=b.symbol,
                    start_date=b.start_date,
                    end_date=b.end_date,
                    signal_source=b.signal_source,
                    strategy_id=b.strategy_id_filter,
                    init_cash=b.init_cash,
                    fees=b.fees,
                    slippage=b.slippage,
                )
                c = _candidate_from_backtest(b.name, b.strategy_id, out)
                if c and _passes_gates(c, gates):
                    all_staged.append(c)

        final_staged = _merge_staged(all_staged)
        status = "awaiting_approval" if final_staged else "completed"
        now = datetime.now(timezone.utc).isoformat()
        result_parts["completed_at"] = now
        result_parts["staged_count"] = len(final_staged)

        conn.execute(
            """
            UPDATE pipeline_jobs
            SET status = ?, result_json = ?, staged_candidates_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
            """,
            [status, json.dumps(result_parts, ensure_ascii=False, default=str), json.dumps(final_staged, ensure_ascii=False), job_id],
        )
        conn.close()
    except Exception as e:
        _log.exception("pipeline job %s failed", job_id)
        try:
            conn.execute(
                """
                UPDATE pipeline_jobs
                SET status = 'failed', result_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                [json.dumps({"error": str(e)[:500]}, ensure_ascii=False), job_id],
            )
            conn.close()
        except Exception:
            pass


def build_pipeline_router() -> APIRouter:
    r = APIRouter(prefix="/strategies/pipeline", tags=["strategy-pipeline"])

    @r.post("/run")
    def post_pipeline_run(body: PipelineRunBody, authorization: Optional[str] = Header(default=None)) -> dict:
        payload = _auth_payload(authorization)
        owner = str(payload.get("sub") or "unknown")
        if body.mode in ("evolve_then_backtest", "evolve_only") and not body.evolution:
            body.evolution = EvolutionParams()
        if body.mode in ("evolve_then_backtest", "backtest_only"):
            if not body.backtest or not getattr(body.backtest, "specs", None):
                raise HTTPException(status_code=400, detail="backtest.specs 不能为空")
        if body.mode == "backtest_only" and not body.backtest:
            raise HTTPException(status_code=400, detail="缺少 backtest")

        conn = _get_conn()
        if not conn:
            return json_fail("数据库不可用", status_code=503)
        try:
            if body.request_id:
                ex = conn.execute(
                    "SELECT job_id, status FROM pipeline_jobs WHERE owner_sub = ? AND client_request_id = ?",
                    [owner, body.request_id[:128]],
                ).fetchone()
                if ex:
                    return json_ok(
                        {"job_id": ex[0], "status": ex[1], "deduplicated": True},
                        source="pipeline",
                    )
            job_id = str(uuid.uuid4())
            payload_json = body.model_dump()
            payload_json["owner_sub"] = owner
            crid = (body.request_id or "")[:128] or None
            conn.execute(
                """
                INSERT INTO pipeline_jobs (job_id, owner_sub, client_request_id, mode, status, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'running', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                [job_id, owner, crid, body.mode, json.dumps(payload_json, ensure_ascii=False, default=str)],
            )
            conn.close()
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            return json_fail(str(e)[:200], status_code=500)

        t = threading.Thread(target=_run_pipeline_job, args=(job_id,), daemon=True)
        t.start()
        return json_ok({"job_id": job_id, "status": "running"}, source="pipeline")

    @r.get("/jobs")
    def list_pipeline_jobs(
        limit: int = 20,
        authorization: Optional[str] = Header(default=None),
    ) -> dict:
        pl = _auth_payload(authorization)
        owner = str(pl.get("sub") or "")
        role = resolve_effective_role(pl)
        lim = max(1, min(limit, 100))
        conn = _get_conn()
        if not conn:
            return json_ok({"items": []}, source="none")
        try:
            if is_admin(role):
                df = conn.execute(
                    """
                    SELECT job_id, owner_sub, mode, status, created_at, updated_at, client_request_id
                    FROM pipeline_jobs ORDER BY updated_at DESC LIMIT ?
                    """,
                    [lim],
                ).fetchdf()
            else:
                df = conn.execute(
                    """
                    SELECT job_id, owner_sub, mode, status, created_at, updated_at, client_request_id
                    FROM pipeline_jobs WHERE owner_sub = ? ORDER BY updated_at DESC LIMIT ?
                    """,
                    [owner, lim],
                ).fetchdf()
            conn.close()
            if df is None or df.empty:
                return json_ok({"items": []}, source="duckdb")
            return json_ok({"items": df.to_dict(orient="records")}, source="duckdb")
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            return json_fail(str(e)[:200], status_code=500)

    @r.get("/jobs/{job_id}")
    def get_pipeline_job(job_id: str, authorization: Optional[str] = Header(default=None)) -> dict:
        pl = _auth_payload(authorization)
        owner = str(pl.get("sub") or "")
        role = resolve_effective_role(pl)
        conn = _get_conn()
        if not conn:
            return json_fail("数据库不可用", status_code=503)
        try:
            row = conn.execute(
                """
                SELECT job_id, owner_sub, mode, status, result_json, staged_candidates_json,
                       approved_by, approved_at, rejected_by, reject_reason, created_at, updated_at, client_request_id
                FROM pipeline_jobs WHERE job_id = ?
                """,
                [job_id],
            ).fetchone()
            conn.close()
            if not row:
                raise HTTPException(status_code=404, detail="job 不存在")
            jid, osub = row[0], row[1]
            if osub != owner and not is_admin(role):
                raise HTTPException(status_code=403, detail="无权查看此任务")
            parsed: Dict[str, Any] = {
                "job_id": jid,
                "owner_sub": osub,
                "mode": row[2],
                "status": row[3],
                "created_at": str(row[10]) if row[10] else None,
                "updated_at": str(row[11]) if row[11] else None,
                "client_request_id": row[12],
                "approved_by": row[6],
                "approved_at": str(row[7]) if row[7] else None,
                "rejected_by": row[8],
                "reject_reason": row[9],
            }
            try:
                parsed["result"] = json.loads(row[4]) if row[4] else None
            except Exception:
                parsed["result"] = None
            try:
                parsed["staged_candidates"] = json.loads(row[5]) if row[5] else []
            except Exception:
                parsed["staged_candidates"] = []
            return json_ok(parsed, source="pipeline")
        except HTTPException:
            raise
        except Exception as e:
            return json_fail(str(e)[:200], status_code=500)

    @r.post("/jobs/{job_id}/approve")
    def approve_pipeline_job(
        job_id: str,
        body: ApprovePipelineBody = Body(default_factory=ApprovePipelineBody),
        authorization: Optional[str] = Header(default=None),
        x_pipeline_approve_key: Optional[str] = Header(default=None, alias="X-Pipeline-Approve-Key"),
    ) -> dict:
        pl = _auth_payload(authorization)
        role = resolve_effective_role(pl)
        if not is_admin(role):
            raise HTTPException(
                status_code=403,
                detail="策略上架仅 admin 可操作（见 hongshan_users.role 或 PIPELINE_ADMIN_SUBJECTS）",
            )
        _check_approve_key(x_pipeline_approve_key)

        approver = str(pl.get("sub") or "")
        conn = _get_conn()
        if not conn:
            return json_fail("数据库不可用", status_code=503)
        promoted = 0
        try:
            row = conn.execute(
                "SELECT status, staged_candidates_json, owner_sub, result_json FROM pipeline_jobs WHERE job_id = ?",
                [job_id],
            ).fetchone()
            if not row:
                conn.close()
                raise HTTPException(status_code=404, detail="job 不存在")
            st, staged_raw, _own, prev_result = row[0], row[1], row[2], row[3]
            if st != "awaiting_approval":
                conn.close()
                return json_fail(f"当前状态不可审批: {st}", status_code=400)
            try:
                staged = json.loads(staged_raw) if staged_raw else []
            except Exception:
                staged = []
            if not staged:
                conn.close()
                return json_fail("无可上架候选", status_code=400)

            allow_ids: Optional[set] = None
            if body.strategy_ids:
                allow_ids = {str(x).strip() for x in body.strategy_ids if str(x).strip()}
                staged = [c for c in staged if isinstance(c, dict) and str(c.get("strategy_id")) in allow_ids]
                if not staged:
                    conn.close()
                    return json_fail("staged 与 strategy_ids 无交集", status_code=400)

            from data_pipeline.strategy_market_writer import upsert_strategy_market_from_backtest

            for c in staged:
                if not isinstance(c, dict):
                    continue
                sid = c.get("strategy_id")
                if not sid:
                    continue
                rp = c.get("return_pct")
                fake_result = {
                    "total_return": (float(rp) / 100.0) if rp is not None else None,
                    "sharpe_ratio": c.get("sharpe_ratio"),
                    "max_drawdown": c.get("max_drawdown"),
                }
                name = str(c.get("name") or sid)
                if upsert_strategy_market_from_backtest(str(sid), name, fake_result):
                    promoted += 1

            extra = {"promoted": promoted, "approved_at": datetime.now(timezone.utc).isoformat()}
            try:
                prev = json.loads(prev_result) if prev_result else {}
            except Exception:
                prev = {}
            if isinstance(prev, dict):
                prev.update(extra)
                merged_result = prev
            else:
                merged_result = extra

            conn.execute(
                """
                UPDATE pipeline_jobs
                SET status = 'completed', approved_by = ?, approved_at = CURRENT_TIMESTAMP,
                    result_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                [approver, json.dumps(merged_result, ensure_ascii=False, default=str), job_id],
            )
            conn.close()
        except HTTPException:
            raise
        except Exception as e:
            _log.exception("approve pipeline")
            try:
                conn.close()
            except Exception:
                pass
            return json_fail(str(e)[:200], status_code=500)
        return json_ok({"job_id": job_id, "promoted": promoted, "status": "completed"}, source="pipeline")

    @r.post("/jobs/{job_id}/reject")
    def reject_pipeline_job(
        job_id: str,
        reason: str = "",
        authorization: Optional[str] = Header(default=None),
    ) -> dict:
        pl = _auth_payload(authorization)
        owner = str(pl.get("sub") or "")
        role = resolve_effective_role(pl)
        conn = _get_conn()
        if not conn:
            return json_fail("数据库不可用", status_code=503)
        try:
            row = conn.execute(
                "SELECT status, owner_sub FROM pipeline_jobs WHERE job_id = ?",
                [job_id],
            ).fetchone()
            if not row:
                conn.close()
                raise HTTPException(status_code=404, detail="job 不存在")
            st, osub = row[0], row[1]
            if st != "awaiting_approval":
                conn.close()
                return json_fail(f"当前状态不可拒绝: {st}", status_code=400)
            if osub != owner and not is_admin(role):
                conn.close()
                raise HTTPException(status_code=403, detail="仅任务提交人或 admin 可拒绝")
            by = owner if osub == owner else str(pl.get("sub"))
            conn.execute(
                """
                UPDATE pipeline_jobs
                SET status = 'rejected', rejected_by = ?, reject_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                [by, (reason or "rejected")[:500], job_id],
            )
            conn.close()
        except HTTPException:
            raise
        except Exception as e:
            return json_fail(str(e)[:200], status_code=500)
        return json_ok({"job_id": job_id, "status": "rejected"}, source="pipeline")

    return r
