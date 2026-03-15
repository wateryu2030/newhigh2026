"""Integration tests for data pipeline and data sources."""

import pytest


def test_list_sources_includes_builtin():
    """list_sources 应包含 ashare、tushare、binance 等注册源。"""
    from data_pipeline import list_sources

    sources = list_sources()
    assert "ashare_daily_kline" in sources
    assert "ashare_longhubang" in sources
    assert "tushare_daily" in sources
    assert "binance_klines" in sources


def test_get_source_ashare():
    from data_pipeline import get_source

    src = get_source("ashare_daily_kline")
    assert src is not None
    assert src.source_id == "ashare_daily_kline"


def test_get_source_tushare():
    from data_pipeline import get_source

    src = get_source("tushare_daily")
    assert src is not None
    assert src.source_id == "tushare_daily"


def test_get_source_binance():
    from data_pipeline import get_source

    src = get_source("binance_klines")
    assert src is not None
    assert src.source_id == "binance_klines"
