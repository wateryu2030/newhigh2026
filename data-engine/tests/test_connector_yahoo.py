"""Tests for Yahoo connector."""
from unittest.mock import patch, MagicMock

import pytest

from data_engine import connector_yahoo
from data_engine.connector_yahoo import fetch_klines_yahoo


@pytest.mark.skipif(connector_yahoo.yf is None, reason="yfinance not installed")
def test_fetch_klines_yahoo_returns_list():
    import pandas as pd
    from datetime import datetime, timezone
    # Mock history to avoid network/rate limit
    mock_df = pd.DataFrame({
        "Open": [100.0, 101.0],
        "High": [102.0, 103.0],
        "Low": [99.0, 100.0],
        "Close": [101.0, 102.0],
        "Volume": [1e6, 1e6],
    }, index=pd.DatetimeIndex([datetime.now(timezone.utc), datetime.now(timezone.utc)]))
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_df
    with patch.object(connector_yahoo.yf, "Ticker", return_value=mock_ticker):
        rows = fetch_klines_yahoo("AAPL", interval="1d", limit=5, period="5d")
    assert isinstance(rows, list)
    assert len(rows) == 2
    from core import OHLCV
    assert isinstance(rows[0], OHLCV)
    assert rows[0].symbol == "AAPL"
    assert rows[0].close == 101.0
