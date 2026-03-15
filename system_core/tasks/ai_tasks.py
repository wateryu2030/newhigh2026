"""Celery 任务：AI 分析。事件驱动架构下由 Worker 独立执行。"""

from __future__ import annotations

try:
    from system_core.celery_app import app
except Exception:
    app = None

if app is not None:

    @app.task(bind=True, name="system_core.tasks.ai_tasks.run_ai_task")
    def run_ai_task(self):
        from system_core.ai_orchestrator import run

        return run()
