# Ingest worker（中期规划）

- **方向**：用 Redis + 任务队列（RQ / Celery 等）承载采集与写入；**单 writer** 进程写 DuckDB，避免与 Gateway 读路径争用同库锁。
- **Gateway**：保持 **读多写少**，复杂 ingest 不阻塞 API 线程。
- **本机流水线**：停 Gateway → 刷新快照 → 再起 Gateway → 探活与新鲜度，见仓库根目录 [`scripts/gateway_batch_pipeline.sh`](../../../scripts/gateway_batch_pipeline.sh)。
