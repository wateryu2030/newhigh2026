# -*- coding: utf-8 -*-
"""
统一日志配置：供每日流水线、Web 与策略运行使用。
"""
from __future__ import annotations
import logging
import sys
from typing import Optional


def init_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> None:
    """
    配置根 logger：控制台输出，可选写入文件。
    """
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt=datefmt,
        stream=sys.stdout,
        force=True,
    )
    # 第三方库降噪
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
