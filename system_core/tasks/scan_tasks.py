"""Celery 任务：市场扫描。事件驱动架构下由 Worker 独立执行。"""

from __future__ import annotations

try:
    from system_core.celery_app import app
except (ImportError, RuntimeError, OSError):
    app = None

if app is not None:

    @app.task(bind=True, name="system_core.tasks.scan_tasks.run_scan_task")
    def run_scan_task(self):
        from system_core.scan_orchestrator import run

        return run()
