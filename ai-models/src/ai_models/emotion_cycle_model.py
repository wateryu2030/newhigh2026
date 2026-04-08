"""
AI情绪周期识别系统：涨停数量、连板高度、成交额 → 冰点/启动/主升/高潮/退潮。
决定仓位与风格。
"""

from __future__ import annotations

import pandas as pd


class EmotionCycleModel:
    def __init__(self, conn=None):
        self._connection = conn

    def _get_connection(self):
        if self._connection is not None:
            return self._connection
        from lib.database import get_connection, ensure_core_tables  # pylint: disable=import-error
        conn = get_connection(read_only=False)
        if conn:
            ensure_core_tables(conn)
        return conn

    def calculate_metrics(self):
        """涨停数量、连板高度、市场成交额，按日聚合。"""
        conn = self._get_connection()
        if not conn:
            return pd.DataFrame(columns=["trade_date", "limitup_count", "max_height", "market_volume"])
        # 涨停按日：日期、数量、最大连板高度
        limitup = conn.execute("""
            SELECT
                DATE(snapshot_time) AS trade_date,
                COUNT(*) AS limitup_count,
                MAX(COALESCE(limit_up_times, 1)) AS max_height
            FROM a_stock_limitup
            WHERE snapshot_time IS NOT NULL
            GROUP BY DATE(snapshot_time)
        """).fetchdf()
        if limitup is None or limitup.empty:
            limitup = pd.DataFrame(columns=["trade_date", "limitup_count", "max_height"])
        # 市场成交额按日
        try:
            volume = conn.execute("""
                SELECT date AS trade_date, SUM(COALESCE(amount, 0)) AS market_volume
                FROM a_stock_daily
                GROUP BY date
            """).fetchdf()
        except Exception:  # pylint: disable=broad-exception-caught
            volume = pd.DataFrame(columns=["trade_date", "market_volume"])
        if volume is None or volume.empty:
            volume = pd.DataFrame(columns=["trade_date", "market_volume"])
        if limitup.empty and volume.empty:
            return pd.DataFrame(
                columns=[
                    "trade_date",
                    "limitup_count",
                    "max_height",
                    "market_volume",
                    "emotion_state",
                ]
            )
        if limitup.empty:
            limitup["limitup_count"] = 0
            limitup["max_height"] = 0
        if volume.empty:
            volume["market_volume"] = 0.0
        df = limitup.merge(volume, on="trade_date", how="outer")
        df = df.fillna(0)
        return df

    def detect_emotion(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """根据涨停数、连板高度判定情绪状态。"""
        if df is None:
            df = self.calculate_metrics()
        if df is None or df.empty:
            df = pd.DataFrame(
                columns=[
                    "trade_date",
                    "limitup_count",
                    "max_height",
                    "market_volume",
                    "emotion_state",
                ]
            )
            return df
        states = []
        for _, row in df.iterrows():
            limitups = int(row.get("limitup_count", 0) or 0)
            _height = int(row.get("max_height", 0) or 0)  # Reserved for future use
            if limitups < 20:
                state = "冰点"
            elif limitups < 40:
                state = "启动"
            elif limitups < 80:
                state = "主升"
            elif limitups < 120:
                state = "高潮"
            else:
                state = "退潮"
            states.append(state)
        df = df.copy()
        df["emotion_state"] = states
        return df

    def save_result(self, df: pd.DataFrame = None) -> int:
        """写入 market_emotion 表。"""
        if df is None:
            df = self.detect_emotion()
        if df is None or df.empty:
            return 0
        conn = self._get_connection()
        if not conn:
            return 0
        try:
            from data_pipeline.storage.duckdb_manager import ensure_tables  # pylint: disable=import-error
            ensure_tables(conn)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        conn.register("tmp", df)
        conn.execute("DELETE FROM market_emotion WHERE trade_date IN (SELECT trade_date FROM tmp)")
        conn.execute("""
            INSERT INTO market_emotion (trade_date, limitup_count, max_height, market_volume, emotion_state)
            SELECT trade_date, limitup_count, max_height, market_volume, emotion_state FROM tmp
        """)
        n = len(df)
        conn.close()
        return n

    def get_latest_state(self) -> dict:
        """返回最近一日情绪状态，供 API 与策略。"""
        conn = self._get_connection()
        try:
            row = conn.execute("""
                SELECT trade_date, limitup_count, max_height, market_volume, emotion_state
                FROM market_emotion ORDER BY trade_date DESC LIMIT 1
            """).fetchone()
            conn.close()
            if row:
                return {
                    "trade_date": str(row[0]),
                    "limitup_count": int(row[1] or 0),
                    "max_height": int(row[2] or 0),
                    "market_volume": float(row[3] or 0),
                    "emotion_state": row[4] or "—",
                }
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return {
            "trade_date": None,
            "limitup_count": 0,
            "max_height": 0,
            "market_volume": 0,
            "emotion_state": "—",
        }


def run_emotion_cycle() -> str:
    """兼容入口：计算并保存，返回当前阶段。"""
    model = EmotionCycleModel()
    df = model.detect_emotion()
    if df is not None and not df.empty:
        model.save_result(df)
        latest = df.iloc[-1]
        return str(latest.get("emotion_state", "—"))
    # 回退：仅用 limitup 总数
    from ._storage import _get_conn

    conn = _get_conn()
    if not conn:
        return "冰点期"
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables  # pylint: disable=import-error
        ensure_tables(conn)
        row = conn.execute("SELECT COUNT(*) FROM a_stock_limitup").fetchone()
        n = int(row[0]) if row and row[0] is not None else 0
    except Exception:  # pylint: disable=broad-exception-caught
        n = 0
    if n >= 80:
        state, stage = "高潮", "高潮期"
    elif n >= 50:
        state, stage = "主升", "主升期"
    elif n >= 20:
        state, stage = "启动", "启动期"
    elif n >= 5:
        state, stage = "退潮", "退潮期"
    else:
        state, stage = "冰点", "冰点期"
    conn.execute(
        "INSERT INTO market_emotion_state (state, stage, limit_up_count, score) VALUES (?, ?, ?, ?)",
        [state, stage, n, 50.0],
    )
    conn.close()
    return stage
