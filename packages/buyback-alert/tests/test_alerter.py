"""Tests for buyback_alert.alerter core logic (cross-referencing with buyback_events)."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

# Adjust path so we can import the package
_PKG_SRC = Path(__file__).resolve().parent.parent.parent / "buyback-alert" / "src"
sys.path.insert(0, str(_PKG_SRC))

from buyback_alert.alerter import cross_reference, _ensure_alerts_table, _EVENT_TO_ALERT


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """Create a temporary DuckDB database with buyback_events and alerts tables."""
    db_file = tmp_path / "test_alerter.duckdb"
    conn = duckdb.connect(str(db_file))

    # Create buyback_events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS buyback_events (
            id INTEGER PRIMARY KEY,
            stock_code VARCHAR,
            event_type VARCHAR,
            announcement_date DATE,
            total_amount DOUBLE,
            price_low DOUBLE,
            price_high DOUBLE,
            planned_shares DOUBLE,
            actual_shares DOUBLE,
            status VARCHAR,
            source VARCHAR,
            source_url VARCHAR,
            summary VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _ensure_alerts_table(conn)
    return conn


def make_drop(stock_code: str, stock_name: str, days: int = 3, drop_pct: float = -5.0,
              end_date: str | None = None) -> dict:
    """Helper to create a drop dict like detector output."""
    end = end_date or "2025-01-15"
    start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "consecutive_drop_days": days,
        "total_drop_pct": round(drop_pct, 2),
        "start_date": start,
        "end_date": end,
        "days": days,
        "drop_pct": drop_pct,
    }


# ---------------------------------------------------------------------------
#  Tests: _EVENT_TO_ALERT mapping
# ---------------------------------------------------------------------------


class TestEventToAlertMap:
    def test_all_event_types_mapped(self):
        """All expected event types should have a mapping."""
        assert "回购" in _EVENT_TO_ALERT
        assert "增持" in _EVENT_TO_ALERT
        assert "要约收购" in _EVENT_TO_ALERT
        assert "溢价收购" in _EVENT_TO_ALERT

    def test_alert_type_strings(self):
        """Alert type strings should be descriptive."""
        assert _EVENT_TO_ALERT["回购"] == "连跌+回购"
        assert _EVENT_TO_ALERT["增持"] == "连跌+增持"
        assert _EVENT_TO_ALERT["要约收购"] == "连跌+溢价收购"
        assert _EVENT_TO_ALERT["溢价收购"] == "连跌+溢价收购"


# ---------------------------------------------------------------------------
#  Tests: cross_reference logic
# ---------------------------------------------------------------------------


class TestCrossReference:
    def test_basic_cross_reference(self, db_conn):
        """Drop + matching buyback event should produce alert."""
        # Add a buyback event
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-01-16", "公司计划回购1亿元"],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)

        assert len(alerts) == 1
        a = alerts[0]
        assert a["alert_type"] == "连跌+回购"
        assert a["stock_code"] == "600519"
        assert a["stock_name"] == "贵州茅台"
        assert a["related_event_id"] == 1
        assert a["related_event_type"] == "回购"

    def test_no_matching_event(self, db_conn):
        """Drop with no matching event should produce no alerts."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "000858", "回购", "2025-01-16", ""],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        assert len(alerts) == 0

    def test_event_outside_window(self, db_conn):
        """Event far outside lookback/lookahead window should be ignored."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-03-01", "太晚了"],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        # lookahead=5 days, so window ends 2025-01-20; event on 2025-03-01 is outside
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        assert len(alerts) == 0

    def test_event_before_window(self, db_conn):
        """Event too far before the drop window should be ignored."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2024-11-01", "太早了"],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        # lookback=30 days from start (2025-01-13) => window starts 2024-12-14
        # Event on 2024-11-01 is outside
        alerts = cross_reference(db_conn, drops, lookback_days=30, lookahead_days=5)
        assert len(alerts) == 0

    def test_dry_run_no_write(self, db_conn):
        """Dry-run mode should not write to alerts table."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-01-16", ""],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, dry_run=True, lookahead_days=5, lookback_days=30)
        assert len(alerts) == 1

        total = db_conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        assert total == 0

    def test_duplicate_suppression(self, db_conn):
        """Same alert should not be written twice."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-01-16", ""],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]

        # First call writes alert
        alerts1 = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        assert len(alerts1) == 1

        # Second call should suppress duplicate
        alerts2 = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        assert len(alerts2) == 0

    def test_multiple_event_types(self, db_conn):
        """Different event types produce different alert types."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-01-16", "回购"],
        )
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [2, "600519", "增持", "2025-01-16", "增持"],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)

        alert_types = {a["alert_type"] for a in alerts}
        assert "连跌+回购" in alert_types
        assert "连跌+增持" in alert_types

    def test_no_drops_input(self, db_conn):
        """Empty drops list should return empty alerts."""
        alerts = cross_reference(db_conn, [])
        assert alerts == []

    def test_unmapped_event_type_skipped(self, db_conn):
        """Event types not in _EVENT_TO_ALERT should be skipped."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "未知事件", "2025-01-16", ""],
        )

        drops = [make_drop("600519", "贵州茅台", end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        assert len(alerts) == 0

    def test_trigger_reason_format(self, db_conn):
        """Trigger reason should include stock, drop info, and event info."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-01-16", "1亿元回购"],
        )

        drops = [make_drop("600519", "贵州茅台", days=3, drop_pct=-6.0, end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        a = alerts[0]

        # Should mention stock name, code, drop count, pct, and event type
        assert "贵州茅台" in a["trigger_reason"]
        assert "600519" in a["trigger_reason"]
        assert "连跌3天" in a["trigger_reason"] or "3天" in a["trigger_reason"]
        assert "回购" in a["trigger_reason"]

    def test_details_json_content(self, db_conn):
        """Details JSON should contain drop and event info."""
        db_conn.execute(
            """INSERT INTO buyback_events
               (id, stock_code, event_type, announcement_date, summary)
               VALUES (?, ?, ?, ?, ?)""",
            [1, "600519", "回购", "2025-01-16", "1亿元回购"],
        )

        drops = [make_drop("600519", "贵州茅台", days=3, drop_pct=-6.0, end_date="2025-01-15")]
        alerts = cross_reference(db_conn, drops, lookahead_days=5, lookback_days=30)
        a = alerts[0]

        import json
        details = json.loads(a["details"])
        assert details["consecutive_drop_days"] == 3
        assert details["total_drop_pct"] == -6.0
        assert details["event_announcement_date"] == "2025-01-16"
        assert details["alert_type"] == "连跌+回购"
