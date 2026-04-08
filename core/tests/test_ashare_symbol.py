"""core.ashare_symbol 单测（无网络）。"""

from core.ashare_symbol import (
    ashare_symbol_to_tushare_ts_code,
    normalize_ashare_symbol,
    normalize_ashare_symbol_bj_display,
    order_book_id_to_newhigh_symbol,
    strip_ashare_code,
    symbol_to_order_book_id,
)


def test_strip_ashare_code():
    assert strip_ashare_code(" 600519.SH ") == "600519"


def test_normalize_ashare_symbol():
    assert normalize_ashare_symbol("600519") == "600519.SH"
    assert normalize_ashare_symbol("900901") == "900901.SH"
    assert normalize_ashare_symbol("920001") == "920001.BSE"
    assert normalize_ashare_symbol("830799") == "830799.BSE"
    assert normalize_ashare_symbol("000001") == "000001.SZ"


def test_ashare_symbol_to_tushare_ts_code():
    assert ashare_symbol_to_tushare_ts_code("830799") == "830799.BJ"
    assert ashare_symbol_to_tushare_ts_code("600519") == "600519.SH"


def test_normalize_ashare_symbol_bj_display():
    assert normalize_ashare_symbol_bj_display("920001") == "920001.BJ"
    assert normalize_ashare_symbol_bj_display("600519") == "600519.SH"


def test_order_book_id_roundtrip():
    assert order_book_id_to_newhigh_symbol("600519.XSHG") == "600519.SH"
    assert symbol_to_order_book_id("600519.SH") == "600519.XSHG"
    assert symbol_to_order_book_id("900901") == "900901.XSHG"
