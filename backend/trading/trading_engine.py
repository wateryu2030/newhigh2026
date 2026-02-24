# -*- coding: utf-8 -*-
"""
交易主引擎：加载数据 -> 生成信号 -> 风险检查 -> 计算仓位 -> 执行订单 -> 记录日志。
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .signal_engine import generate_signals
from .risk_manager import RiskManager, check_risk
from .position_manager import calculate_position
from .order_executor import OrderExecutor
from .broker_interface import Broker
from . import db_logger


class TradingEngine:
    """
    交易主引擎：串联信号、风险、仓位、执行与日志。
    """

    def __init__(
        self,
        broker: Optional[Broker] = None,
        risk_manager: Optional[RiskManager] = None,
        order_executor: Optional[OrderExecutor] = None,
    ):
        self.broker = broker or Broker(mode="simulation")
        self.risk_manager = risk_manager or RiskManager()
        self.order_executor = order_executor or OrderExecutor(self.broker)

    def _load_market_data(self, symbols: Optional[List[str]] = None, limit: int = 300) -> Dict[str, Any]:
        """从数据库加载近期行情，供 generate_signals。"""
        try:
            from database.duckdb_backend import get_db_backend
            db = get_db_backend()
            import os
            if not getattr(db, "db_path", None) or not os.path.exists(getattr(db, "db_path", "")):
                return {}
            stocks = db.get_stocks()
            if not stocks:
                return {}
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
            if symbols is None:
                symbols = [r[0] for r in (stocks[:limit] if limit else stocks)]
            market_data = {}
            for order_book_id in symbols:
                df = db.get_daily_bars(order_book_id, start_date, end_date)
                if df is not None and len(df) >= 20:
                    market_data[order_book_id] = df
            return market_data
        except Exception:
            return {}

    def _get_portfolio(self) -> Dict[str, Any]:
        """当前资金与持仓，用于风险与仓位计算。"""
        balance = self.broker.get_balance()
        positions = self.broker.get_positions()
        total = float(balance.get("total_asset") or 0)
        cash = float(balance.get("cash") or 0)
        pos_dict = {}
        for sym, p in positions.items():
            mv = float(p.get("market_value") or 0)
            w = (mv / total) if total > 0 else 0
            pos_dict[sym] = {"market_value": mv, "weight": w}
        return {
            "total_asset": total,
            "cash": cash,
            "positions": pos_dict,
            "daily_pnl": getattr(self, "_daily_pnl", 0),
            "peak_asset": getattr(self, "_peak_asset", total),
            "risk_budget": 0.2,
        }

    def run_daily_trading(
        self,
        symbols: Optional[List[str]] = None,
        signal_limit: int = 50,
    ) -> Dict[str, Any]:
        """
        执行当日交易流程：加载数据 -> 生成信号 -> 风险检查 -> 计算仓位 -> 执行订单 -> 记录日志。
        返回: {"signals": [...], "orders": [...], "logs": [...]}
        """
        self.broker.connect()
        portfolio = self._get_portfolio()
        if not portfolio.get("total_asset"):
            portfolio["total_asset"] = 1000000.0
            portfolio["cash"] = 1000000.0
        market_data = self._load_market_data(symbols=symbols)
        if not market_data:
            return {"signals": [], "orders": [], "logs": ["无行情数据"]}
        signals = generate_signals(market_data)[:signal_limit]
        orders_done = []
        logs = []
        for sig in signals:
            ok, msg = check_risk(sig, portfolio)
            if not ok:
                db_logger.log_trade(
                    symbol=sig.get("symbol", ""),
                    action=sig.get("action", ""),
                    signal_confidence=float(sig.get("confidence", 0)),
                    risk_ok=False,
                    position_pct=0,
                    msg=msg,
                )
                logs.append(f"风险拒绝: {sig.get('symbol')} {msg}")
                continue
            account = self._get_portfolio()
            position_pct = calculate_position(sig, account)
            if position_pct <= 0 and (sig.get("action") or "").upper() == "BUY":
                continue
            symbol = (sig.get("symbol") or "").strip()
            order_book_id = symbol if "." in symbol else (symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE")
            price = None
            if market_data and order_book_id in market_data:
                df = market_data[order_book_id]
                if df is not None and len(df) > 0 and "close" in df.columns:
                    price = float(df["close"].iloc[-1])
            if price is None or price <= 0:
                try:
                    from database.duckdb_backend import get_db_backend
                    db = get_db_backend()
                    df = db.get_daily_bars(order_book_id, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"))
                    if df is not None and len(df) > 0:
                        price = float(df["close"].iloc[-1])
                except Exception:
                    pass
            if price is None or price <= 0:
                logs.append(f"跳过: {symbol} 无有效价格")
                continue
            total = float(portfolio.get("total_asset") or 0)
            if (sig.get("action") or "").upper() == "BUY":
                qty_float = (total * position_pct) / price
                qty = int(qty_float) // 100 * 100
                if qty < 100:
                    qty = 100
            else:
                qty = 0
            if qty <= 0:
                continue
            order = self.order_executor.place_order(symbol=order_book_id, qty=qty, price=price, side=(sig.get("action") or "BUY").upper())
            if order:
                orders_done.append(order)
                db_logger.log_trade(
                    symbol=symbol,
                    action=sig.get("action", ""),
                    signal_confidence=float(sig.get("confidence", 0)),
                    risk_ok=True,
                    position_pct=position_pct,
                    order_id=order.get("order_id"),
                    msg="已下单",
                )
                logs.append(f"下单: {symbol} {sig.get('action')} qty={qty} price={price}")
        try:
            pos_list = []
            for sym, p in self.broker.get_positions().items():
                pos_list.append({
                    "symbol": sym,
                    "qty": p.get("qty", 0),
                    "avg_price": p.get("avg_price", 0),
                    "market_value": p.get("market_value", 0),
                    "weight": p.get("weight", 0),
                })
            if pos_list:
                db_logger.log_positions(pos_list)
        except Exception:
            pass
        return {"signals": signals, "orders": orders_done, "logs": logs}


def run_daily_trading(
    symbols: Optional[List[str]] = None,
    broker_mode: str = "simulation",
) -> Dict[str, Any]:
    """
    便捷函数：创建默认 TradingEngine 并执行 run_daily_trading。
    """
    broker = Broker(mode=broker_mode)
    engine = TradingEngine(broker=broker)
    return engine.run_daily_trading(symbols=symbols)
