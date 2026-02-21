# -*- coding: utf-8 -*-
"""
交易引擎：从策略读取买卖信号，调用 broker 执行，每日更新资产。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from .paper_broker import PaperBroker


def _default_signal_parser(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将策略信号解析为统一格式。"""
    out = []
    for s in signals:
        date = str(s.get("date", ""))[:10]
        typ = str(s.get("type", s.get("signal", "HOLD"))).upper()
        if typ not in ("BUY", "SELL"):
            continue
        price = float(s.get("price", 0))
        reason = str(s.get("reason", ""))
        amount = int(s.get("amount", 100))
        out.append({"date": date, "type": typ, "price": price, "reason": reason, "amount": amount})
    return out


class TradeEngine:
    """
    交易引擎。
    - 从 strategy 模块读取买卖信号
    - 调用 broker 执行交易
    - 每日更新资产（equity curve）
    """

    def __init__(
        self,
        broker: Optional[PaperBroker] = None,
        signal_parser: Optional[Callable] = None,
    ):
        self.broker = broker or PaperBroker()
        self.signal_parser = signal_parser or _default_signal_parser

    def run_day(
        self,
        date_str: str,
        symbol: str,
        close: float,
        signals: List[Dict[str, Any]],
    ) -> None:
        """
        执行单日逻辑：处理信号 + 更新持仓价 + 记录权益。
        """
        parsed = self.signal_parser(signals)
        for sig in parsed:
            if str(sig.get("date", ""))[:10] != date_str[:10]:
                continue
            typ = sig.get("type", "HOLD")
            price = float(sig.get("price", close))
            reason = sig.get("reason", "")
            amount = int(sig.get("amount", 100))
            if typ == "BUY":
                self.broker.buy(symbol, price, amount, date_str, reason)
            elif typ == "SELL":
                self.broker.sell_all(symbol, price, date_str, reason)

        self.broker.account.update_position_price(symbol, close)
        self.broker.account.record_equity(date_str)

    def run_from_kline(
        self,
        df: pd.DataFrame,
        symbol: str,
        get_signals: Callable[[pd.DataFrame], List[Dict[str, Any]]],
    ) -> None:
        """
        按 K 线逐日运行：对每一天生成信号并执行。
        :param df: K 线，需有 date 或 datetime index，及 close
        :param symbol: 标的代码
        :param get_signals: 函数 (df_slice) -> signals
        """
        if df is None or len(df) == 0:
            return
        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        dates = df["date"].drop_duplicates().tolist() if "date" in df.columns else []
        if not dates and df.index is not None:
            dates = [str(d)[:10] for d in df.index.unique()]
        for i, d in enumerate(dates):
            sub = df[df["date"] == d] if "date" in df.columns else df.iloc[: i + 1]
            if sub is None or len(sub) == 0:
                continue
            close = float(sub["close"].iloc[-1])
            signals = get_signals(sub)
            self.run_day(str(d)[:10], symbol, close, signals)
