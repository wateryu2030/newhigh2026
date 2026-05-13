"""Tests for rumor_capture.fetcher core logic (keyword classification, dedup, source parsing)."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

# Adjust path so we can import the package
_PKG_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_PKG_SRC))

from rumor_capture.fetcher import (
    is_rumour_related,
    classify_rumor_type,
    extract_keywords,
    compute_sentiment_score,
    content_hash,
    match_stock_code,
    ensure_company_rumors_table,
    write_records,
    dedup_records,
    GUBA_ARTICLE_URL,
)


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """Create a temporary DuckDB database with company_rumors table."""
    db_file = tmp_path / "test_rumors.duckdb"
    conn = duckdb.connect(str(db_file))
    ensure_company_rumors_table(conn)
    return conn


# ---------------------------------------------------------------------------
#  content_hash
# ---------------------------------------------------------------------------


class TestContentHash:
    def test_basic_hash(self):
        """Same title+content should produce same hash."""
        h1 = content_hash("标题", "内容")
        h2 = content_hash("标题", "内容")
        assert h1 == h2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        h1 = content_hash("标题", "内容A")
        h2 = content_hash("标题", "内容B")
        assert h1 != h2

    def test_none_values(self):
        """None values should be handled gracefully."""
        h = content_hash(None, None)
        assert isinstance(h, str)
        assert len(h) == 32


# ---------------------------------------------------------------------------
#  is_rumour_related
# ---------------------------------------------------------------------------


class TestIsRumourRelated:
    def test_rumour_keyword_in_title(self):
        assert is_rumour_related("公司传闻", "一些内容") is True

    def test_clarification_keyword_in_content(self):
        assert is_rumour_related("标题", "公司发布澄清公告") is True

    def test_bullish_keyword_in_content(self):
        assert is_rumour_related("标题", "公司计划回购股票") is True

    def test_no_keyword(self):
        assert is_rumour_related("普通标题", "普通内容") is False

    def test_empty_strings(self):
        assert is_rumour_related("", "") is False


# ---------------------------------------------------------------------------
#  classify_rumor_type
# ---------------------------------------------------------------------------


class TestClassifyRumorType:
    def test_clarification(self):
        """澄清 keyword should return 辟谣."""
        assert classify_rumor_type("公司澄清公告", "") == "辟谣"

    def test_bullish(self):
        """利好 keywords should return 利好."""
        assert classify_rumor_type("公司回购计划", "") == "利好"

    def test_bearish(self):
        """利空 keywords should return 利空."""
        assert classify_rumor_type("大股东减持", "") == "利空"

    def test_bullish_and_bearish(self):
        """Both bullish and bearish should return 中性."""
        result = classify_rumor_type("公司回购应对减持", "")
        assert result == "中性"

    def test_rumour_keyword_only(self):
        """Rumour keyword without bullish/bearish should return 中性."""
        assert classify_rumor_type("市场传闻", "") == "中性"

    def test_no_match(self):
        """No matching keywords returns 其他."""
        assert classify_rumor_type("普通新闻标题", "") == "其他"

    def test_clarification_overrides_bullish(self):
        """澄清 should take priority over bullish keywords."""
        assert classify_rumor_type("公司澄清回购传闻", "") == "辟谣"

    def test_clarification_overrides_bearish(self):
        """澄清 should take priority over bearish keywords."""
        assert classify_rumor_type("公司澄清减持传闻", "") == "辟谣"


# ---------------------------------------------------------------------------
#  extract_keywords
# ---------------------------------------------------------------------------


class TestExtractKeywords:
    def test_single_keyword(self):
        kw = extract_keywords("市场传闻", "")
        assert "传闻" in kw

    def test_multiple_keywords(self):
        kw = extract_keywords("公司澄清回购传闻", "")
        assert "传闻" in kw
        assert "澄清" in kw
        assert "回购" in kw

    def test_no_keywords(self):
        assert extract_keywords("普通标题", "") == ""

    def test_case_insensitivity(self):
        """Keywords matching should be case insensitive."""
        kw = extract_keywords("RUMOR", "")
        # "rumor" is lowercase in the keyword list
        assert "rumor" in kw or "rumour" in kw

    def test_keywords_sorted(self):
        kw = extract_keywords("回购减持", "")
        parts = kw.split(",")
        assert parts == sorted(parts)


# ---------------------------------------------------------------------------
#  compute_sentiment_score
# ---------------------------------------------------------------------------


class TestComputeSentimentScore:
    def test_bullish_score(self):
        """Bullish keywords should give positive score."""
        score = compute_sentiment_score("公司回购增持", "")
        assert score > 0

    def test_bearish_score(self):
        """Bearish keywords should give negative score."""
        score = compute_sentiment_score("公司减持亏损", "")
        assert score < 0

    def test_clarification_boost(self):
        """澄清 should add a small positive boost."""
        score = compute_sentiment_score("澄清", "")
        assert score > 0

    def test_no_keywords(self):
        assert compute_sentiment_score("普通标题", "") == 0.0

    def test_clamp_positive(self):
        """Score should be clamped to max 1.0."""
        # Multiple bullish keywords
        score = compute_sentiment_score(
            "回购增持收购要约溢价收购重大利好",
            "",
        )
        assert score <= 1.0

    def test_clamp_negative(self):
        """Score should be clamped to min -1.0."""
        score = compute_sentiment_score(
            "减持亏损暴雷违约立案调查处罚",
            "",
        )
        assert score >= -1.0


# ---------------------------------------------------------------------------
#  match_stock_code
# ---------------------------------------------------------------------------


class TestMatchStockCode:
    def test_match_six_digit_code_at_start(self):
        """6-digit stock code at start of string should be matched."""
        stock_map = {}
        result = match_stock_code("600519 今日大涨", "内容", stock_map)
        assert result == "600519"

    def test_match_prefix_60_with_spaces(self):
        """60xxxx code surrounded by spaces should be matched."""
        result = match_stock_code("关注 600519 大涨", "", {})
        assert result == "600519"

    def test_match_prefix_00_with_spaces(self):
        """00xxxx code surrounded by spaces should be matched."""
        result = match_stock_code("关注 000858 大跌", "", {})
        assert result == "000858"

    def test_match_prefix_30_with_spaces(self):
        """30xxxx code surrounded by spaces should be matched."""
        result = match_stock_code("关注 300750 波动", "", {})
        assert result == "300750"

    def test_match_at_end_of_string(self):
        """Code at end of string should be matched."""
        result = match_stock_code("股票 600519", "", {})
        assert result == "600519"

    def test_match_stock_name(self):
        """Stock name from map should be matched."""
        stock_map = {"贵州茅台": "600519"}
        result = match_stock_code("", "贵州茅台最新消息", stock_map)
        assert result == "600519"

    def test_no_match(self):
        """No recognizable code or name should return None."""
        result = match_stock_code("普通新闻标题", "一些内容", {})
        assert result is None

    def test_code_in_content(self):
        """Code in content field should also be matched."""
        result = match_stock_code("标题", "代码 600519 出现在内容中", {})
        assert result == "600519"


# ---------------------------------------------------------------------------
#  DB write/read for company_rumors
# ---------------------------------------------------------------------------


class TestDBWriteRead:
    def test_write_and_read_back(self, db_conn):
        """Write records then read them back."""
        records = [
            {
                "stock_code": "600519",
                "title": "市场传闻",
                "content": "贵州茅台可能涨价",
                "source": "雪球",
                "source_url": "https://xueqiu.com/123",
                "rumor_type": "利好",
                "publish_time": "2025-01-01 10:00:00",
                "keywords": "传闻",
                "sentiment_score": 0.3,
            }
        ]
        count = write_records(records, db_conn)
        assert count == 1

        result = db_conn.execute(
            "SELECT stock_code, rumor_type, source FROM company_rumors"
        ).fetchall()
        assert len(result) == 1
        assert result[0][0] == "600519"
        assert result[0][1] == "利好"
        assert result[0][2] == "雪球"

    def test_write_empty(self, db_conn):
        """Writing empty list returns 0."""
        assert write_records([], db_conn) == 0

    def test_dry_run_does_not_write(self, db_conn):
        """Dry-run should not insert data."""
        records = [
            {
                "stock_code": "600519",
                "title": "测试",
                "content": "内容",
                "source": "雪球",
                "source_url": "",
                "rumor_type": "中性",
                "publish_time": "2025-01-01",
                "keywords": "",
                "sentiment_score": 0.0,
            }
        ]
        count = write_records(records, db_conn, dry_run=True)
        assert count == 1

        result = db_conn.execute(
            "SELECT COUNT(*) FROM company_rumors"
        ).fetchone()[0]
        assert result == 0

    def test_write_multiple(self, db_conn):
        """Writing multiple records."""
        records = [
            {
                "stock_code": "600519",
                "title": "传闻A",
                "content": "内容A",
                "source": "雪球",
                "source_url": "",
                "rumor_type": "利好",
                "publish_time": "2025-01-01",
                "keywords": "传闻",
                "sentiment_score": 0.3,
            },
            {
                "stock_code": "000858",
                "title": "传闻B",
                "content": "内容B",
                "source": "东方财富股吧",
                "source_url": "",
                "rumor_type": "利空",
                "publish_time": "2025-01-02",
                "keywords": "减持",
                "sentiment_score": -0.3,
            },
        ]
        count = write_records(records, db_conn)
        assert count == 2

        total = db_conn.execute(
            "SELECT COUNT(*) FROM company_rumors"
        ).fetchone()[0]
        assert total == 2


# ---------------------------------------------------------------------------
#  dedup_records
# ---------------------------------------------------------------------------


class TestDedupRecords:
    def test_dedup_within_batch(self, db_conn):
        """Duplicate records within the same batch should be deduped."""
        records = [
            {
                "stock_code": "600519",
                "title": "市场传闻",
                "content": "内容",
                "source": "雪球",
                "source_url": "",
                "rumor_type": "利好",
                "publish_time": "2025-01-01",
                "keywords": "传闻",
                "sentiment_score": 0.3,
            },
            {
                "stock_code": "600519",
                "title": "市场传闻",
                "content": "内容",
                "source": "雪球",
                "source_url": "",
                "rumor_type": "利好",
                "publish_time": "2025-01-01",
                "keywords": "传闻",
                "sentiment_score": 0.3,
            },
        ]
        result = dedup_records(records, "雪球", db_conn)
        assert len(result) == 1

    def test_dedup_against_db(self, db_conn):
        """Records that already exist in DB should be filtered out."""
        # Write a record first
        record = {
            "stock_code": "600519",
            "title": "已有记录",
            "content": "已存在的内容",
            "source": "雪球",
            "source_url": "",
            "rumor_type": "利好",
            "publish_time": "2025-01-01",
            "keywords": "传闻",
            "sentiment_score": 0.3,
        }
        write_records([record], db_conn)

        # Try to dedup same record
        deduped = dedup_records([record], "雪球", db_conn)
        assert len(deduped) == 0

    def test_no_duplicates(self, db_conn):
        """Records not in DB should all pass through."""
        records = [
            {
                "stock_code": "600519",
                "title": "新记录",
                "content": "新内容",
                "source": "雪球",
                "source_url": "",
                "rumor_type": "利好",
                "publish_time": "2025-01-01",
                "keywords": "传闻",
                "sentiment_score": 0.3,
            }
        ]
        deduped = dedup_records(records, "雪球", db_conn)
        assert len(deduped) == 1

    def test_empty_input(self, db_conn):
        """Empty input returns empty list."""
        assert dedup_records([], "雪球", db_conn) == []


# ---------------------------------------------------------------------------
#  GUBA_ARTICLE_URL format
# ---------------------------------------------------------------------------


class TestGubaUrl:
    def test_url_format(self):
        """Verify GUBA_ARTICLE_URL format."""
        url = GUBA_ARTICLE_URL.format(code="600519", artid="12345")
        assert "600519" in url
        assert "12345" in url
        assert url == "https://guba.eastmoney.com/news,600519,12345.html"
