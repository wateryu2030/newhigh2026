"""
统一数据库连接管理器

所有模块通过此模块获取数据库连接，避免重复实现。

使用示例:
    from lib.database import get_connection

    # 获取连接 (默认读写)
    conn = get_connection()

    # 仅单测/独立进程内验证只读语义；与 Gateway 同进程访问 quant_system 时请用默认 False
    conn = get_connection(read_only=True)

    # 确保表存在
    from lib.database import ensure_core_tables
    ensure_core_tables(conn)

Author: OpenClaw Agent
Version: 1.0.0
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import duckdb

# 类型别名
DBPath = Union[str, Path]
DuckDBConnection = duckdb.DuckDBPyConnection

# 项目根目录定位 (从 lib 向上 1 层)
_LIB_DIR: Path = Path(__file__).resolve().parent
_PROJECT_ROOT: Path = _LIB_DIR.parent

# 默认数据库路径
DEFAULT_DB_PATH: Path = _PROJECT_ROOT / "data" / "quant_system.duckdb"


def get_db_path() -> str:
    """
    统一数据库路径获取

    优先级:
    1. 环境变量 QUANT_DB_PATH
    2. 环境变量 QUANT_SYSTEM_DUCKDB_PATH（与 data_pipeline.duckdb_manager 一致）
    3. 环境变量 NEWHIGH_MARKET_DUCKDB_PATH
    4. 环境变量 NEWHIGH_DB_PATH
    5. 默认路径 data/quant_system.duckdb

    Returns:
        数据库文件绝对路径

    Example:
        >>> db_path = get_db_path()
        >>> print(db_path)
        '/path/to/newhigh/data/quant_system.duckdb'
    """
    # 环境变量 (与 data_pipeline.storage.duckdb_manager.get_db_path 对齐)
    env_path: str = (
        os.environ.get("QUANT_DB_PATH", "").strip()
        or os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_DB_PATH", "").strip()
    )
    if env_path:
        return env_path

    # 配置文件 (可选)
    config_file: Path = _PROJECT_ROOT / ".env"
    if config_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(config_file)
            env_path = (
                os.environ.get("QUANT_DB_PATH", "").strip()
                or os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
                or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
                or os.environ.get("NEWHIGH_DB_PATH", "").strip()
            )
            if env_path:
                return env_path
        except ImportError:
            pass

    # 默认路径
    return str(DEFAULT_DB_PATH)


def get_connection(read_only: bool = False) -> Optional[DuckDBConnection]:
    """
    获取数据库连接

    Args:
        read_only: 是否只读模式 (默认 False，允许写入)

    Returns:
        DuckDB 连接对象，失败返回 None

    Raises:
        Exception: 数据库连接失败

    Example:
        >>> conn = get_connection()
        >>> if conn:
        ...     result = conn.execute("SELECT 1").fetchone()
        ...     conn.close()
    """
    db_path: str = get_db_path()

    # 确保目录存在
    db_dir: Path = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    try:
        conn: DuckDBConnection = duckdb.connect(db_path, read_only=read_only)
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        return None


def ensure_core_tables(conn: DuckDBConnection) -> None:
    """
    确保核心表存在

    由 data 层在初始化时调用，避免各模块重复定义。

    Args:
        conn: DuckDB 连接

    Raises:
        Exception: 表创建失败

    表列表:
    - a_stock_basic: 股票基本信息
    - a_stock_daily: 日 K 线数据
    - a_stock_realtime: 实时行情
    - a_stock_fundflow: 资金流
    - a_stock_limitup: 涨停池
    - a_stock_longhubang: 龙虎榜
    - market_signals: 市场信号
    - news_items: 新闻数据
    - market_emotion: 市场情绪
    - sniper_candidates: 狙击候选
    - trade_signals: 交易信号

    Example:
        >>> conn = get_connection()
        >>> ensure_core_tables(conn)
        >>> conn.close()
    """

    tables: Dict[str, str] = {
        "a_stock_basic": """
            CREATE TABLE IF NOT EXISTS a_stock_basic (
                code VARCHAR PRIMARY KEY,
                name VARCHAR,
                sector VARCHAR,
                industry VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,

        "a_stock_daily": """
            CREATE TABLE IF NOT EXISTS a_stock_daily (
                code VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                PRIMARY KEY (code, date)
            )
        """,

        "a_stock_realtime": """
            CREATE TABLE IF NOT EXISTS a_stock_realtime (
                code VARCHAR,
                name VARCHAR,
                latest_price DOUBLE,
                change_pct DOUBLE,
                volume BIGINT,
                amount DOUBLE,
                snapshot_time TIMESTAMP
            )
        """,

        "a_stock_fundflow": """
            CREATE TABLE IF NOT EXISTS a_stock_fundflow (
                code VARCHAR,
                name VARCHAR,
                main_net_inflow DOUBLE,
                snapshot_date DATE,
                snapshot_time TIMESTAMP
            )
        """,

        "a_stock_limitup": """
            CREATE TABLE IF NOT EXISTS a_stock_limitup (
                code VARCHAR,
                name VARCHAR,
                price DOUBLE,
                change_pct DOUBLE,
                limit_up_times INTEGER,
                snapshot_time TIMESTAMP
            )
        """,

        "a_stock_longhubang": """
            CREATE TABLE IF NOT EXISTS a_stock_longhubang (
                code VARCHAR,
                name VARCHAR,
                lhb_date DATE,
                net_buy DOUBLE,
                buy_amount DOUBLE,
                sell_amount DOUBLE,
                snapshot_time TIMESTAMP
            )
        """,

        "market_signals": """
            CREATE TABLE IF NOT EXISTS market_signals (
                code VARCHAR NOT NULL,
                signal_type VARCHAR NOT NULL,
                score DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code, signal_type)
            )
        """,

        "news_items": """
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY,
                title VARCHAR NOT NULL,
                content TEXT,
                source_site VARCHAR,
                publish_time TIMESTAMP,
                sentiment_score DOUBLE,
                sentiment_label VARCHAR,
                url VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,

        "market_emotion": """
            CREATE TABLE IF NOT EXISTS market_emotion (
                trade_date DATE PRIMARY KEY,
                emotion_state VARCHAR,
                limit_up_count INTEGER,
                max_height INTEGER,
                total_volume DOUBLE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,

        # 与 data_pipeline duckdb_manager 一致，供 scanner 写入 (code, theme, sniper_score, confidence)
        "sniper_candidates": """
            CREATE TABLE IF NOT EXISTS sniper_candidates (
                code VARCHAR NOT NULL,
                theme VARCHAR,
                sniper_score DOUBLE,
                confidence DOUBLE,
                snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,

        "trade_signals": """
            CREATE TABLE IF NOT EXISTS trade_signals (
                id INTEGER PRIMARY KEY,
                code VARCHAR NOT NULL,
                signal_type VARCHAR NOT NULL,
                signal_score DOUBLE,
                confidence DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }

    for table_name, sql in tables.items():
        try:
            conn.execute(sql)
        except Exception as e:
            print(f"⚠️  创建表 {table_name} 失败：{e}")

    # 旧库 news_items 可能无 url，补列以便插入原文链接
    try:
        conn.execute("ALTER TABLE news_items ADD COLUMN url VARCHAR")
    except Exception:
        pass


def get_table_counts(conn: DuckDBConnection) -> Dict[str, int]:
    """
    获取所有表的记录数

    Args:
        conn: DuckDB 连接

    Returns:
        表名 -> 记录数 的字典

    Example:
        >>> conn = get_connection()
        >>> counts = get_table_counts(conn)
        >>> print(counts)
        {'a_stock_basic': 5000, 'news_items': 406, ...}
    """
    tables: List[str] = [
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

    counts: Dict[str, int] = {}
    for table in tables:
        try:
            result: Optional[tuple] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = result[0] if result else 0
        except Exception:
            counts[table] = 0

    return counts
