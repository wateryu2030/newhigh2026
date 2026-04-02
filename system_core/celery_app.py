"""
Celery 应用：可选任务队列，将 data/scan/ai/strategy 作为异步任务执行。
需安装 celery、redis；设置 CELERY_BROKER_URL、CELERY_RESULT_BACKEND 后启动 worker 与 beat。
"""

from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
_NEWHIGH = os.path.dirname(_ROOT)
import sys

if _NEWHIGH not in sys.path:
    sys.path.insert(0, _NEWHIGH)
for _d in [
    "data-pipeline/src",
    "market-scanner/src",
    "ai-models/src",
    "strategy-engine/src",
    "core/src",
    "backtest-engine/src",
    "openclaw_engine",
]:
    _p = os.path.join(_NEWHIGH, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

broker = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")

try:
    from celery import Celery

    app = Celery(
        "system_core",
        broker=broker,
        backend=backend,
        include=[
            "system_core.tasks.data_tasks",
            "system_core.tasks.scan_tasks",
            "system_core.tasks.ai_tasks",
            "system_core.tasks.strategy_tasks",
            "system_core.tasks.pipeline_tasks",
            "system_core.tasks.backtest_tasks",
        ],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=True,
        task_track_started=True,
    )
    app.conf.beat_schedule = {
        "full-cycle-every-60s": {
            "task": "system_core.tasks.pipeline_tasks.run_full_cycle_task",
            "schedule": 60.0,
        },
    }
except ImportError:
    app = None  # type: ignore
