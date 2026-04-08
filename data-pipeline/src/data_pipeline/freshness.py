"""数据新鲜度：解析时间戳并校验 /api/system/data-overview 类负载（纯函数，可单测）。"""

from __future__ import annotations

import datetime as dt
from typing import Any, Mapping

# 与 scripts/check_data_freshness.py 退出码一致
EXIT_OK = 0
EXIT_STALE = 1
EXIT_MISSING_REALTIME = 2
EXIT_INVALID = 3


def parse_freshness_timestamp(value: Any) -> dt.datetime | None:
    """将 JSON/API 中的时间字段解析为 aware 或 naive datetime；无法解析返回 None。"""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed
    return parsed


def age_seconds(now: dt.datetime, ts: dt.datetime) -> float:
    """返回 ts 相对 now 的秒数（越大越旧）。naive/aware 混用时将缺失的一方视为本地时区对齐比较。"""
    if now.tzinfo is None and ts.tzinfo is not None:
        now = now.replace(tzinfo=ts.tzinfo)
    elif now.tzinfo is not None and ts.tzinfo is None:
        ts = ts.replace(tzinfo=now.tzinfo)
    return (now - ts).total_seconds()


def _extract_snapshot_times(payload: Mapping[str, Any]) -> tuple[Any, Any]:
    """
    Gateway /api/system/data-overview 使用 data_freshness；
    旧版或测试可使用 freshness.realtime_snapshot_time 等字段。
    """
    df = payload.get("data_freshness")
    if isinstance(df, Mapping) and (
        df.get("a_stock_realtime_max") is not None or df.get("a_stock_limitup_max") is not None
    ):
        return df.get("a_stock_realtime_max"), df.get("a_stock_limitup_max")
    leg = payload.get("freshness")
    if isinstance(leg, Mapping):
        return leg.get("realtime_snapshot_time"), leg.get("limitup_snapshot_time")
    return None, None


def _comparison_now(
    explicit_now: dt.datetime | None,
    rt_ts: dt.datetime | None,
    lu_ts: dt.datetime | None,
) -> dt.datetime:
    """
    DuckDB 常见为 **naive 本地墙钟**；若任一时间戳为 naive，则用本地 naive now 比较，避免误当 UTC。
    若快照均为 aware，则用 UTC（或与传入的 aware now 对齐）。
    """
    snap_naive = (rt_ts is not None and rt_ts.tzinfo is None) or (
        lu_ts is not None and lu_ts.tzinfo is None
    )
    if explicit_now is not None:
        n = explicit_now
        if snap_naive and n.tzinfo is not None:
            return n.astimezone().replace(tzinfo=None)
        if not snap_naive and n.tzinfo is None:
            return n.replace(tzinfo=dt.timezone.utc)
        return n
    if snap_naive:
        return dt.datetime.now()
    return dt.datetime.now(dt.timezone.utc)


def check_overview_payload(
    payload: Mapping[str, Any],
    *,
    max_age_realtime_sec: float,
    max_age_limitup_sec: float,
    require_realtime: bool,
    now: dt.datetime | None = None,
) -> tuple[int, str]:
    """
    校验 data-overview JSON。

    Returns:
        (exit_code, message)
    """
    if not isinstance(payload, Mapping):
        return EXIT_INVALID, "payload is not an object"
    if not payload.get("ok"):
        err = payload.get("error", "unknown")
        return EXIT_INVALID, f"overview not ok: {err}"

    rt_raw, lu_raw = _extract_snapshot_times(payload)
    rt_ts = parse_freshness_timestamp(rt_raw)
    lu_ts = parse_freshness_timestamp(lu_raw)

    now = _comparison_now(now, rt_ts, lu_ts)

    if require_realtime and rt_ts is None:
        return EXIT_MISSING_REALTIME, "realtime snapshot time missing but required"

    if rt_ts is not None:
        if age_seconds(now, rt_ts) > max_age_realtime_sec:
            return EXIT_STALE, f"realtime stale (>{max_age_realtime_sec}s)"

    if lu_ts is not None:
        if age_seconds(now, lu_ts) > max_age_limitup_sec:
            return EXIT_STALE, f"limitup stale (>{max_age_limitup_sec}s)"

    return EXIT_OK, "ok"
