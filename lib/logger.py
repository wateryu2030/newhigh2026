# Auto-fixed by Cursor on 2026-04-02: unified logging for newhigh (stdlib + optional loguru).
"""统一日志：默认标准库；若安装 loguru 则同时写 logs/newhigh.log。"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

_CONFIGURED = False


def setup_logging(level: Optional[str] = None) -> None:
    """幂等配置根 logger；环境变量 LOG_LEVEL 覆盖。"""
    global _CONFIGURED
    if _CONFIGURED:
        return
    lv = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    root.setLevel(getattr(logging, lv, logging.INFO))
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
    )
    root.handlers.clear()
    root.addHandler(h)

    log_dir = Path(__file__).resolve().parents[1] / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "newhigh.log", encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
        )
        root.addHandler(fh)
    except OSError:
        pass

    try:
        from loguru import logger as loguru_logger

        loguru_logger.remove()
        loguru_logger.add(sys.stderr, level=lv)
        loguru_logger.add(str(log_dir / "newhigh_loguru.log"), rotation="10 MB", level=lv)
    except ImportError:
        pass

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
