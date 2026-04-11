"""股票问答：实体提取纯函数测试（不依赖 DuckDB）。"""

import pytest

from gateway.endpoints_stock_qa import (
    extract_name_matches,
    extract_six_digit_codes,
)


def test_extract_six_digit_codes_basic():
    assert extract_six_digit_codes("关注600519和000001走势") == ["600519", "000001"]


def test_extract_six_digit_codes_no_overlap():
    assert extract_six_digit_codes("x1234567y") == []  # 7-digit block, no isolated 6


def test_extract_name_matches_longest_first():
    text = "招商银行与银行板块"
    names_sorted = [
        ("银行板块", "000001"),
        ("招商银行", "600036"),
        ("银行", "999999"),
    ]
    m = extract_name_matches(text, names_sorted)
    names_found = [x[0] for x in m]
    assert "招商银行" in names_found
    assert "银行板块" in names_found


def test_extract_name_matches_overlap_blocks_short_inside_long():
    text = "贵州茅台发布财报"
    names_sorted = [("贵州茅台", "600519"), ("茅台", "600519")]
    m = extract_name_matches(text, names_sorted)
    assert len(m) >= 1
    assert m[0][0] == "贵州茅台"


def test_extract_name_matches_respects_used_mask():
    text = "AA"
    used = [True, True]
    m = extract_name_matches("xx", [("xx", "1")], used=used)
    assert m == []
