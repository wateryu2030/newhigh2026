"""
Binance K 线数据源（公开 API）：拉取现货 K 线写入 binance_klines 表。
"""
from __future__ import annotations

import os
from typing import Any, List, Optional

from .base import BaseDataSource, register_source


def _ensure_binance_table(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS binance_klines (
            symbol VARCHAR NOT NULL,
            interval VARCHAR NOT NULL,
            open_time BIGINT NOT NULL,
            open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE,
            PRIMARY KEY (symbol, interval, open_time)
        )
    """)


class BinanceKlinesSource(BaseDataSource):
    """Binance 现货 K 线，interval 如 1d/1h/15m。"""

    @property
    def source_id(self) -> str:
        return "binance_klines"

    def get_last_key(self, conn: Any) -> Optional[str]:
        try:
            _ensure_binance_table(conn)
            _ensure_binance_table(conn)
            row = conn.execute(
                "SELECT max(open_time) AS t FROM binance_klines WHERE symbol = ? AND interval = ?",
                [self._symbol(), self._interval()],
            ).fetchone()
            if row and row[0] is not None:
                return str(int(row[0]))
        except Exception:
            pass
        return None

    def _symbol(self) -> str:
        return os.environ.get("BINANCE_KLINES_SYMBOL", "BTCUSDT")

    def _interval(self) -> str:
        return os.environ.get("BINANCE_KLINES_INTERVAL", "1d")

    def fetch(
        self,
        start_key: Optional[str] = None,
        end_key: Optional[str] = None,
        symbol: Optional[str] = None,
        interval: Optional[str] = None,
        limit: int = 500,
        **kwargs: Any,
    ) -> Any:
        try:
            import pandas as pd
            import urllib.request
            import json
        except ImportError:
            return None
        sym = symbol or self._symbol()
        inv = interval or self._interval()
        base = "https://api.binance.com/api/v3/klines"
        params = f"symbol={sym}&interval={inv}&limit={limit}"
        if start_key:
            params += f"&startTime={start_key}"
        if end_key:
            params += f"&endTime={end_key}"
        try:
            with urllib.request.urlopen(base + "?" + params, timeout=15) as r:
                rows = json.loads(r.read().decode())
        except Exception:
            return __import__("pandas").DataFrame()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
        ])
        df = df.astype({
            "open_time": int, "open": float, "high": float, "low": float, "close": float, "volume": float,
        })
        df["symbol"] = sym
        df["interval"] = inv
        return df[["symbol", "interval", "open_time", "open", "high", "low", "close", "volume"]]

    def write(self, conn: Any, data: Any) -> int:
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        import pandas as pd
        if not isinstance(data, pd.DataFrame):
            return 0
        _ensure_binance_table(conn)
        conn.register("tmp_bn", data)
        try:
            conn.execute("""
                INSERT INTO binance_klines (symbol, interval, open_time, open, high, low, close, volume)
                SELECT symbol, interval, open_time, open, high, low, close, volume FROM tmp_bn
                ON CONFLICT (symbol, interval, open_time) DO UPDATE SET
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume
            """)
        except Exception:
            for _, row in data.iterrows():
                try:
                    conn.execute("""
                        INSERT INTO binance_klines (symbol, interval, open_time, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (symbol, interval, open_time) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume
                    """, [
                        row["symbol"], row["interval"], int(row["open_time"]),
                        float(row["open"]), float(row["high"]), float(row["low"]),
                        float(row["close"]), float(row["volume"]),
                    ])
                except Exception:
                    pass
        return int(len(data))

    def run_incremental(self, conn: Any, force_full: bool = False, **kwargs: Any) -> int:
        _ensure_binance_table(conn)
        last = None if force_full else self.get_last_key(conn)
        data = self.fetch(start_key=last, limit=kwargs.pop("limit", 500), **kwargs)
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        return self.write(conn, data)


register_source("binance_klines", BinanceKlinesSource())
