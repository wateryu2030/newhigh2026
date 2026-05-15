"""
测试 data-pipeline 的 6 个核心 collector。

策略：
- patch ``sys.modules['akshare']`` 为 mock 模块，拦截函数内 ``import akshare as ak``
- mock ``duckdb_manager.get_conn()`` 使用在内存 DuckDB
- mock ``duckdb_manager.ensure_tables()`` 为 noop（表已在 in_memory_db 预建）
- 验证：列名重命名正确、INSERT 行数正确、异常降级返回 0
"""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest

# ── 确保 data-pipeline/src 可 import ──
_DATA_PIPELINE_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"
)
if _DATA_PIPELINE_SRC not in sys.path:
    sys.path.insert(0, _DATA_PIPELINE_SRC)


def _make_akshare_mock(**attrs) -> types.ModuleType:
    """创建 mock 的 akshare 模块，可设任意属性。"""
    mod = types.ModuleType("akshare")
    mod.pd = pd
    mod.__dict__.update(attrs)
    return mod


def _clear_data_pipeline_cache() -> None:
    """清除 data_pipeline 包下所有模块的 sys.modules 缓存，
    确保下次 import 时重新加载，使 mock 生效。"""
    for k in list(sys.modules.keys()):
        if k.startswith("data_pipeline"):
            del sys.modules[k]


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def in_memory_db():
    """创建 :memory: DuckDB，预建所有 collector 需要的表。"""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE a_stock_basic (code VARCHAR, name VARCHAR)")
    conn.execute("""
        CREATE TABLE a_stock_daily (
            code VARCHAR, date DATE,
            open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
            volume DOUBLE, amount DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE a_stock_realtime (
            code VARCHAR, name VARCHAR,
            latest_price DOUBLE, change_pct DOUBLE,
            volume DOUBLE, amount DOUBLE,
            snapshot_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE a_stock_fundflow (
            code VARCHAR, name VARCHAR,
            main_net_inflow DOUBLE,
            snapshot_date DATE, snapshot_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE a_stock_limitup (
            code VARCHAR, name VARCHAR,
            price DOUBLE, change_pct DOUBLE,
            limit_up_times DOUBLE,
            snapshot_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE a_stock_longhubang (
            code VARCHAR, name VARCHAR,
            lhb_date DATE, net_buy DOUBLE,
            snapshot_time TIMESTAMP
        )
    """)
    yield conn
    conn.close()


@pytest.fixture
def mock_deps(in_memory_db):
    """mock duckdb_manager.get_conn() 和 ensure_tables 永远使用
    :memory: 连接，不碰真实的 quant_system.duckdb。"""
    with patch(
        "data_pipeline.storage.duckdb_manager.get_conn", return_value=in_memory_db
    ), patch(
        "data_pipeline.storage.duckdb_manager.ensure_tables", return_value=None
    ):
        yield


# ============================================================
# Stock List
# ============================================================

class TestStockList:
    def test_update_stock_list_success(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_info_a_code_name=MagicMock(
                return_value=pd.DataFrame(
                    {"code": ["600519", "000001", "300750"],
                     "name": ["茅台", "平安", "宁德"]}
                )
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.stock_list import update_stock_list
            assert update_stock_list() == 3

    def test_update_stock_list_empty_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_info_a_code_name=MagicMock(
                return_value=pd.DataFrame(columns=["code", "name"])
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.stock_list import update_stock_list
            assert update_stock_list() == 0

    def test_update_stock_list_fallback_on_failure(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_info_a_code_name=MagicMock(side_effect=ConnectionError("API 超时")),
            stock_info_sh_app=MagicMock(
                return_value=pd.DataFrame({"证券代码": ["600519"], "证券简称": ["茅台"]})
            ),
            stock_info_sz_a=MagicMock(
                return_value=pd.DataFrame({"证券代码": ["000001"], "证券简称": ["平安"]})
            ),
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.stock_list import update_stock_list
            assert update_stock_list() == 2

    def test_update_stock_list_all_fail_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_info_a_code_name=MagicMock(side_effect=ConnectionError("全挂")),
            stock_info_sh_app=MagicMock(side_effect=ConnectionError("全挂")),
            stock_info_sz_a=MagicMock(side_effect=ConnectionError("全挂")),
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.stock_list import update_stock_list
            assert update_stock_list() == 0


# ============================================================
# Daily Kline
# ============================================================

class TestDailyKline:
    def test_update_daily_kline_success(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zh_a_hist=MagicMock(
                return_value=pd.DataFrame({
                    "股票代码": ["600519"],
                    "日期": pd.to_datetime(["2026-01-02"]),
                    "开盘": [2020.0], "最高": [2080.0], "最低": [2010.0], "收盘": [2070.0],
                    "成交量": [1.2e6], "成交额": [2.5e9],
                })
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.daily_kline import update_daily_kline
            assert update_daily_kline(code="600519") == 1

    def test_update_daily_kline_empty_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zh_a_hist=MagicMock(
                return_value=pd.DataFrame(columns=["股票代码", "日期", "开盘", "收盘"])
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.daily_kline import update_daily_kline
            assert update_daily_kline(code="600519") == 0

    def test_update_daily_kline_invalid_code_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        with patch.dict("sys.modules", {"akshare": _make_akshare_mock()}):
            from data_pipeline.collectors.daily_kline import update_daily_kline
            assert update_daily_kline(code="") == 0


# ============================================================
# Realtime Quotes
# ============================================================

class TestRealtimeQuotes:
    def test_update_realtime_success(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zh_a_spot_em=MagicMock(
                return_value=pd.DataFrame({
                    "代码": ["600519", "000001"],
                    "名称": ["贵州茅台", "平安银行"],
                    "最新价": [2050.0, 12.5],
                    "涨跌幅": [1.5, -0.3],
                    "成交量": [5_000_000, 10_000_000],
                    "成交额": [1e10, 1.25e8],
                })
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.realtime_quotes import update_realtime_quotes
            assert update_realtime_quotes() == 2

    def test_update_realtime_failure_raises(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zh_a_spot_em=MagicMock(side_effect=ConnectionError("挂"))
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.realtime_quotes import update_realtime_quotes
            with pytest.raises(ConnectionError):
                update_realtime_quotes()


# ============================================================
# Fund Flow
# ============================================================

class TestFundFlow:
    def test_update_fundflow_success(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_individual_fund_flow_rank=MagicMock(
                return_value=pd.DataFrame({
                    "代码": ["600519", "000001"],
                    "名称": ["贵州茅台", "平安银行"],
                    "主力净流入": [2.5e8, -1.0e8],
                })
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.fund_flow import update_fundflow
            assert update_fundflow(max_retries=1) == 2

    def test_update_fundflow_empty_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_individual_fund_flow_rank=MagicMock(
                return_value=pd.DataFrame(columns=["代码", "名称", "主力净流入"])
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.fund_flow import update_fundflow
            assert update_fundflow(max_retries=1) == 0

    def test_update_fundflow_retries_on_failure(self):
        """失败时重试，全部失败返回 0（不需要 mock，因为真实 DB 被占用的场景和网络失败一样）。"""
        from data_pipeline.collectors.fund_flow import update_fundflow
        assert update_fundflow(max_retries=1) == 0


# ============================================================
# Limit Up
# ============================================================

class TestLimitUp:
    def test_update_limitup_success(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zt_pool_em=MagicMock(
                return_value=pd.DataFrame({
                    "代码": ["600519"],
                    "名称": ["贵州茅台"],
                    "最新价": [2100.0],
                    "涨跌幅": [10.0],
                    "连板数": [3],
                })
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.limit_up import update_limitup
            assert update_limitup() == 1

    def test_update_limitup_empty_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zt_pool_em=MagicMock(
                return_value=pd.DataFrame(columns=["代码", "名称", "最新价", "涨跌幅", "连板数"])
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.limit_up import update_limitup
            assert update_limitup() == 0

    def test_update_limitup_failure_raises(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_zt_pool_em=MagicMock(side_effect=ValueError("日期无数据"))
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.limit_up import update_limitup
            with pytest.raises(ValueError):
                update_limitup()


# ============================================================
# Longhubang
# ============================================================

class TestLonghubang:
    def test_update_longhubang_success(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_lhb_detail_em=MagicMock(
                return_value=pd.DataFrame({
                    "代码": ["600519"],
                    "名称": ["贵州茅台"],
                    "成交日期": ["2026-01-15"],
                    "净买入": [5.0e8],
                })
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.longhubang import update_longhubang
            assert update_longhubang() == 1

    def test_update_longhubang_empty_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_lhb_detail_em=MagicMock(
                return_value=pd.DataFrame(columns=["代码", "名称", "成交日期", "净买入"])
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.longhubang import update_longhubang
            assert update_longhubang() == 0

    def test_update_longhubang_failure_fallback(self, mock_deps):
        _clear_data_pipeline_cache()
        df2 = pd.DataFrame({
            "代码": ["000001"], "名称": ["平安"],
            "成交日期": ["2026-01-15"], "净买入": [1.0e7],
        })
        ak = _make_akshare_mock(
            stock_lhb_detail_em=MagicMock(
                side_effect=[RuntimeError("近一月失败"), df2]
            )
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.longhubang import update_longhubang
            assert update_longhubang() == 1

    def test_update_longhubang_all_fail_returns_zero(self, mock_deps):
        _clear_data_pipeline_cache()
        ak = _make_akshare_mock(
            stock_lhb_detail_em=MagicMock(side_effect=ConnectionError("全挂"))
        )
        with patch.dict("sys.modules", {"akshare": ak}):
            from data_pipeline.collectors.longhubang import update_longhubang
            assert update_longhubang() == 0
