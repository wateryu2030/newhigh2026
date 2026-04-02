"""Celery：异步回测单策略并写入 strategy_market；失败写入 backtest_task_errors。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:
    from system_core.celery_app import app
except (ImportError, RuntimeError, OSError):
    app = None


def _run_backtest_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for d in ("backtest-engine/src", "data-pipeline/src", "core/src"):
        p = os.path.join(root, d)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)

    from backtest_engine.run_with_db import run_backtest_from_db

    symbol = str(payload.get("symbol") or "000001.SZ")
    start_date = str(payload.get("start_date") or "")
    end_date = str(payload.get("end_date") or "")
    strategy_id = str(payload.get("strategy_id") or "celery_backtest")
    name = str(payload.get("name") or strategy_id)
    signal_source = str(payload.get("signal_source") or "trade_signals")
    sig_filter = payload.get("strategy_id_filter")
    init_cash = float(payload.get("init_cash") or 10000.0)
    slippage = float(payload.get("slippage") or 0.0)
    fees = float(payload.get("fees") or 0.001)
    persist = payload.get("persist", True)

    out = run_backtest_from_db(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        signal_source=signal_source,
        strategy_id=sig_filter if sig_filter else None,
        init_cash=init_cash,
        fees=fees,
        slippage=slippage,
    )
    out["strategy_id"] = strategy_id
    if out.get("error"):
        return out
    if persist:
        from data_pipeline.strategy_market_writer import upsert_strategy_market_from_backtest

        upsert_strategy_market_from_backtest(strategy_id, name, out)
    return out


if app is not None:

    @app.task(
        bind=True,
        name="system_core.tasks.backtest_tasks.run_strategy_backtest_task",
        autoretry_for=(OSError, RuntimeError),
        retry_backoff=True,
        retry_kwargs={"max_retries": 3},
    )
    def run_strategy_backtest_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return _run_backtest_sync(payload)
        except Exception as e:
            try:
                from data_pipeline.strategy_market_writer import log_backtest_task_error

                log_backtest_task_error(
                    "run_strategy_backtest_task",
                    json.dumps(payload, ensure_ascii=False, default=str)[:8000],
                    str(e)[:2000],
                    strategy_id=str(payload.get("strategy_id") or ""),
                )
            except Exception:
                pass
            raise

    @app.task(name="system_core.tasks.backtest_tasks.run_parallel_backtests_group")
    def run_parallel_backtests_group_task(specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        多策略回测：默认 CELERY_BACKTEST_USE_PARALLEL_GROUP=1 时用 Celery group 并行；
        失败或非并行时回退为当前进程顺序执行。
        """
        if not specs:
            return {"count": 0, "results": [], "mode": "empty"}
        use_parallel = os.environ.get("CELERY_BACKTEST_USE_PARALLEL_GROUP", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if use_parallel and len(specs) > 1:
            try:
                from celery import group

                g = group(run_strategy_backtest_task.s(s) for s in specs)
                grp = g.apply_async()
                timeout = int(os.environ.get("CELERY_BACKTEST_GROUP_TIMEOUT_SEC", "7200"))
                raw = grp.get(timeout=timeout, disable_sync_subtasks=False)
                return {"count": len(raw), "results": list(raw), "mode": "parallel_group"}
            except Exception as e:
                # broker/worker 异常时回退顺序执行，避免任务完全失败
                err_msg = str(e)[:500]
        else:
            err_msg = None
        results: List[Any] = []
        for spec in specs:
            try:
                results.append(_run_backtest_sync(spec))
            except Exception as e:
                results.append({"error": str(e), "strategy_id": spec.get("strategy_id")})
        out: Dict[str, Any] = {"count": len(results), "results": results, "mode": "sequential"}
        if err_msg:
            out["parallel_fallback_reason"] = err_msg
        return out

    @app.task(name="system_core.tasks.backtest_tasks.dispatch_parallel_backtests_async")
    def dispatch_parallel_backtests_async_task(specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """仅派发 group，不阻塞等待结果；客户端用 AsyncResult(group_id) 或 flower 追踪。"""
        if not specs:
            return {"n": 0, "group_id": None}
        try:
            from celery import group

            g = group(run_strategy_backtest_task.s(s) for s in specs)
            async_result = g.apply_async()
            return {"n": len(specs), "group_id": async_result.id, "mode": "dispatched"}
        except Exception as e:
            return {"n": len(specs), "group_id": None, "error": str(e)[:500]}
