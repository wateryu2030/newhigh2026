# Centralized JSON logging for Filebeat/Loki; 支持 service、trace_id（可观测性）
from __future__ import annotations
import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# 请求级 trace_id，Gateway 中间件可设置
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": os.environ.get("SERVICE_NAME", "newhigh"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        tid = trace_id_ctx.get()
        if tid:
            log_obj["trace_id"] = tid
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


def configure_logging(
        level: str | None = None,
        json_output: bool | None = None,
        logger_name: str | None = None) -> None:
    lvl = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    use_json = json_output if json_output is not None else os.environ.get(
        "LOG_JSON", "").lower() in ("1", "true", "yes")
    logger = logging.getLogger(
        logger_name) if logger_name else logging.getLogger()
    logger.setLevel(getattr(logging, lvl, logging.INFO))
    if logger.handlers:
        for h in logger.handlers[:]:
            logger.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if use_json else logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(handler)
