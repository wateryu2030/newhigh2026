"""Realtime stream: subscribe to Binance WebSocket klines and yield OHLCV updates."""

import datetime as dt
import json
import threading
from typing import Callable, Optional

import websocket

from core import OHLCV


def _parse_ws_kline(msg: dict) -> OHLCV:
    k = msg.get("k", {})
    return OHLCV(
        symbol=k.get("s", ""),
        timestamp=dt.datetime.fromtimestamp(int(k.get("t", 0)) / 1000, tz=dt.timezone.utc),
        open=float(k.get("o", 0)),
        high=float(k.get("h", 0)),
        low=float(k.get("l", 0)),
        close=float(k.get("c", 0)),
        volume=float(k.get("v", 0)),
        interval=k.get("i", "1m"),
    )


def stream_klines(
    symbol: str,
    interval: str = "1m",
    on_bar: Optional[Callable[[OHLCV], None]] = None,
    ws_url: str = "wss://stream.binance.com:9443/ws",
) -> None:
    """
    Connect to Binance kline stream and call on_bar for each update.
    Runs in current thread; for background use, run in a thread.
    """
    stream_name = f"{symbol.lower().replace('/', '')}@kline_{interval}"
    url = f"{ws_url}/{stream_name}"

    def on_message(ws, message):
        data = json.loads(message)
        if "k" in data:
            bar = _parse_ws_kline(data)
            if on_bar:
                on_bar(bar)

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
    )
    ws.run_forever()


def stream_klines_async(
    symbol: str,
    interval: str = "1m",
    on_bar: Optional[Callable[[OHLCV], None]] = None,
) -> threading.Thread:
    """Start realtime stream in a background thread. Returns the thread."""
    t = threading.Thread(
        target=stream_klines,
        kwargs={"symbol": symbol, "interval": interval, "on_bar": on_bar},
        daemon=True,
    )
    t.start()
    return t
