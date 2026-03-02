# -*- coding: utf-8 -*-
"""
DuckDB 数据后端：平台唯一数据库，与旧 StockDatabase 接口兼容。
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _duckdb_path() -> str:
    return os.path.join(_ROOT, "data", "quant.duckdb")


def get_db_backend():
    """返回平台唯一数据后端（DuckDB）。"""
    return DuckDBBackend()


class DuckDBBackend:
    """
    与 database.db_schema.StockDatabase 兼容的接口，底层用 DuckDB。
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _duckdb_path()
        self._connection = None

    def _get_conn(self):
        if self._connection is not None and not getattr(self._connection, "closed", True):
            return self._connection
        try:
            import duckdb
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._connection = duckdb.connect(self.db_path)
            self._connection.execute("PRAGMA threads=4")
            self._ensure_schema()
            return self._connection
        except ImportError:
            raise ImportError("请安装 duckdb: pip install duckdb")

    def _ensure_schema(self):
        """确保基础表结构存在（空库首次使用时创建）。"""
        c = self._connection
        c.execute("""
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
        # 新库：直接建带 adjust_type 的表；老库：由迁移补上 adjust_type
        c.execute("""
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
        self._migrate_daily_bars_add_adjust_type(c)
        # 新闻热点与舆情摘要表（可选，用于新闻服务留痕）
        c.execute("""
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
        for idx_sql in (
            "CREATE INDEX IF NOT EXISTS idx_daily_bars_order_book_id ON daily_bars(order_book_id)",
            "CREATE INDEX IF NOT EXISTS idx_daily_bars_trade_date ON daily_bars(trade_date)",
        ):
            try:
                c.execute(idx_sql)
            except Exception:
                pass

    def _migrate_daily_bars_add_adjust_type(self, c) -> None:
        """若 daily_bars 已存在但无 adjust_type 列，则迁移为 (order_book_id, trade_date, adjust_type) 主键，原数据标为 qfq。"""
        try:
            info = c.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_catalog=current_database() AND table_name='daily_bars'"
            ).fetchall()
            cols = [r[0] for r in info] if info else []
            if "adjust_type" in cols:
                return
            # 表存在但无 adjust_type：重建表并迁移
            c.execute("""
                CREATE TABLE daily_bars_new (
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
            c.execute("""
                INSERT INTO daily_bars_new (order_book_id, trade_date, adjust_type, open, high, low, close, volume, total_turnover, adjust_factor)
                SELECT order_book_id, trade_date, 'qfq', open, high, low, close, volume, total_turnover, adjust_factor FROM daily_bars
            """)
            c.execute("DROP TABLE daily_bars")
            c.execute("ALTER TABLE daily_bars_new RENAME TO daily_bars")
            for idx_sql in (
                "CREATE INDEX IF NOT EXISTS idx_daily_bars_order_book_id ON daily_bars(order_book_id)",
                "CREATE INDEX IF NOT EXISTS idx_daily_bars_trade_date ON daily_bars(trade_date)",
            ):
                try:
                    c.execute(idx_sql)
                except Exception:
                    pass
        except Exception:
            pass

    # ----- 新闻写入 -----

    def insert_news_items(self, symbol: str, items: List[Dict[str, Any]]) -> None:
        """
        将新闻列表写入 DuckDB。调用方负责去重策略，此处仅做追加写入。
        items 预期包含 title / content / url / source / source_site / publish_time /
        keyword / tag / sentiment_score / sentiment_label 等键（缺失则为空）。
        """
        if not items:
            return
        c = self._get_conn()
        rows = []
        for it in items:
            rows.append(
                [
                    str(symbol or ""),
                    str(it.get("source_site") or ""),
                    str(it.get("source") or ""),
                    str(it.get("title") or ""),
                    str(it.get("content") or ""),
                    str(it.get("url") or ""),
                    str(it.get("keyword") or ""),
                    str(it.get("tag") or ""),
                    str(it.get("publish_time") or ""),
                    float(it.get("sentiment_score") or 0.0),
                    str(it.get("sentiment_label") or ""),
                ]
            )
        try:
            c.executemany(
                """
                INSERT INTO news_items (
                    symbol,
                    source_site,
                    source,
                    title,
                    content,
                    url,
                    keyword,
                    tag,
                    publish_time,
                    sentiment_score,
                    sentiment_label
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        except Exception:
            # 新闻落库失败不应影响主流程
            return

    def get_daily_bars(
        self,
        order_book_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: str = "qfq",
    ) -> pd.DataFrame:
        """与 StockDatabase.get_daily_bars 一致：返回 index=trade_date, columns=open,high,low,close,volume,total_turnover。adjust_type: qfq 前复权 / hfq 后复权。"""
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
        c = self._get_conn()
        sql = "SELECT trade_date, open, high, low, close, volume, total_turnover FROM daily_bars WHERE order_book_id = ? AND adjust_type = ?"
        params = [order_book_id, adjust_type]
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY trade_date"
        try:
            df = c.execute(sql, params).fetchdf()
        except Exception:
            return pd.DataFrame()
        if len(df) == 0:
            return pd.DataFrame()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date")
        return df

    def get_stocks(self) -> List[Tuple]:
        """与 StockDatabase.get_stocks 一致。"""
        if not os.path.exists(self.db_path):
            return []
        try:
            df = self._get_conn().execute("SELECT order_book_id, symbol, name FROM stocks").fetchdf()
            out = []
            for _, row in df.iterrows():
                ob = str(row["order_book_id"]) if row.get("order_book_id") is not None else ""
                sym = str(row["symbol"]) if row.get("symbol") is not None else ""
                name = str(row["name"]) if row.get("name") is not None else ""
                out.append((ob, sym, name))
            return out
        except Exception:
            return []

    def get_stocks_from_daily_bars(self) -> List[Tuple]:
        """当 stocks 表为空时，从 daily_bars 去重得到标的列表。返回 (order_book_id, symbol, name)，name 暂用 symbol。"""
        if not os.path.exists(self.db_path):
            return []
        try:
            df = self._get_conn().execute(
                "SELECT DISTINCT order_book_id FROM daily_bars ORDER BY order_book_id"
            ).fetchdf()
            out = []
            for ob in df["order_book_id"].astype(str).tolist():
                sym = ob.split(".")[0] if "." in ob else ob
                out.append((ob, sym, sym))
            return out
        except Exception:
            return []

    def get_daily_bars_count(self) -> int:
        """日线表总条数，供 db_stats 等使用，避免重复打开同一 DuckDB 文件。"""
        if not os.path.exists(self.db_path):
            return 0
        try:
            r = self._get_conn().execute("SELECT COUNT(*) FROM daily_bars").fetchone()
            return int(r[0]) if r else 0
        except Exception:
            return 0

    def get_last_trade_date(self, order_book_id: str, adjust_type: Optional[str] = None) -> Optional[str]:
        """某标的在库中的最新交易日，用于增量拉取。adjust_type 为空时取任意复权序列的最大日期。返回 YYYY-MM-DD 或 None。"""
        if not os.path.exists(self.db_path):
            return None
        try:
            if adjust_type:
                r = self._get_conn().execute(
                    "SELECT max(trade_date) FROM daily_bars WHERE order_book_id = ? AND adjust_type = ?",
                    [order_book_id, adjust_type],
                ).fetchone()
            else:
                r = self._get_conn().execute(
                    "SELECT max(trade_date) FROM daily_bars WHERE order_book_id = ?",
                    [order_book_id],
                ).fetchone()
            if r and r[0] is not None:
                return str(r[0])[:10]
            return None
        except Exception:
            return None

    def add_daily_bars(
        self,
        order_book_id: str,
        bars_df: pd.DataFrame,
        adjust_type: str = "qfq",
    ) -> None:
        """写入日线。bars_df 可为中文列名 日期/开盘/最高/最低/收盘/成交量/成交额。adjust_type: qfq 前复权 / hfq 后复权。"""
        if bars_df is None or len(bars_df) == 0:
            return
        col_map = {
            "日期": "trade_date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "total_turnover",
            "date": "trade_date",
        }
        d = bars_df.copy()
        for cn, en in col_map.items():
            if cn in d.columns and en not in d.columns:
                d[en] = d[cn]
        if "trade_date" not in d.columns and "日期" in d.columns:
            d["trade_date"] = pd.to_datetime(d["日期"]).dt.strftime("%Y-%m-%d")
        if "trade_date" not in d.columns and "date" in d.columns:
            d["trade_date"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
        d["order_book_id"] = order_book_id
        d["adjust_type"] = adjust_type
        d["total_turnover"] = d.get("total_turnover", d.get("成交额", 0))
        d["adjust_factor"] = 1.0
        cols = ["order_book_id", "trade_date", "adjust_type", "open", "high", "low", "close", "volume", "total_turnover", "adjust_factor"]
        for c in cols:
            if c not in d.columns:
                d[c] = 0.0 if c != "adjust_type" else "qfq"
        d = d[cols]
        conn = self._get_conn()
        conn.register("_bars", d)
        try:
            conn.execute("""
                MERGE INTO daily_bars AS t
                USING _bars AS s
                ON t.order_book_id = s.order_book_id AND t.trade_date = s.trade_date AND t.adjust_type = s.adjust_type
                WHEN MATCHED THEN UPDATE SET
                    open = s.open, high = s.high, low = s.low, close = s.close,
                    volume = s.volume, total_turnover = s.total_turnover
                WHEN NOT MATCHED THEN INSERT (order_book_id, trade_date, adjust_type, open, high, low, close, volume, total_turnover, adjust_factor)
                    VALUES (s.order_book_id, s.trade_date, s.adjust_type, s.open, s.high, s.low, s.close, s.volume, s.total_turnover, s.adjust_factor)
            """)
        except Exception:
            conn.execute(
                "DELETE FROM daily_bars WHERE order_book_id = ? AND adjust_type = ? AND trade_date IN (SELECT trade_date FROM _bars)",
                [order_book_id, adjust_type],
            )
            conn.execute("INSERT INTO daily_bars SELECT * FROM _bars")
        conn.unregister("_bars")

    def add_stock(
        self,
        order_book_id: str,
        symbol: str,
        name: Optional[str] = None,
        market: str = "CN",
        listed_date: Optional[str] = None,
        de_listed_date: Optional[str] = None,
        type: str = "CS",
    ) -> None:
        """添加或更新股票基本信息，与 StockDatabase.add_stock 兼容。"""
        from datetime import datetime
        c = self._get_conn()
        now = datetime.now().isoformat()[:19]
        name_val = name if name else symbol
        c.execute("DELETE FROM stocks WHERE order_book_id = ?", [order_book_id])
        # 北交所写入 .BSE 时，删除历史上错误写入的同代码 .XSHE，避免重复
        if order_book_id.endswith(".BSE"):
            c.execute("DELETE FROM stocks WHERE symbol = ? AND order_book_id LIKE ?", [symbol, "%.XSHE"])
        try:
            c.execute("""
                INSERT INTO stocks (order_book_id, symbol, name, market, listed_date, de_listed_date, type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [order_book_id, symbol, name_val, market, listed_date, de_listed_date, type, now])
        except Exception:
            c.execute(
                "INSERT INTO stocks (order_book_id, symbol, name) VALUES (?, ?, ?)",
                [order_book_id, symbol, name_val],
            )


