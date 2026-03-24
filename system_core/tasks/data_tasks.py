"""Celery 任务：数据管道。事件驱动架构下由 Worker 独立执行。"""

from __future__ import annotations

try:
    from system_core.celery_app import app
except (ImportError, RuntimeError, OSError):
    app = None

if app is not None:

    @app.task(bind=True, name="system_core.tasks.data_tasks.run_data_task")
    def run_data_task(
        self,
        run_stock_list: bool = True,
        run_daily_kline: bool = False,
        run_realtime: bool = True,
        run_fundflow: bool = True,
        run_limitup: bool = True,
        run_longhubang: bool = True,
        daily_kline_codes_limit: int = 0,
    ):
        from system_core.data_orchestrator import update

        return update(
            run_stock_list=run_stock_list,
            run_daily_kline=run_daily_kline,
            run_realtime=run_realtime,
            run_fundflow=run_fundflow,
            run_limitup=run_limitup,
            run_longhubang=run_longhubang,
            daily_kline_codes_limit=daily_kline_codes_limit,
        )
