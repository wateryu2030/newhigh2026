# -*- coding: utf-8 -*-
"""
事件总线：策略信号、订单、成交、风控告警等解耦发布/订阅。
支持生产级扩展（日志、监控、风控联动）。
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    """简单内存事件总线，可替换为 Redis/RabbitMQ。"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable[..., None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[..., None]) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any = None) -> None:
        for h in self._handlers.get(event_type, []):
            try:
                h(payload)
            except Exception as e:
                logger.exception("event handler error %s: %s", event_type, e)

    def clear(self, event_type: str | None = None) -> None:
        if event_type is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event_type, None)
