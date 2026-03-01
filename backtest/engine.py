# -*- coding: utf-8 -*-
"""
回测引擎骨架：接收策略、K 线、初始资金，输出净值与交易记录。
可与 run_backtest_db、portfolio 等现有回测逻辑对接。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional


def run_backtest(
    strategy_signal_fn: Callable[[Any], int],
    bars: Any,
    initial_cash: float = 1000000.0,
) -> Dict[str, Any]:
    """
    简化回测：bars 为 DataFrame(close, ...)，strategy_signal_fn(df) 返回 1 买 0 卖/持。
    返回 { "equity_curve": [], "trades": [], "total_return": 0, "max_drawdown": 0 }。
    """
    equity_curve = [initial_cash]
    trades: List[Dict[str, Any]] = []
    position = 0.0
    cash = initial_cash
    if bars is None or len(bars) < 2:
        return {"equity_curve": equity_curve, "trades": trades, "total_return": 0.0, "max_drawdown": 0.0}
    close = bars["close"] if "close" in bars.columns else bars.get("收盘", bars.iloc[:, 3])
    for i in range(1, len(bars)):
        df_slice = bars.iloc[: i + 1]
        sig = strategy_signal_fn(df_slice)
        price = float(close.iloc[i])
        if sig == 1 and position == 0 and cash > price * 100:
            sh = int(cash * 0.5 / price / 100) * 100 or 100
            cost = sh * price
            cash -= cost
            position = sh
            trades.append({"date": str(bars.index[i])[:10], "side": "BUY", "price": price, "qty": sh})
        elif sig == 0 and position > 0:
            cash += position * price
            trades.append({"date": str(bars.index[i])[:10], "side": "SELL", "price": price, "qty": position})
            position = 0
        equity_curve.append(cash + position * price)
    total_return = (equity_curve[-1] / initial_cash - 1.0) if equity_curve else 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "total_return": total_return,
        "max_drawdown": max_dd,
    }
