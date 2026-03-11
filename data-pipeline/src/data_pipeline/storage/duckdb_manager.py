"""统一 DuckDB 数据仓库：data/quant_system.duckdb，管道 + 日K/新闻/扫描/AI/策略 共用。"""
from __future__ import annotations

import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PIPELINE_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))  # data_pipeline
_DATA_PIPELINE_ROOT = os.path.dirname(_PIPELINE_ROOT)  # data-pipeline
_NEWHIGH_ROOT = os.path.dirname(_DATA_PIPELINE_ROOT)  # newhigh
DEFAULT_DB_PATH = os.path.join(_NEWHIGH_ROOT, "data", "quant_system.duckdb")


def get_db_path() -> str:
    """统一入口：环境变量 QUANT_SYSTEM_DUCKDB_PATH 或 NEWHIGH_MARKET_DUCKDB_PATH 覆盖默认路径。"""
    return (
        os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
        or DEFAULT_DB_PATH
    )


def get_conn(read_only: bool = False):
    path = get_db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    import duckdb
    return duckdb.connect(path, read_only=read_only)


def ensure_tables(conn) -> None:
    """创建管道所需表（若不存在）。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS a_stock_basic (
            code VARCHAR PRIMARY KEY,
            name VARCHAR
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
        conn.execute("ALTER TABLE a_stock_basic ADD COLUMN sector VARCHAR")
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
