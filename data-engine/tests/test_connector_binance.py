"""Tests for Binance connector."""
import pytest
from unittest.mock import patch, Mock

from data_engine.connector_binance import fetch_klines


@patch("data_engine.connector_binance.requests.get")
def test_fetch_klines_normalizes_response(mock_get):
    mock_get.return_value = Mock(
        status_code=200,
        json=Mock(
            return_value=[
                [
                    1609459200000,  # ts
                    "29000", "29500", "28800", "29200", "1000.5",  # o,h,l,c,v
                    1609462799999,
                    "29000000",
                    100,
                    "1000",
                    "1000",
                ]
            ]
        ),
    )
    rows = fetch_klines("BTCUSDT", "1m", limit=1)
    assert len(rows) == 1
    assert rows[0].symbol == "BTCUSDT"
    assert rows[0].open == 29000.0
    assert rows[0].high == 29500.0
    assert rows[0].low == 28800.0
    assert rows[0].close == 29200.0
    assert rows[0].volume == 1000.5
    assert rows[0].interval == "1m"
