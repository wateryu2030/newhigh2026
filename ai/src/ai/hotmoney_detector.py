"""
龙虎榜游资席位胜率系统：席位统计、胜率、平均收益 → 顶级游资席位。
决定跟谁。
"""

from __future__ import annotations

import pandas as pd


class HotMoneyAnalyzer:
    def __init__(self, conn=None):
        self._connection = conn

    def _get_connection(self):
        if self._connection is not None:
            return self._connection
        from lib.database import get_connection, ensure_core_tables

        conn = get_connection(read_only=False)
        if conn:
            ensure_core_tables(conn)
        return conn

    def seat_statistics(self) -> pd.DataFrame:
        """按席位（或 code 当无席位时）统计：交易次数、总买入金额。"""
        conn = self._get_connection()
        if not conn:
            return pd.DataFrame(columns=["seat", "trade_count", "total_buy"])
        # 若有 seat_name 则按席位，否则按 code 作为“席位”维度
        try:
            df = conn.execute("""
                SELECT
                    COALESCE(seat_name, code) AS seat,
                    COUNT(*) AS trade_count,
                    SUM(COALESCE(buy_amount, net_buy, 0)) AS total_buy
                FROM a_stock_longhubang
                GROUP BY COALESCE(seat_name, code)
            """).fetchdf()
        except Exception:
            df = conn.execute("""
                SELECT
                    code AS seat,
                    COUNT(*) AS trade_count,
                    SUM(COALESCE(net_buy, 0)) AS total_buy
                FROM a_stock_longhubang
                GROUP BY code
            """).fetchdf()
        return (
            df
            if df is not None and not df.empty
            else pd.DataFrame(columns=["seat", "trade_count", "total_buy"])
        )

    def calculate_winrate(self, forward_days: int = 5) -> pd.DataFrame:
        """结合后续涨幅算席位胜率与平均收益。买价用龙虎榜当日收盘价近似。"""
        conn = self._get_connection()
        try:
            from data_pipeline.storage.duckdb_manager import ensure_tables

            ensure_tables(conn)
        except Exception:
            pass
        # 用 SQL：daily 上 LEAD(close, N) 得 N 日后收盘，再与龙虎榜 join 算收益
        try:
            result = conn.execute(f"""
                WITH daily_lead AS (
                    SELECT code, date, close AS buy_price,
                           LEAD(close, {forward_days}) OVER (PARTITION BY code ORDER BY date) AS sell_price
                    FROM a_stock_daily
                ),
                trades AS (
                    SELECT code, COALESCE(seat_name, code) AS seat, lhb_date AS trade_date
                    FROM a_stock_longhubang WHERE lhb_date IS NOT NULL
                ),
                combined AS (
                    SELECT t.seat, d.buy_price, d.sell_price
                    FROM trades t
                    JOIN daily_lead d ON t.code = d.code AND t.trade_date = d.date
                    WHERE d.sell_price IS NOT NULL AND d.buy_price IS NOT NULL AND d.buy_price > 0
                )
                SELECT seat,
                       AVG(CASE WHEN sell_price / buy_price - 1 > 0 THEN 1.0 ELSE 0.0 END) AS win_rate,
                       AVG(sell_price / buy_price - 1) AS avg_return
                FROM combined
                GROUP BY seat
            """).fetchdf()
        except Exception:
            try:
                result = conn.execute("""
                    SELECT code AS seat, 0.5 AS win_rate, 0.0 AS avg_return
                    FROM a_stock_longhubang LIMIT 0
                """).fetchdf()
            except Exception:
                result = None
        if result is None or result.empty:
            return pd.DataFrame(columns=["seat", "win_rate", "avg_return"])
        return result

    def detect_top_hotmoney(
        self, min_win_rate: float = 0.55, min_avg_return: float = 0.03
    ) -> pd.DataFrame:
        """筛选顶级游资：胜率 > min_win_rate，平均收益 > min_avg_return。"""
        df = self.calculate_winrate()
        if df is None or df.empty:
            return pd.DataFrame(columns=["seat_name", "trade_count", "win_rate", "avg_return"])
        stats = self.seat_statistics()
        if not stats.empty:
            df = df.merge(
                stats[["seat", "trade_count"]], left_on="seat", right_on="seat", how="left"
            )
        else:
            df["trade_count"] = 0
        df = df[(df["win_rate"] > min_win_rate) & (df["avg_return"] > min_avg_return)]
        df = df.rename(columns={"seat": "seat_name"})
        return df[["seat_name", "trade_count", "win_rate", "avg_return"]].fillna(0)

    def save_top_seats(self, df: pd.DataFrame = None) -> int:
        """写入 top_hotmoney_seats 表。"""
        if df is None:
            df = self.detect_top_hotmoney()
        if df is None or df.empty:
            return 0
        conn = self._get_connection()
        try:
            from data_pipeline.storage.duckdb_manager import ensure_tables

            ensure_tables(conn)
        except Exception:
            pass
        conn.execute("DELETE FROM top_hotmoney_seats")
        conn.register("tmp", df)
        conn.execute("""
            INSERT INTO top_hotmoney_seats (seat_name, trade_count, win_rate, avg_return)
            SELECT seat_name, trade_count, win_rate, avg_return FROM tmp
        """)
        n = len(df)
        return n


def run_hotmoney_detector() -> int:
    """兼容入口：计算顶级席位并写入表，同时写 hotmoney_signals。"""
    analyzer = HotMoneyAnalyzer()
    top = analyzer.detect_top_hotmoney()
    n_seats = 0
    if top is not None and not top.empty:
        analyzer.save_top_seats(top)
        n_seats = len(top)
    signals = []
    if top is not None and not top.empty:
        for _, row in top.iterrows():
            signals.append((str(row.get("seat_name", "")), "游资", float(row.get("win_rate", 0.5))))
    if not signals:
        from ._storage import _get_conn

        conn = _get_conn()
        try:
            df = conn.execute(
                "SELECT code, net_buy FROM a_stock_longhubang ORDER BY net_buy DESC NULLS LAST LIMIT 50"
            ).fetchdf()
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    signals.append((str(row.get("code", "")), "游资", 0.55))
        except Exception:
            pass
        conn.close()
    from ._storage import write_hotmoney_signals

    write_hotmoney_signals(signals)
    return len(signals)
