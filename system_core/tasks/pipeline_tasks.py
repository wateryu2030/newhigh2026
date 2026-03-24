"""Celery 任务：全周期链式调用 data → scan → ai → strategy，供 worker 与 beat 调用。"""

from __future__ import annotations


def _run_full_cycle_sync() -> dict:
    from system_core.system_runner import run_once

    return run_once(
        run_data=True,
        run_scan=True,
        run_ai=True,
        run_strategy=True,
        data_include_daily_kline=False,
        data_daily_kline_limit=0,
    )


try:
    from system_core.celery_app import app
except (ImportError, RuntimeError, OSError):
    app = None

if app is not None:

    @app.task(bind=True, name="system_core.tasks.pipeline_tasks.run_full_cycle_task")
    def run_full_cycle_task(self):
        """单任务同步执行全周期（兼容 beat）；事件驱动下可改用 run_full_cycle_chain 异步串行。"""
        return _run_full_cycle_sync()

    def run_full_cycle_chain():
        """异步链式执行：data → scan → ai → strategy，返回 chain 的 AsyncResult。"""
        from celery import chain
        from system_core.tasks.data_tasks import run_data_task
        from system_core.tasks.scan_tasks import run_scan_task
        from system_core.tasks.ai_tasks import run_ai_task
        from system_core.tasks.strategy_tasks import run_strategy_task

        return chain(
            run_data_task.s(),
            run_scan_task.s(),
            run_ai_task.s(),
            run_strategy_task.s(),
        ).apply_async()

    @app.task(bind=True, name="system_core.tasks.pipeline_tasks.run_evolution_task")
    def run_evolution_task(self, population_limit: int = 10, symbol: str = "000001.SZ"):
        """OpenClaw 进化周期：从策略市场加载种群，遗传操作，回测评估，优秀个体写回。"""
        try:
            from openclaw_engine import run_evolution_cycle

            return run_evolution_cycle(population_limit=population_limit, symbol=symbol)
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            return {"error": str(e), "saved": 0}
