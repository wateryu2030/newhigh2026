# Auto-fixed by Cursor on 2026-04-02: BaseStrategy + prevent_future_data decorator.
"""策略基类：向量化 generate_signals 与可选止损止盈参数。"""

from __future__ import annotations

import functools
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Tuple

import pandas as pd

_log = logging.getLogger(__name__)


def prevent_future_data(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    装饰向量化信号函数：要求第一个位置参数为 DataFrame 时索引单调递增，
    且列名不得包含明显未来字段（启发式，非完备证明）。
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if args and isinstance(args[0], pd.DataFrame):
            df = args[0]
            if not df.index.is_monotonic_increasing:
                _log.warning(
                    "%s: DataFrame index not monotonic increasing; risk of lookahead bugs",
                    fn.__name__,
                )
            bad = [c for c in df.columns if "future" in str(c).lower() or "next_ret" in str(c).lower()]
            if bad:
                _log.warning("%s: suspicious columns (possible lookahead): %s", fn.__name__, bad)
        return fn(*args, **kwargs)

    return wrapper


class BaseStrategy(ABC):
    """向量化策略基类；子类实现 generate_signals。"""

    def __init__(self) -> None:
        self._stop_loss_pct: Optional[float] = None
        self._take_profit_pct: Optional[float] = None

    def set_stop_loss(self, pct: float) -> None:
        """pct 如 0.08 表示亏损 8% 止损（由上层回测消费）。"""
        self._stop_loss_pct = float(pct)

    def set_take_profit(self, pct: float) -> None:
        self._take_profit_pct = float(pct)

    @property
    def stop_loss_pct(self) -> Optional[float]:
        return self._stop_loss_pct

    @property
    def take_profit_pct(self) -> Optional[float]:
        return self._take_profit_pct

    def init(self) -> None:
        """可选：加载参数。"""

    @abstractmethod
    def generate_signals(self, ohlcv: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """输入含 date 索引或列的 OHLCV，返回 (entries, exits) 布尔 Series。"""
