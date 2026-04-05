"""Tests for akshare A-share connector (mock to avoid network)."""

from unittest.mock import MagicMock, patch

import pytest

from data_engine.connector_akshare import (
    _normalize_symbol,
    fetch_klines_akshare,
)


def test_normalize_symbol():
    assert _normalize_symbol("600519") == "600519.SH"
    assert _normalize_symbol("000001") == "000001.SZ"
    assert _normalize_symbol("000001.SZ") == "000001.SZ"
    assert _normalize_symbol("300750") == "300750.SZ"


@patch("data_engine.connector_akshare.ak")
def test_fetch_klines_akshare_mock(mock_ak):
    import pandas as pd

    df = pd.DataFrame(
        {
            "日期": ["2024-01-02", "2024-01-03"],
            "开盘": [100.0, 101.0],
            "收盘": [101.0, 102.0],
            "最高": [102.0, 103.0],
            "最低": [99.0, 100.0],
            "成交量": [1e6, 1.2e6],
        }
    )
    mock_ak.stock_zh_a_hist_em.side_effect = Exception("mock skip em")
    mock_ak.stock_zh_a_hist.return_value = df
    rows = fetch_klines_akshare("600519", "20240101", "20240110", period="daily")
    assert len(rows) == 2
    assert rows[0].symbol == "600519.SH"
    assert rows[0].interval == "1d"
    assert rows[0].open == 100.0 and rows[0].close == 101.0
    mock_ak.stock_zh_a_hist.assert_called_once_with(
        symbol="600519",
        start_date="20240101",
        end_date="20240110",
        period="daily",
        adjust="qfq",
    )


def test_fetch_klines_akshare_no_ak():
    with patch("data_engine.connector_akshare.ak", None):
        with pytest.raises(ImportError, match="akshare"):
            fetch_klines_akshare("600519", "20240101", "20240110")


def test_fetch_klines_akshare_bad_symbol():
    with patch("data_engine.connector_akshare.ak", MagicMock()):
        with pytest.raises(ValueError, match="6 or 8 digits"):
            fetch_klines_akshare("123", "20240101", "20240110")
