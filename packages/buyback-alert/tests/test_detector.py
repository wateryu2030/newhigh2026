"""Tests for buyback_alert.detector core logic (consecutive drop detection with synthetic data)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

# Adjust path so we can import the package
_PKG_SRC = Path(__file__).resolve().parent.parent.parent / "buyback-alert" / "src"
sys.path.insert(0, str(_PKG_SRC))

from buyback_alert.detector import detect_consecutive_drops


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

TABLE_DDL = {
    "stocks": """
        CREATE TABLE IF NOT EXISTS stocks (
            order_book_id VARCHAR,
            symbol VARCHAR,
            name VARCHAR,
            type VARCHAR
        )
    """,
    "daily_bars": """
        CREATE TABLE IF NOT EXISTS daily_bars (
            order_book_id VARCHAR,
            trade_date DATE,
            close DOUBLE
        )
    """,
}


@pytest.fixture
def db_conn(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """Create a temporary DuckDB database with stocks and daily_bars tables."""
    db_file = tmp_path / "test_detector.duckdb"
    conn = duckdb.connect(str(db_file))
    for ddl in TABLE_DDL.values():
        conn.execute(ddl)
    return conn


def insert_bar(
    conn: duckdb.DuckDBPyConnection,
    order_book_id: str,
    trade_date: str,
    close: float,
) -> None:
    conn.execute(
        "INSERT INTO daily_bars (order_book_id, trade_date, close) VALUES (?, ?, ?)",
        [order_book_id, trade_date, close],
    )


# ---------------------------------------------------------------------------
#  Tests: consecutive drop detection algorithm
# ---------------------------------------------------------------------------


class TestDetectConsecutiveDrops:
    def test_3_consecutive_drops(self, db_conn):
        """Stock with 3 consecutive drops should be detected."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)  # day 0
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 98.0)  # drop 1
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 96.0)  # drop 2
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 94.0)  # drop 3 ✓

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 1
        assert results[0]["stock_code"] == "600519"
        assert results[0]["consecutive_drop_days"] == 3
        # Drop from 100 -> 94 = -6.0%
        assert abs(results[0]["total_drop_pct"] - (-6.0)) < 0.01

    def test_no_drops(self, db_conn):
        """Stock with no drops should not appear in results."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 101.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 102.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 103.0)

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 0

    def test_uptrend_after_drops(self, db_conn):
        """Stock with fewer drops than min_days should not appear."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 98.0)  # drop 1
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 99.0)  # up
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 97.0)  # drop, but not consecutive

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 0

    def test_4_consecutive_drops(self, db_conn):
        """4 consecutive drops should be detected with min_days=3."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["000858.XSHE", "000858", "五粮液", "CS"],
        )

        insert_bar(db_conn, "000858.XSHE", "2025-01-06", 200.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-07", 195.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-08", 190.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-09", 185.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-10", 180.0)  # 4th drop

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 1
        assert results[0]["consecutive_drop_days"] == 4
        # 200 -> 180 = -10.0%
        assert abs(results[0]["total_drop_pct"] - (-10.0)) < 0.01

    def test_multiple_stocks_one_with_drops(self, db_conn):
        """Among multiple stocks, only the one with drops should be detected."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["000858.XSHE", "000858", "五粮液", "CS"],
        )

        # Stock 1: drops
        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 97.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 94.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 91.0)

        # Stock 2: flat
        insert_bar(db_conn, "000858.XSHE", "2025-01-06", 150.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-07", 151.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-08", 152.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-09", 153.0)

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 1
        assert results[0]["stock_code"] == "600519"

    def test_dry_run_no_effect_on_results(self, db_conn):
        """Dry-run mode should still return results."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 97.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 94.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 91.0)

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120, dry_run=True)
        assert len(results) == 1
        assert results[0]["consecutive_drop_days"] == 3

    def test_no_stocks(self, db_conn):
        """Empty stocks table should return empty list."""
        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert results == []

    def test_no_bars(self, db_conn):
        """Stock exists but no bars should return empty."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )
        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert results == []

    def test_symbol_filter(self, db_conn):
        """Filtering by symbol should only check that stock."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["000858.XSHE", "000858", "五粮液", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 97.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 94.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 91.0)

        insert_bar(db_conn, "000858.XSHE", "2025-01-06", 150.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-07", 145.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-08", 140.0)
        insert_bar(db_conn, "000858.XSHE", "2025-01-09", 135.0)

        # Only look at 600519
        results = detect_consecutive_drops(db_conn, min_days=3, symbol="600519", trade_date_limit=120)
        assert len(results) == 1
        assert results[0]["stock_code"] == "600519"

    def test_results_have_correct_keys(self, db_conn):
        """Each result dict should have the expected fields."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 97.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 94.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 91.0)

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        r = results[0]

        assert "stock_code" in r
        assert "stock_name" in r
        assert "consecutive_drop_days" in r
        assert "total_drop_pct" in r
        assert "start_date" in r
        assert "end_date" in r

    def test_insufficient_bars(self, db_conn):
        """Fewer bars than min_days+1 should not trigger."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 98.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 96.0)

        # Only 3 bars, need min_days+1=4 for 3-drop detection
        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 0

    def test_mixed_up_and_down(self, db_conn):
        """Series with up/down should only count proper consecutive drops."""
        db_conn.execute(
            "INSERT INTO stocks (order_book_id, symbol, name, type) VALUES (?, ?, ?, ?)",
            ["600519.XSHG", "600519", "贵州茅台", "CS"],
        )

        # 100(d0) -> 98(d1 drop) -> 99(d2 up) -> 96(d3 drop) -> 94(d4 drop) -> 92(d5 drop)
        insert_bar(db_conn, "600519.XSHG", "2025-01-06", 100.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-07", 98.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-08", 99.0)  # up
        insert_bar(db_conn, "600519.XSHG", "2025-01-09", 96.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-10", 94.0)
        insert_bar(db_conn, "600519.XSHG", "2025-01-13", 92.0)

        results = detect_consecutive_drops(db_conn, min_days=3, trade_date_limit=120)
        assert len(results) == 1
        assert results[0]["consecutive_drop_days"] == 3
        # The 3-drop: 99 -> 96 -> 94 -> 92 (3 drops starting from 99)
        # Actually: 99(d2) -> 96(d3) drop1, 96->94(d4) drop2, 94->92(d5) drop3
        # total drop from 99 to 92 = -7.07%
        assert abs(results[0]["total_drop_pct"] - (-7.07)) < 0.1
