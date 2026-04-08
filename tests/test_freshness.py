"""data_pipeline.freshness 纯函数单测。"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_dp = _ROOT / "data-pipeline" / "src"
if _dp.is_dir():
    s = str(_dp)
    if s not in sys.path:
        sys.path.insert(0, s)

from data_pipeline.freshness import (  # noqa: E402
    EXIT_INVALID,
    EXIT_MISSING_REALTIME,
    EXIT_OK,
    EXIT_STALE,
    age_seconds,
    check_overview_payload,
    parse_freshness_timestamp,
)


def test_parse_freshness_timestamp_none_and_iso_z():
    assert parse_freshness_timestamp(None) is None
    assert parse_freshness_timestamp("") is None
    ts = parse_freshness_timestamp("2026-01-15T12:00:00Z")
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_freshness_timestamp_naive_iso():
    ts = parse_freshness_timestamp("2026-01-15T12:00:00")
    assert ts is not None
    assert ts.tzinfo is None


def test_age_seconds_naive():
    a = dt.datetime(2026, 1, 15, 12, 0, 0)
    b = dt.datetime(2026, 1, 15, 12, 2, 0)
    assert age_seconds(b, a) == pytest.approx(120.0)


def test_check_overview_ok():
    fixed = dt.datetime(2026, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc)
    payload = {
        "ok": True,
        "freshness": {
            "realtime_snapshot_time": fixed.isoformat().replace("+00:00", "Z"),
            "limitup_snapshot_time": fixed.isoformat().replace("+00:00", "Z"),
        },
        "counts": {},
    }
    now = fixed
    code, msg = check_overview_payload(
        payload,
        max_age_realtime_sec=60,
        max_age_limitup_sec=60,
        require_realtime=True,
        now=now,
    )
    assert code == EXIT_OK
    assert msg == "ok"


def test_check_overview_stale_realtime():
    old = dt.datetime(2026, 1, 15, 10, 0, 0, tzinfo=dt.timezone.utc)
    now = dt.datetime(2026, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc)
    payload = {
        "ok": True,
        "freshness": {"realtime_snapshot_time": old.isoformat(), "limitup_snapshot_time": now.isoformat()},
        "counts": {},
    }
    code, msg = check_overview_payload(
        payload,
        max_age_realtime_sec=60,
        max_age_limitup_sec=3600,
        require_realtime=True,
        now=now,
    )
    assert code == EXIT_STALE
    assert "realtime stale" in msg


def test_check_overview_missing_realtime_required():
    payload = {
        "ok": True,
        "freshness": {"limitup_snapshot_time": "2026-01-15T12:00:00+00:00"},
        "counts": {},
    }
    code, msg = check_overview_payload(
        payload,
        max_age_realtime_sec=120,
        max_age_limitup_sec=360,
        require_realtime=True,
        now=dt.datetime(2026, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc),
    )
    assert code == EXIT_MISSING_REALTIME


def test_check_overview_not_ok():
    code, msg = check_overview_payload(
        {"ok": False, "error": "db", "freshness": {}},
        max_age_realtime_sec=120,
        max_age_limitup_sec=360,
        require_realtime=False,
    )
    assert code == EXIT_INVALID
    assert "not ok" in msg


def test_check_overview_data_freshness_gateway_shape():
    """与 Gateway endpoints_system_data 返回的 data_freshness 一致（naive 墙钟 + 本地 now）。"""
    fixed_naive = dt.datetime(2026, 1, 15, 12, 0, 0)
    payload = {
        "ok": True,
        "counts": {},
        "data_freshness": {
            "a_stock_realtime_max": fixed_naive.strftime("%Y-%m-%d %H:%M:%S"),
            "a_stock_limitup_max": fixed_naive.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
    code, msg = check_overview_payload(
        payload,
        max_age_realtime_sec=120,
        max_age_limitup_sec=120,
        require_realtime=True,
        now=fixed_naive,
    )
    assert code == EXIT_OK
    assert msg == "ok"
