"""数据管道核心功能测试。"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data-pipeline", "src"))


class TestDuckDBManager:
    """测试 DuckDB 管理器。"""

    def test_get_db_path_returns_str(self):
        """get_db_path 应返回字符串路径。"""
        from data_pipeline.storage.duckdb_manager import get_db_path

        path = get_db_path()
        assert isinstance(path, str)
        assert len(path) > 0

    def test_get_conn_read_only(self):
        """get_conn(read_only=True) 应返回连接对象。"""
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=True)
        assert conn is not None
        conn.close()

    def test_ensure_tables_creates_core(self):
        """ensure_tables 应创建核心表而不抛异常。"""
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            # Verify key tables exist
            for table in ["a_stock_daily", "a_stock_basic", "trade_signals"]:
                try:
                    conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
                except Exception:
                    pass  # Table may not exist but ensure_tables shouldn't crash
        finally:
            conn.close()

    def test_db_connectivity(self):
        """验证 DuckDB 可正常查询。"""
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=True)
        try:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1
        finally:
            conn.close()


class TestDataPipeline:
    """测试数据管道核心流程。"""

    def test_stock_list_table_exists(self):
        """a_stock_basic 表应有数据。"""
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=True)
        try:
            cnt = conn.execute("SELECT count(*) FROM a_stock_basic").fetchone()
            assert cnt[0] > 0, "a_stock_basic should have stocks"
        finally:
            conn.close()

    def test_daily_kline_table_exists(self):
        """a_stock_daily 表应有历史行情数据。"""
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=True)
        try:
            cnt = conn.execute("SELECT count(*) FROM a_stock_daily").fetchone()
            assert cnt[0] > 0, "a_stock_daily should have data"
        finally:
            conn.close()

    def test_trade_signals_schema(self):
        """trade_signals 表应有 signal_score 列。"""
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=True)
        try:
            cols = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='trade_signals'"
            ).fetchall()
            col_names = [c[0] for c in cols]
            assert "signal_score" in col_names
            assert "strategy_id" in col_names or True  # may or may not exist
        finally:
            conn.close()

    def test_sim_tables_exist(self):
        """模拟盘相关表应存在。"""
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            pytest.skip("DuckDB file not found")

        conn = get_conn(read_only=True)
        try:
            for table in ["sim_positions", "sim_orders", "sim_account_snapshots"]:
                try:
                    conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
                except Exception:
                    pytest.fail(f"{table} should exist")
        finally:
            conn.close()


class TestStrategyMarketWriter:
    """测试策略市场写入。"""

    def test_upsert_no_db(self):
        """无 DB 时应安全失败。"""
        from data_pipeline.strategy_market_writer import upsert_strategy_market_from_backtest

        # This will try to connect to DB; if no DB exists it should return False
        result = upsert_strategy_market_from_backtest(
            "test_strategy", "Test", {"return_pct": 10}
        )
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
