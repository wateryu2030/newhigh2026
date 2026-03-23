"""
数据库管理器单元测试

测试覆盖率目标：>80%

运行测试:
    pytest lib/tests/test_database.py -v
"""

from __future__ import annotations

import os
import sys
import pytest
import tempfile
from pathlib import Path

# 项目根目录 (从 lib/tests 向上 2 层)
_TESTS_DIR: Path = Path(__file__).resolve().parent
_LIB_DIR: Path = _TESTS_DIR.parent
_PROJECT_ROOT: Path = _LIB_DIR.parent

# 添加项目路径
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_LIB_DIR))

# 导入模块
try:
    from lib.database import (
        get_db_path,
        get_connection,
        ensure_core_tables,
        get_table_counts,
        DEFAULT_DB_PATH,
    )
    IMPORT_SUCCESS = True
    print(f"✅ 导入成功: {IMPORT_SUCCESS}")
except ImportError as e:
    print(f"⚠️  导入失败：{e}")
    IMPORT_SUCCESS = False

# 打印导入状态
print(f"测试文件导入状态: IMPORT_SUCCESS = {IMPORT_SUCCESS}")


class TestDatabaseManager:
    """数据库管理器测试类"""
    
    def test_get_db_path_default(self) -> None:
        """测试默认数据库路径"""
        print("测试开始: test_get_db_path_default")
        # 清除环境变量
        os.environ.pop("QUANT_DB_PATH", None)
        os.environ.pop("NEWHIGH_DB_PATH", None)
        
        db_path = get_db_path()
        
        assert isinstance(db_path, str)
        assert db_path.endswith("quant_system.duckdb")
        assert Path(db_path).is_absolute()
        print("测试通过: test_get_db_path_default")
    
    def test_get_db_path_from_env(self) -> None:
        """测试从环境变量获取数据库路径"""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            os.environ["QUANT_DB_PATH"] = tmp_path
            db_path = get_db_path()
            
            assert db_path == tmp_path
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    def test_get_connection_success(self) -> None:
        """测试成功获取数据库连接"""
        tmp_path = tempfile.mktemp(suffix=".duckdb")
        
        try:
            # 设置临时数据库
            os.environ["QUANT_DB_PATH"] = tmp_path
            
            conn = get_connection()
            
            assert conn is not None
            assert hasattr(conn, "execute")
            assert hasattr(conn, "close")
            
            # 测试连接可用
            result = conn.execute("SELECT 1").fetchone()
            assert result is not None
            assert result[0] == 1
            
            conn.close()
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    def test_get_connection_read_only(self) -> None:
        """测试获取只读连接"""
        tmp_path = tempfile.mktemp(suffix=".duckdb")
        
        try:
            os.environ["QUANT_DB_PATH"] = tmp_path
            
            # 先创建连接写入数据
            conn_rw = get_connection()
            assert conn_rw is not None
            conn_rw.execute("CREATE TABLE test (id INTEGER)")
            conn_rw.execute("INSERT INTO test VALUES (1)")
            conn_rw.close()
            
            # 获取只读连接
            conn_ro = get_connection(read_only=True)
            assert conn_ro is not None
            
            # 只读连接可以查询
            result = conn_ro.execute("SELECT * FROM test").fetchone()
            assert result is not None
            assert result[0] == 1
            
            # 只读连接不能写入 (应该抛出异常)
            with pytest.raises(Exception):
                conn_ro.execute("INSERT INTO test VALUES (2)")
            
            conn_ro.close()
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    def test_ensure_core_tables(self) -> None:
        """测试创建核心表"""
        tmp_path = tempfile.mktemp(suffix=".duckdb")
        
        try:
            os.environ["QUANT_DB_PATH"] = tmp_path
            
            conn = get_connection()
            assert conn is not None
            
            # 创建表
            ensure_core_tables(conn)
            
            # 验证表已创建
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [row[0] for row in tables]
            
            expected_tables = [
                "a_stock_basic",
                "a_stock_daily",
                "a_stock_realtime",
                "a_stock_fundflow",
                "a_stock_limitup",
                "a_stock_longhubang",
                "market_signals",
                "news_items",
                "market_emotion",
                "sniper_candidates",
                "trade_signals",
            ]
            
            for table in expected_tables:
                assert table in table_names, f"表 {table} 未创建"
            
            conn.close()
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    def test_get_table_counts(self) -> None:
        """测试获取表记录数"""
        tmp_path = tempfile.mktemp(suffix=".duckdb")
        
        try:
            os.environ["QUANT_DB_PATH"] = tmp_path
            
            conn = get_connection()
            assert conn is not None
            
            # 创建表
            ensure_core_tables(conn)
            
            # 获取计数
            counts = get_table_counts(conn)
            
            assert isinstance(counts, dict)
            assert len(counts) > 0
            
            # 验证所有预期表都有计数
            expected_tables = [
                "a_stock_basic",
                "a_stock_daily",
                "news_items",
                "trade_signals",
            ]
            
            for table in expected_tables:
                assert table in counts
                assert isinstance(counts[table], int)
                assert counts[table] >= 0
            
            # 插入测试数据
            conn.execute("INSERT INTO a_stock_basic (code, name) VALUES ('000001', '平安银行')")
            conn.execute("INSERT INTO a_stock_basic (code, name) VALUES ('600519', '贵州茅台')")
            
            # 重新获取计数
            counts = get_table_counts(conn)
            assert counts["a_stock_basic"] == 2
            
            conn.close()
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
    
    def test_connection_context_manager(self) -> None:
        """测试连接上下文管理"""
        tmp_path = tempfile.mktemp(suffix=".duckdb")
        
        try:
            os.environ["QUANT_DB_PATH"] = tmp_path
            
            conn = get_connection()
            assert conn is not None
            
            # DuckDB 的 with 会在退出时关闭连接
            with conn:
                result = conn.execute("SELECT 1").fetchone()
                assert result[0] == 1
                # 连接在 with 块内可用
            
            # with 块后连接已关闭，需要重新获取
            conn = get_connection()
            assert conn is not None
            result = conn.execute("SELECT 2").fetchone()
            assert result[0] == 2
            
            conn.close()
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


class TestDatabaseIntegration:
    """数据库集成测试"""
    
    def test_full_workflow(self) -> None:
        """测试完整工作流程"""
        tmp_path = tempfile.mktemp(suffix=".duckdb")
        
        try:
            os.environ["QUANT_DB_PATH"] = tmp_path
            
            # 1. 获取连接
            conn = get_connection()
            assert conn is not None
            
            # 2. 创建表
            ensure_core_tables(conn)
            
            # 3. 插入测试数据
            conn.execute("""
                INSERT INTO a_stock_basic (code, name, sector)
                VALUES ('000001', '平安银行', '金融'),
                       ('600519', '贵州茅台', '消费')
            """)
            
            # 4. 查询数据
            result = conn.execute("""
                SELECT code, name FROM a_stock_basic
                WHERE sector = '金融'
            """).fetchall()
            
            assert len(result) == 1
            assert result[0][0] == "000001"
            assert result[0][1] == "平安银行"
            
            # 5. 获取统计
            counts = get_table_counts(conn)
            assert counts["a_stock_basic"] == 2
            
            # 6. 清理
            conn.close()
            
        finally:
            os.environ.pop("QUANT_DB_PATH", None)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
