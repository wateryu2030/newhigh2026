"""Tests for astock DuckDB connector (mock DB when not present)."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


def test_order_book_id_to_symbol():
    from data_engine.connector_astock_duckdb import _order_book_id_to_symbol
    assert _order_book_id_to_symbol("600519.XSHG") == "600519.SH"
    assert _order_book_id_to_symbol("000001.XSHE") == "000001.SZ"
    assert _order_book_id_to_symbol("430047.BSE") == "430047.BSE"


def test_symbol_to_order_book_id():
    from data_engine.connector_astock_duckdb import _symbol_to_order_book_id
    assert _symbol_to_order_book_id("600519") == "600519.XSHG"
    assert _symbol_to_order_book_id("600519.SH") == "600519.XSHG"
    assert _symbol_to_order_book_id("000001") == "000001.XSHE"
    assert _symbol_to_order_book_id("000001.SZ") == "000001.XSHE"


@patch("data_engine.connector_astock_duckdb._get_conn")
def test_fetch_klines_from_astock_duckdb_mock(mock_conn):
    import pandas as pd
    from data_engine.connector_astock_duckdb import fetch_klines_from_astock_duckdb
    conn = MagicMock()
    conn.execute.return_value.fetchdf.return_value = pd.DataFrame({
        "order_book_id": ["600519.XSHG", "600519.XSHG"],
        "trade_date": [date(2024, 1, 2), date(2024, 1, 3)],
        "open": [100.0, 101.0],
        "high": [102.0, 103.0],
        "low": [99.0, 100.0],
        "close": [101.0, 102.0],
        "volume": [1e6, 1.2e6],
    })
    mock_conn.return_value = conn
    rows = fetch_klines_from_astock_duckdb("600519", start_date="2024-01-01", end_date="2024-01-10")
    assert len(rows) == 2
    assert rows[0].symbol == "600519.SH"
    assert rows[0].interval == "1d"
    assert rows[0].close == 101.0


def test_get_astock_duckdb_available_no_file():
    with patch("data_engine.connector_astock_duckdb.os.path.isfile", return_value=False):
        from data_engine.connector_astock_duckdb import get_astock_duckdb_available
        assert get_astock_duckdb_available() is False
