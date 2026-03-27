"""
统一 DuckDB 数据仓库（唯一事实源）

- **路径**：``get_db_path()`` / ``get_conn()`` — 环境变量优先级与仓库根 ``.env`` 见 ``get_db_path`` 文档。
- **DDL**：``ensure_tables(conn)`` — 全项目请使用本函数，勿在 ``lib.database`` 等处重复建表语句。
- **兼容**：``lib.database`` 仅将 ``get_connection`` / ``ensure_core_tables`` 代理到本模块。

库文件默认 ``<repo>/data/quant_system.duckdb``；与 Gateway、管道、脚本共用同一文件时须统一使用 ``read_only=False``（同进程勿混只读连接）。
"""

from __future__ import annotations

import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))  # data_pipeline
_DATA_PIPELINE_ROOT = os.path.dirname(_PIPELINE_ROOT)  # data-pipeline
_NEWHIGH_ROOT = os.path.dirname(_DATA_PIPELINE_ROOT)  # newhigh
DEFAULT_DB_PATH = os.path.join(_NEWHIGH_ROOT, "data", "quant_system.duckdb")


def _db_path_from_environ() -> str:
    """与 lib.database.get_db_path 相同优先级，避免管道脚本与 Gateway/旧模块各连各库。"""
    return (
        os.environ.get("QUANT_DB_PATH", "").strip()
        or os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_DB_PATH", "").strip()
    )


def get_db_path() -> str:
    """
    统一 DuckDB 文件路径。

    优先级：QUANT_DB_PATH → QUANT_SYSTEM_DUCKDB_PATH → NEWHIGH_MARKET_DUCKDB_PATH → NEWHIGH_DB_PATH；
    若均未设置，尝试加载仓库根目录 ``.env`` 后再读上述变量（与 lib.database 一致）；
    最后回落到 ``<repo>/data/quant_system.duckdb``。
    """
    p = _db_path_from_environ()
    if p:
        return p
    env_file = os.path.join(_NEWHIGH_ROOT, ".env")
    if os.path.isfile(env_file):
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file)
        except ImportError:
            pass
    p = _db_path_from_environ()
    if p:
        return p
    return DEFAULT_DB_PATH


def get_conn(read_only: bool = False):
    """
    连接统一 DuckDB 文件。

    注意：DuckDB 在同一进程内对**同一数据库文件**不能混用 read_only=True 与 False。
    FastAPI Gateway 因审计中间件会 read_only=False 写入 audit_log，故 Gateway 内其它路由
    也应使用 read_only=False（只读 SQL 仍可执行），否则会触发
    \"Can't open a connection to same database file with a different configuration...\".
    """
    path = get_db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    import duckdb

    return duckdb.connect(path, read_only=read_only)


def ensure_tables(conn) -> None:
    """创建本仓 DuckDB 所需全部表（若不存在）；旧库缺列时由下方 ALTER 补齐。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS a_stock_basic (
            code VARCHAR PRIMARY KEY,
            name VARCHAR,
            sector VARCHAR,
            industry VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
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
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS a_stock_realtime (
            code VARCHAR,
            name VARCHAR,
            latest_price DOUBLE,
            change_pct DOUBLE,
            volume BIGINT,
            amount DOUBLE,
            snapshot_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS a_stock_fundflow (
            code VARCHAR,
            name VARCHAR,
            main_net_inflow DOUBLE,
            snapshot_date DATE,
            snapshot_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS a_stock_limitup (
            code VARCHAR,
            name VARCHAR,
            price DOUBLE,
            change_pct DOUBLE,
            limit_up_times INTEGER,
            snapshot_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS a_stock_longhubang (
            code VARCHAR,
            name VARCHAR,
            lhb_date DATE,
            net_buy DOUBLE,
            buy_amount DOUBLE,
            sell_amount DOUBLE,
            snapshot_time TIMESTAMP
        )
    """)
    # 市场扫描器 + AI + 策略 输出表（统一终端方案）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_signals (
            code VARCHAR NOT NULL,
            signal_type VARCHAR NOT NULL,
            score DOUBLE,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_emotion_state (
            state VARCHAR NOT NULL,
            stage VARCHAR,
            limit_up_count INTEGER,
            score DOUBLE,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hotmoney_signals (
            code VARCHAR,
            seat_type VARCHAR,
            win_rate DOUBLE,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sector_strength (
            sector VARCHAR NOT NULL,
            strength DOUBLE,
            rank INTEGER,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_signals (
            code VARCHAR NOT NULL,
            signal VARCHAR NOT NULL,
            confidence DOUBLE,
            target_price DOUBLE,
            stop_loss DOUBLE,
            strategy_id VARCHAR,
            signal_score DOUBLE,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 策略市场：回测结果写入，供前端策略市场页展示
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_market (
            strategy_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            return_pct DOUBLE,
            sharpe_ratio DOUBLE,
            max_drawdown DOUBLE,
            status VARCHAR DEFAULT 'active',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 情绪周期每日指标 + 状态（三套核心算法）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_emotion (
            trade_date DATE PRIMARY KEY,
            limitup_count INTEGER,
            max_height INTEGER,
            market_volume DOUBLE,
            emotion_state VARCHAR,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 游资席位胜率（席位名、胜率、平均收益）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS top_hotmoney_seats (
            seat_name VARCHAR PRIMARY KEY,
            trade_count INTEGER,
            win_rate DOUBLE,
            avg_return DOUBLE,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 主线题材（板块/行业 + 强度排名）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS main_themes (
            sector VARCHAR NOT NULL,
            total_volume DOUBLE,
            rank INTEGER,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 龙虎榜扩展：支持席位维度（可选）
    try:
        conn.execute("ALTER TABLE a_stock_longhubang ADD COLUMN seat_name VARCHAR")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE a_stock_longhubang ADD COLUMN buy_amount DOUBLE")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE a_stock_longhubang ADD COLUMN sell_amount DOUBLE")
    except Exception:
        pass
    for _sql in (
        "ALTER TABLE a_stock_basic ADD COLUMN sector VARCHAR",
        "ALTER TABLE a_stock_basic ADD COLUMN industry VARCHAR",
        "ALTER TABLE a_stock_basic ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    ):
        try:
            conn.execute(_sql)
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE trade_signals ADD COLUMN signal_score DOUBLE")
    except Exception:
        pass
    # 游资狙击候选池（Sniper Score > 0.7）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sniper_candidates (
            code VARCHAR NOT NULL,
            theme VARCHAR,
            sniper_score DOUBLE,
            confidence DOUBLE,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 旧库由 lib.database 建过另一套 sniper_candidates（无 theme/confidence/snapshot_time），补列否则 Gateway 查询报错返回空
    for _col_sql in (
        "ALTER TABLE sniper_candidates ADD COLUMN theme VARCHAR",
        "ALTER TABLE sniper_candidates ADD COLUMN confidence DOUBLE",
        "ALTER TABLE sniper_candidates ADD COLUMN snapshot_time TIMESTAMP",
    ):
        try:
            conn.execute(_col_sql)
        except Exception:
            pass
    # 统一运行核心：系统状态（system_core 写入）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_status (
            data_status VARCHAR,
            scanner_status VARCHAR,
            ai_status VARCHAR,
            strategy_status VARCHAR,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # OpenClaw：Skill 调用统计（单行）、进化任务记录
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_stats (
            call_count INTEGER DEFAULT 0,
            last_call_time TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evolution_tasks (
            task_id VARCHAR PRIMARY KEY,
            status VARCHAR NOT NULL,
            result VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 日K/标的/新闻（与 data_engine 共用，与 astock 复制脚本结构一致）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_bars (
            order_book_id VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            adjust_type VARCHAR NOT NULL DEFAULT 'qfq',
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            total_turnover DOUBLE,
            adjust_factor DOUBLE DEFAULT 1.0,
            PRIMARY KEY (order_book_id, trade_date, adjust_type)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            order_book_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            name VARCHAR,
            market VARCHAR,
            listed_date VARCHAR,
            de_listed_date VARCHAR,
            type VARCHAR,
            updated_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol VARCHAR,
            source_site VARCHAR,
            source VARCHAR,
            title VARCHAR,
            content VARCHAR,
            url VARCHAR,
            keyword VARCHAR,
            tag VARCHAR,
            publish_time VARCHAR,
            sentiment_score DOUBLE,
            sentiment_label VARCHAR
        )
    """)
    # 审计日志：API 请求记录（认证与审计）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            method VARCHAR,
            path VARCHAR,
            client_host VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 风控规则：可配置单票上限、回撤、敞口等
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_rules (
            id INTEGER PRIMARY KEY,
            rule_type VARCHAR NOT NULL,
            value DOUBLE NOT NULL,
            enabled BOOLEAN DEFAULT true,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 模拟盘：持仓、订单、资金快照
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_positions (
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            qty DOUBLE NOT NULL,
            avg_price DOUBLE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code, side)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_orders (
            id INTEGER PRIMARY KEY,
            code VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            qty DOUBLE NOT NULL,
            price DOUBLE,
            status VARCHAR DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            filled_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_account_snapshots (
            snapshot_time TIMESTAMP PRIMARY KEY,
            cash DOUBLE NOT NULL,
            equity DOUBLE NOT NULL,
            total_assets DOUBLE NOT NULL
        )
    """)
    # 数据质量巡检报告（scripts/run_data_quality_checks.py 写入）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_reports (
            id INTEGER PRIMARY KEY,
            run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_json VARCHAR NOT NULL
        )
    """)
    # 十大股东（scripts/run_shareholder_collect.py / 财报采集器）；与股东筹码策略 API 共用
    conn.execute("""
        CREATE TABLE IF NOT EXISTS top_10_shareholders (
            stock_code VARCHAR NOT NULL,
            report_date DATE NOT NULL,
            report_type VARCHAR,
            rank INTEGER NOT NULL,
            shareholder_name VARCHAR,
            shareholder_type VARCHAR,
            share_count DOUBLE,
            share_ratio DOUBLE,
            share_change DOUBLE,
            change_ratio DOUBLE,
            pledge_count DOUBLE,
            freeze_count DOUBLE,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            PRIMARY KEY (stock_code, report_date, rank)
        )
    """)
    for _tbl_alter in (
        "ALTER TABLE top_10_shareholders ADD COLUMN share_change DOUBLE",
        "ALTER TABLE top_10_shareholders ADD COLUMN change_ratio DOUBLE",
        "ALTER TABLE top_10_shareholders ADD COLUMN pledge_count DOUBLE",
        "ALTER TABLE top_10_shareholders ADD COLUMN freeze_count DOUBLE",
        "ALTER TABLE top_10_shareholders ADD COLUMN created_at TIMESTAMP",
        "ALTER TABLE top_10_shareholders ADD COLUMN updated_at TIMESTAMP",
        "ALTER TABLE top_10_shareholders ADD COLUMN report_type VARCHAR",
    ):
        try:
            conn.execute(_tbl_alter)
        except Exception:
            pass
    # 统一终端用户与纸面委托（原 Hongshan PostgreSQL 逻辑迁入 DuckDB，仅保留一套存储）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hongshan_users (
            user_id VARCHAR PRIMARY KEY,
            username VARCHAR NOT NULL UNIQUE,
            email VARCHAR NOT NULL UNIQUE,
            phone VARCHAR,
            password_hash VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hongshan_accounts (
            user_id VARCHAR PRIMARY KEY,
            available_cash DOUBLE NOT NULL DEFAULT 500000,
            frozen_cash DOUBLE NOT NULL DEFAULT 0,
            total_assets DOUBLE NOT NULL DEFAULT 500000,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hongshan_paper_orders (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            stock_name VARCHAR,
            order_type VARCHAR NOT NULL,
            order_style VARCHAR DEFAULT 'limit',
            order_price DOUBLE,
            order_quantity INTEGER NOT NULL,
            filled_quantity INTEGER DEFAULT 0,
            status VARCHAR DEFAULT 'pending',
            order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        conn.execute("ALTER TABLE hongshan_paper_orders ADD COLUMN filled_at TIMESTAMP")
    except Exception:
        pass
