# -*- coding: utf-8 -*-
"""
股票扫描器：对股票池逐只运行策略，筛选出「最新 K 线出现信号」的标的。
支持插件策略（ma_cross/rsi/macd/breakout/swing_newhigh）与自进化策略（ev_*）。
"""
import os
import sys
from typing import List, Dict, Any, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def scan_market(
    strategy_id: str,
    timeframe: str = "D",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    扫描市场：对每只股票运行策略，仅保留「最新一根 K 线当日有信号」的标的。

    :param strategy_id: 策略 id，如 ma_cross, rsi, macd, breakout
    :param timeframe: D / W / M
    :param start_date: 回测开始日期，默认向前 120 日
    :param end_date: 回测结束日期，默认最近
    :param stock_list: 指定股票代码列表；None 则从数据库取全部（或 limit 条）
    :param limit: 仅当 stock_list 为 None 时生效，限制扫描只数
    :return: [{"symbol", "name", "signal", "price", "date", "reason", "trend", "score"}, ...]
    """
    from datetime import datetime, timedelta
    from database.db_schema import StockDatabase
    from core.timeframe import resample_kline, normalize_timeframe
    from strategies import get_plugin_strategy
    from core.prediction import predict_trend

    tf = normalize_timeframe(timeframe)
    strategy = get_plugin_strategy(strategy_id)
    if strategy is None:
        return []

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_dt = datetime.now() - timedelta(days=120)
        start_date = start_dt.strftime("%Y-%m-%d")

    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        return []

    db = StockDatabase(db_path)
    all_rows = db.get_stocks()
    stock_names = {r[0]: (r[1], r[2]) for r in all_rows}
    if stock_list is None:
        rows = all_rows if limit is None or limit <= 0 else all_rows[:limit]
        stock_list = [r[0] for r in rows]

    results: List[Dict[str, Any]] = []
    for order_book_id in stock_list:
        try:
            df = db.get_daily_bars(order_book_id, start_date, end_date)
            if df is None or len(df) < 20:
                continue
            df = resample_kline(df, tf)
            if len(df) == 0:
                continue
            if "date" not in df.columns and df.index is not None:
                df["date"] = df.index.astype(str).str[:10]
            signals = strategy.generate_signals(df)
            if not signals:
                continue
            last_signal = signals[-1]
            last_bar_date = str(df["date"].iloc[-1])[:10]
            if last_signal["date"] != last_bar_date:
                continue
            symbol = order_book_id.split(".")[0] if "." in order_book_id else order_book_id
            name = (stock_names.get(order_book_id) or (None, None))[1] or symbol
            try:
                pred = predict_trend(df)
                trend = (pred.get("trend") or "SIDEWAYS") if isinstance(pred, dict) else "SIDEWAYS"
            except Exception:
                trend = "SIDEWAYS"
            results.append({
                "symbol": symbol,
                "order_book_id": order_book_id,
                "name": name,
                "signal": last_signal.get("type", "BUY"),
                "price": round(float(last_signal.get("price", 0)), 2),
                "date": last_signal.get("date", last_bar_date),
                "reason": last_signal.get("reason", ""),
                "trend": trend,
            })
        except Exception:
            continue

    return results


def scan_market_evolution(
    ev_id: str,
    timeframe: str = "D",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    limit: Optional[int] = None,
    pool_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    自进化策略扫描：用策略池中 ev_id 对应代码对每只股票运行，保留最新 K 线为买入信号的标的。
    :param ev_id: 自进化策略 id，如 ev_1771688319_0
    :param pool_path: 策略池 JSON 路径；None 则用 data/evolution/strategy_pool.json
    :return: 与 scan_market 同构的列表 [{"symbol", "name", "signal", "price", "date", "reason"}, ...]
    """
    from datetime import datetime, timedelta
    from database.db_schema import StockDatabase
    from core.timeframe import resample_kline, normalize_timeframe
    from evolution.strategy_pool import StrategyPool
    from evolution.strategy_runner import StrategyRunner

    if pool_path is None:
        pool_path = os.path.join(_root, "data", "evolution", "strategy_pool.json")
    pool = StrategyPool(persist_path=pool_path)
    pool.load()
    entry = next((p for p in pool.get_all() if (p.get("id") or "") == ev_id), None)
    if not entry or not entry.get("code"):
        return []

    code = entry["code"]
    runner = StrategyRunner()
    tf = normalize_timeframe(timeframe)
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_dt = datetime.now() - timedelta(days=120)
        start_date = start_dt.strftime("%Y-%m-%d")

    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        return []

    db = StockDatabase(db_path)
    all_rows = db.get_stocks()
    stock_names = {r[0]: (r[1], r[2]) for r in all_rows}
    if stock_list is None:
        rows = all_rows[: 2000]
        stock_list = [r[0] for r in rows]

    results: List[Dict[str, Any]] = []
    max_results = limit if limit and limit > 0 else 50
    for order_book_id in stock_list:
        if len(results) >= max_results:
            break
        try:
            df = db.get_daily_bars(order_book_id, start_date, end_date)
            if df is None or len(df) < 20:
                continue
            df = resample_kline(df, tf)
            if len(df) == 0:
                continue
            if "date" not in df.columns and df.index is not None:
                df = df.copy()
                df["date"] = df.index.astype(str).str[:10] if hasattr(df.index, "str") else str(df.index[-1])[:10]
            res = runner.run(code, df, entry_point="strategy")
            if res.get("error") or res.get("df") is None:
                continue
            out = res["df"]
            if "signal" not in out.columns or len(out) == 0:
                continue
            last_sig = out["signal"].iloc[-1]
            if last_sig != 1:
                continue
            last_bar_date = str(out["date"].iloc[-1])[:10] if "date" in out.columns else (str(out.index[-1])[:10] if hasattr(out.index[-1], "__str__") else "")
            close = float(out["close"].iloc[-1]) if "close" in out.columns else 0
            symbol = order_book_id.split(".")[0] if "." in order_book_id else order_book_id
            name = (stock_names.get(order_book_id) or (None, None))[1] or symbol
            results.append({
                "symbol": symbol,
                "order_book_id": order_book_id,
                "name": name,
                "signal": "BUY",
                "price": round(close, 2),
                "date": last_bar_date,
                "reason": "自进化策略最新K线信号=1",
                "trend": "SIDEWAYS",
            })
        except Exception:
            continue
    return results


def scan_market_portfolio(
    strategies: List[Dict[str, Any]],
    timeframe: str = "D",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    组合策略版扫描：多策略融合后，筛选「最新 K 线当日组合信号为 BUY/SELL」的标的。
    :param strategies: [{"strategy_id": "ma_cross", "weight": 0.5}, ...]
    :param timeframe: D / W / M
    :param start_date, end_date: 同 scan_market
    :param stock_list, limit: 同 scan_market
    :return: 与 scan_market 同构的列表，signal 为组合信号
    """
    from datetime import datetime, timedelta
    from database.db_schema import StockDatabase
    from core.timeframe import resample_kline, normalize_timeframe
    from strategies import get_plugin_strategy
    from portfolio import PortfolioEngine

    if not strategies:
        return []

    strategy_instances = []
    weights = []
    for s in strategies:
        sid = s.get("strategy_id")
        w = s.get("weight", 1.0)
        if not sid:
            continue
        inst = get_plugin_strategy(sid)
        if inst is not None:
            strategy_instances.append(inst)
            weights.append(w)
    if not strategy_instances:
        return []

    engine = PortfolioEngine(strategy_instances, weights)
    tf = normalize_timeframe(timeframe)

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_dt = datetime.now() - timedelta(days=120)
        start_date = start_dt.strftime("%Y-%m-%d")

    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        return []

    db = StockDatabase(db_path)
    all_rows = db.get_stocks()
    stock_names = {r[0]: (r[1], r[2]) for r in all_rows}
    if stock_list is None:
        rows = all_rows if limit is None or limit <= 0 else all_rows[:limit]
        stock_list = [r[0] for r in rows]

    results = []
    for order_book_id in stock_list:
        try:
            df = db.get_daily_bars(order_book_id, start_date, end_date)
            if df is None or len(df) < 20:
                continue
            df = resample_kline(df, tf)
            if len(df) == 0:
                continue
            out = engine.run(df)
            sigs = out.get("signals") or []
            if not sigs:
                continue
            last = sigs[-1]
            last_bar_date = str(df["date"].iloc[-1])[:10]
            if last.get("date") != last_bar_date:
                continue
            comb = (last.get("signal") or "HOLD").upper()
            if comb not in ("BUY", "SELL"):
                continue
            symbol = order_book_id.split(".")[0] if "." in order_book_id else order_book_id
            name = (stock_names.get(order_book_id) or (None, None))[1] or symbol
            close = float(df["close"].iloc[-1]) if len(df) else 0
            results.append({
                "symbol": symbol,
                "order_book_id": order_book_id,
                "name": name,
                "signal": comb,
                "price": round(close, 2),
                "date": last_bar_date,
                "reason": "组合信号",
                "trend": "—",
            })
        except Exception:
            continue
    return results
