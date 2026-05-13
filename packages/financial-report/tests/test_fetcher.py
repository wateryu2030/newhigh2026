"""Tests for financial_report.fetcher core logic (DB write/read, report type detection, dry-run)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

# Adjust path so we can import the package
_PKG_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_PKG_SRC))

from financial_report.fetcher import (
    determine_report_type,
    ensure_table,
    parse_sina_rows,
    write_reports,
    deduplicate_stock_reports,
)


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """Create a temporary DuckDB database for testing."""
    db_file = tmp_path / "test_financial.duckdb"
    conn = duckdb.connect(str(db_file))
    ensure_table(conn)
    return conn


# ---------------------------------------------------------------------------
#  determine_report_type
# ---------------------------------------------------------------------------


class TestDetermineReportType:
    def test_annual_report_dec31(self):
        """20251231 should be classified as 年报."""
        assert determine_report_type("20251231") == "年报"

    def test_annual_report_jan(self):
        """20260115 should be 年报 (January is 年报)."""
        assert determine_report_type("20260115") == "年报"

    def test_annual_report_feb(self):
        """20260201 should be 年报."""
        assert determine_report_type("20260201") == "年报"

    def test_q1_report_march(self):
        """20260331 should be 一季报."""
        assert determine_report_type("20260331") == "一季报"

    def test_q1_report_april(self):
        """20260415 should be 一季报."""
        assert determine_report_type("20260415") == "一季报"

    def test_h1_report_may(self):
        """20260515 should be 中报/半年报."""
        assert determine_report_type("20260515") == "中报/半年报"

    def test_h1_report_aug(self):
        """20260815 should be 中报/半年报."""
        assert determine_report_type("20260815") == "中报/半年报"

    def test_q3_report_sep(self):
        """20260930 should be 三季报."""
        assert determine_report_type("20260930") == "三季报"

    def test_q3_report_nov(self):
        """20261115 should be 三季报."""
        assert determine_report_type("20261115") == "三季报"

    def test_dec_not_31(self):
        """20261215 is December but not 31st, should still be 年报 (December maps to 年报)."""
        assert determine_report_type("20261215") == "年报"

    def test_empty_string(self):
        """Empty string should return 年报."""
        assert determine_report_type("") == "年报"

    def test_short_string(self):
        """Short string < 6 chars should return 年报."""
        assert determine_report_type("2025") == "年报"

    def test_invalid_chars(self):
        """Invalid characters should return 年报."""
        assert determine_report_type("abcdef") == "年报"


# ---------------------------------------------------------------------------
#  parse_sina_rows
# ---------------------------------------------------------------------------


class TestParseSinaRows:
    def test_basic_parse(self):
        """Parse a valid DataFrame row."""
        df = pd.DataFrame(
            [
                {
                    "报告日": "20251231",
                    "类型": "年报",
                    "币种": "CNY",
                    "净利润": 100000000,
                    "营业收入": 500000000,
                }
            ]
        )
        rows = parse_sina_rows("600519", "利润表", df)
        assert len(rows) == 1
        assert rows[0]["stock_code"] == "600519"
        assert rows[0]["statement_type"] == "利润表"
        assert rows[0]["report_type"] == "年报"
        assert rows[0]["currency"] == "CNY"
        assert rows[0]["period_end"] == "年报"
        data = json.loads(rows[0]["data_json"])
        assert data["净利润"] == 100000000

    def test_multiple_rows(self):
        """Parse multiple report rows from DataFrame."""
        df = pd.DataFrame(
            [
                {"报告日": "20251231", "类型": "年报", "币种": "CNY"},
                {"报告日": "20250630", "类型": "中报", "币种": "CNY"},
            ]
        )
        rows = parse_sina_rows("000858", "资产负债表", df)
        assert len(rows) == 2
        assert rows[0]["report_date"].isoformat() == "2025-12-31"
        assert rows[1]["report_date"].isoformat() == "2025-06-30"

    def test_empty_report_date_skipped(self):
        """Rows with empty report date should be skipped."""
        df = pd.DataFrame(
            [
                {"报告日": "", "类型": "年报", "币种": "CNY"},
                {"报告日": "20251231", "类型": "年报", "币种": "CNY"},
            ]
        )
        rows = parse_sina_rows("600519", "利润表", df)
        assert len(rows) == 1

    def test_date_with_dash_format(self):
        """Report date in YYYY-MM-DD format should also be parsed."""
        df = pd.DataFrame(
            [
                {"报告日": "2025-12-31", "类型": "年报", "币种": "CNY"},
            ]
        )
        rows = parse_sina_rows("600519", "利润表", df)
        assert len(rows) == 1
        assert rows[0]["report_date"].isoformat() == "2025-12-31"

    def test_default_currency(self):
        """Empty currency should default to CNY."""
        df = pd.DataFrame(
            [
                {"报告日": "20251231", "类型": "年报", "币种": None},
            ]
        )
        rows = parse_sina_rows("600519", "利润表", df)
        assert rows[0]["currency"] == "CNY"

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty list."""
        df = pd.DataFrame()
        rows = parse_sina_rows("600519", "利润表", df)
        assert rows == []


# ---------------------------------------------------------------------------
#  DB write / read / dedup
# ---------------------------------------------------------------------------


class TestDBWriteRead:
    def test_write_and_read_back(self, db_conn):
        """Write rows then read them back from the database."""
        rows = [
            {
                "stock_code": "600519",
                "report_date": "2025-12-31",
                "report_type": "年报",
                "statement_type": "利润表",
                "period_end": "年报",
                "data_json": json.dumps({"净利润": 100}, ensure_ascii=False),
                "currency": "CNY",
                "created_at": "2025-01-01 00:00:00",
            }
        ]
        # Convert report_date string to date object
        from datetime import date

        rows[0]["report_date"] = date.fromisoformat(rows[0]["report_date"])

        count = write_reports(db_conn, rows)
        assert count == 1

        result = db_conn.execute(
            "SELECT stock_code, report_type, statement_type FROM financial_reports"
        ).fetchall()
        assert len(result) == 1
        assert result[0][0] == "600519"
        assert result[0][1] == "年报"
        assert result[0][2] == "利润表"

    def test_write_multiple_rows(self, db_conn):
        """Write multiple rows and verify count."""
        from datetime import date

        rows = [
            {
                "stock_code": "600519",
                "report_date": date(2025, 12, 31),
                "report_type": "年报",
                "statement_type": "利润表",
                "period_end": "年报",
                "data_json": "{}",
                "currency": "CNY",
                "created_at": "2025-01-01 00:00:00",
            },
            {
                "stock_code": "000858",
                "report_date": date(2025, 6, 30),
                "report_type": "中报/半年报",
                "statement_type": "资产负债表",
                "period_end": "中报",
                "data_json": "{}",
                "currency": "CNY",
                "created_at": "2025-01-01 00:00:00",
            },
        ]
        count = write_reports(db_conn, rows)
        assert count == 2

        count_all = db_conn.execute(
            "SELECT COUNT(*) FROM financial_reports"
        ).fetchone()[0]
        assert count_all == 2

    def test_write_empty_rows(self, db_conn):
        """Writing empty list should return 0."""
        count = write_reports(db_conn, [])
        assert count == 0

    def test_dry_run_does_not_write(self, db_conn):
        """Dry-run mode should not actually insert data."""
        from datetime import date

        rows = [
            {
                "stock_code": "600519",
                "report_date": date(2025, 12, 31),
                "report_type": "年报",
                "statement_type": "利润表",
                "period_end": "年报",
                "data_json": "{}",
                "currency": "CNY",
                "created_at": "2025-01-01 00:00:00",
            }
        ]
        count = write_reports(db_conn, rows, dry_run=True)
        assert count == 1  # Returns the planned write count

        count_all = db_conn.execute(
            "SELECT COUNT(*) FROM financial_reports"
        ).fetchone()[0]
        assert count_all == 0  # Nothing actually written

    def test_dedup(self, db_conn):
        """deduplicate_stock_reports should identify existing dates."""
        from datetime import date

        # Insert a row first
        rows = [
            {
                "stock_code": "600519",
                "report_date": date(2025, 12, 31),
                "report_type": "年报",
                "statement_type": "利润表",
                "period_end": "年报",
                "data_json": "{}",
                "currency": "CNY",
                "created_at": "2025-01-01 00:00:00",
            }
        ]
        write_reports(db_conn, rows)

        # Query for dedup
        existing = deduplicate_stock_reports(
            db_conn, "600519", "利润表", [date(2025, 12, 31), date(2025, 6, 30)]
        )
        assert date(2025, 12, 31) in existing
        assert date(2025, 6, 30) not in existing

    def test_data_json_content(self, db_conn):
        """Verify data_json column stores and retrieves correct JSON."""
        from datetime import date

        original_data = {"净利润": 123456789, "营业收入": 987654321, "币种": "CNY"}
        rows = [
            {
                "stock_code": "600519",
                "report_date": date(2025, 12, 31),
                "report_type": "年报",
                "statement_type": "利润表",
                "period_end": "年报",
                "data_json": json.dumps(original_data, ensure_ascii=False),
                "currency": "CNY",
                "created_at": "2025-01-01 00:00:00",
            }
        ]
        write_reports(db_conn, rows)

        result = db_conn.execute(
            "SELECT data_json FROM financial_reports WHERE stock_code='600519'"
        ).fetchone()
        retrieved = json.loads(result[0])
        assert retrieved["净利润"] == 123456789
        assert retrieved["营业收入"] == 987654321
