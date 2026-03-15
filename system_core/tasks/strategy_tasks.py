"""Celery 任务：策略生成。事件驱动架构下由 Worker 独立执行。"""

from __future__ import annotations

try:
    from system_core.celery_app import app
except Exception:
    app = None

if app is not None:

    @app.task(bind=True, name="system_core.tasks.strategy_tasks.run_strategy_task")
    def run_strategy_task(self):
        from system_core.strategy_orchestrator import run

        return run()
