"""
按用户（或匿名 IP）的日配额与简单滑动窗口限流；默认内存计数，重启清零。
支持 user_level（trial / basic / pro）：不同级别可配置不同上限（环境变量）。
"""

from __future__ import annotations

import os
import threading
from datetime import date, datetime, timezone
from typing import Optional, Tuple

_lock = threading.Lock()
# key: (day_iso, user_or_ip, kind) -> count
_counters: dict[tuple[str, str, str], int] = {}


def _today_iso() -> str:
    return date.today().isoformat()


def _resolve_limit(kind: str, user_level: Optional[str]) -> int:
    """返回当日上限（stock_qa 或 backtest）。"""
    qa_default = int(os.environ.get("FREE_STOCK_QA_PER_DAY", "20"))
    bt_default = int(os.environ.get("FREE_BACKTEST_PER_DAY", "10"))
    if not user_level or not str(user_level).strip():
        return max(1, qa_default if kind == "stock_qa" else bt_default)
    lv = str(user_level).strip().lower()
    if kind == "stock_qa":
        if lv == "trial":
            return max(1, int(os.environ.get("QUOTA_TRIAL_STOCK_QA", "5")))
        if lv == "basic":
            return max(1, int(os.environ.get("QUOTA_BASIC_STOCK_QA", "20")))
        if lv in ("pro", "enterprise", "admin"):
            return max(1, int(os.environ.get("QUOTA_PRO_STOCK_QA", "100")))
        return max(1, qa_default)
    if lv == "trial":
        return max(1, int(os.environ.get("QUOTA_TRIAL_BACKTEST_PER_DAY", "5")))
    if lv == "basic":
        return max(1, int(os.environ.get("QUOTA_BASIC_BACKTEST_PER_DAY", "10")))
    if lv in ("pro", "enterprise", "admin"):
        return max(1, int(os.environ.get("QUOTA_PRO_BACKTEST_PER_DAY", "50")))
    return max(1, bt_default)


def reset_counters_for_tests() -> None:
    with _lock:
        _counters.clear()


def check_and_increment(
    user_key: str,
    kind: str,
    user_level: Optional[str] = None,
) -> Tuple[bool, str, int, int]:
    """
    kind: stock_qa | backtest
    user_level: trial/basic/pro；匿名不传则使用 FREE_* 环境变量上限。
    返回 (allowed, message, used, limit).
    """
    day = _today_iso()
    limit = _resolve_limit(kind, user_level)
    k = (day, user_key, kind)
    with _lock:
        cur = _counters.get(k, 0)
        if cur >= limit:
            return False, f"今日{kind}次数已达上限（{limit}）", cur, limit
        _counters[k] = cur + 1
        return True, "ok", cur + 1, limit


def peek(user_key: str, kind: str, user_level: Optional[str] = None) -> Tuple[int, int]:
    """不递增，仅查看今日已用与上限。"""
    day = _today_iso()
    limit = _resolve_limit(kind, user_level)
    with _lock:
        cur = _counters.get((day, user_key, kind), 0)
    return cur, limit


def default_quota_payload(user_key: str, user_level: Optional[str] = None) -> dict:
    s_used, s_lim = peek(user_key, "stock_qa", user_level)
    b_used, b_lim = peek(user_key, "backtest", user_level)
    return {
        "day": _today_iso(),
        "user_level": user_level or "trial",
        "stock_qa": {"used": s_used, "limit": s_lim},
        "backtest": {"used": b_used, "limit": b_lim},
    }
