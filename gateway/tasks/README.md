# Gateway 异步任务

- **股票问答**：`/api/stock-qa/analyze` 已支持 `async_mode: true`，返回 `job_id`，轮询 `/api/stock-qa/jobs/{id}`（见 `endpoints_stock_qa.py`）。
- **重型回测/管道**：如需统一队列，可后续接入 Celery（`system_core/celery_app.py`）或专用表 + worker 进程；本迭代不新增并行框架以免破坏现有部署。
