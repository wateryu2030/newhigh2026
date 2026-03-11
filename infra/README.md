# 基础设施

- **日志**：统一 JSON 日志由 `core/src/core/logging_config.py` 提供。各模块启动时调用 `from core.logging_config import configure_logging` 并执行 `configure_logging()`；通过环境变量 `LOG_LEVEL`（如 INFO）、`LOG_JSON=true` 启用 JSON 输出，便于 Filebeat / Loki 采集。
- **监控**：见上级目录 `monitoring/`（Prometheus 配置与说明）。
