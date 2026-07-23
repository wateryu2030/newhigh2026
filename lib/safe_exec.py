"""
安全执行工具：统一异常处理和结构化日志。
提供装饰器和上下文管理器，替代 try/except: pass 的坏习惯。
"""

from __future__ import annotations

import functools
import logging
import traceback
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

_log = logging.getLogger("safe_exec")


def safe_call(
    fallback: Any = None,
    log_level: int = logging.WARNING,
    reraise: bool = False,
) -> Callable[[F], F]:
    """
    装饰器：安全调用函数，异常时记录日志并返回 fallback。

    用法::

        @safe_call(fallback=[])
        def get_positions():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception:
                _log.log(
                    log_level,
                    "[%s] failed: %s",
                    func.__qualname__,
                    traceback.format_exc().strip().split("\n")[-1],
                )
                if reraise:
                    raise
                return fallback() if callable(fallback) else fallback

        return wrapper  # type: ignore[return-value]

    return decorator


def safe_cached_call(
    key: str,
    cache_dict: Dict[str, Any],
    fallback: Any = None,
    log_level: int = logging.WARNING,
) -> Callable[[F], F]:
    """
    带缓存的 safe_call：首次调用成功则缓存结果，后续直接返回缓存。

    用法::

        _cache: Dict[str, Any] = {}

        @safe_cached_call("positions", _cache, fallback=[])
        def get_positions():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key in cache_dict:
                return cache_dict[key]
            try:
                result = func(*args, **kwargs)
                cache_dict[key] = result
                return result
            except Exception:
                _log.log(
                    log_level,
                    "[%s] failed (cached key=%s): %s",
                    func.__qualname__,
                    key,
                    traceback.format_exc().strip().split("\n")[-1],
                )
                return fallback() if callable(fallback) else fallback

        return wrapper  # type: ignore[return-value]

    return decorator


@contextmanager
def safe_context(
    operation: str = "operation",
    fallback: Any = None,
    log_level: int = logging.ERROR,
):
    """
    上下文管理器：安全执行代码块，异常时记录日志。

    用法::

        with safe_context("risk_evaluation", fallback={"pass": True}):
            result = evaluate(positions)
    """
    try:
        yield
    except Exception:
        _log.log(
            log_level,
            "[%s] context failed: %s",
            operation,
            traceback.format_exc().strip().split("\n")[-1],
        )
        # 不能从 contextmanager 返回 fallback，但调用方可通过 else 处理


def log_and_ignore(operation: str, log_level: int = logging.WARNING) -> Callable[[F], F]:
    """简写：safe_call(fallback=None, log_level=log_level)"""
    return safe_call(fallback=None, log_level=log_level)


def log_and_return_empty(operation: str = "") -> Callable[[F], F]:
    """简写：safe_call(fallback=[])"""
    return safe_call(fallback=[], log_level=logging.WARNING)


def try_or_log(
    operation: str,
    func: Callable[..., T],
    *args: Any,
    fallback: Optional[T] = None,
    **kwargs: Any,
) -> Optional[T]:
    """
    函数式安全调用：try: func(*args, **kwargs); except: log + fallback。

    用法::

        df = try_or_log("load_signals", conn.execute, sql, [limit], fallback=None)
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        _log.warning("[%s] call failed: %s", operation, traceback.format_exc().strip().split("\n")[-1])
        return fallback
