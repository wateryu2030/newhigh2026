#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用数据库数据源运行回测
"""
import sys
import os
import subprocess

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)


def main():
    if len(sys.argv) < 2:
        print("用法: python run_backtest_db.py <策略文件> [开始日期] [结束日期]")
        print("示例: python run_backtest_db.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30")
        sys.exit(1)

    strategy_file = sys.argv[1]
    start_date = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    end_date = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"

    if not os.path.exists(strategy_file):
        print(f"策略文件不存在: {strategy_file}")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)
    strategy_abs = os.path.abspath(strategy_file)

    print(f"运行策略: {strategy_file}")
    print(f"回测期间: {start_date} 至 {end_date}")
    print("使用数据库数据源（SQLite）")
    print("-" * 50)

    # 检查数据库是否存在
    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        print("⚠️  数据库不存在，正在获取数据...")
        from database.data_fetcher import DataFetcher
        fetcher = DataFetcher()
        fetcher.fetch_wentai_data()
        print("✅ 数据获取完成")

    site = next((p for p in sys.path if "venv" in p and "site-packages" in p), None)
    if not site:
        print("❌ 未找到 venv")
        sys.exit(1)

    code = f'''
import sys, os
root = {repr(_root)}
strategy_abs_path = {repr(strategy_abs)}
# 先导入 rqalpha（此时 cwd 仍为 /tmp）
from rqalpha import run_func
os.chdir(root)

# 导入策略函数
import importlib.util
spec = importlib.util.spec_from_file_location("strategy", strategy_abs_path)
strategy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategy_module)

# 导入数据库数据源 Mod
from database.db_data_source_mod import DatabaseDataSourceMod

# 配置：使用数据库数据源 Mod
config = {{
    "base": {{
        "start_date": {repr(start_date)},
        "end_date": {repr(end_date)},
        "frequency": "1d",
        "accounts": {{"stock": 1000000}},
    }},
    "mod": {{
        "sys_analyser": {{"enabled": True, "output_file": os.path.join(root, "output", "last_backtest_result.pkl")}},
        "sys_progress": {{"enabled": True}},
        "sys_simulation": {{"enabled": True}},
        "sys_accounts": {{"enabled": True}},
        "db_data_source": {{
            "enabled": True,
            "lib": "database.db_data_source_mod",
            "db_path": os.path.join(root, "data", "astock.db"),
        }},
    }},
    "extra": {{"log_level": "INFO", "stock_code": os.environ.get("STOCK_CODE", "")}},
}}

# 构建 user_funcs，只包含存在的函数（不包含 None）
user_funcs = {{
    "init": strategy_module.init,
    "handle_bar": strategy_module.handle_bar,
}}
if hasattr(strategy_module, "before_trading") and strategy_module.before_trading is not None:
    user_funcs["before_trading"] = strategy_module.before_trading
if hasattr(strategy_module, "after_trading") and strategy_module.after_trading is not None:
    user_funcs["after_trading"] = strategy_module.after_trading

try:
    result = run_func(config=config, **user_funcs)
    print("\\n✅ 回测完成！")
    # 写出 JSON 供 Web 展示（指标 + 净值曲线 + 决策驾驶舱）
    import json
    import pickle
    import datetime as _dt
    pkl_path = os.path.join(root, "output", "last_backtest_result.pkl")
    json_path = os.path.join(root, "output", "last_backtest_result.json")
    start_date = {repr(start_date)}
    end_date = {repr(end_date)}
    stock_code = os.environ.get("STOCK_CODE", "")
    if os.path.exists(pkl_path):
        with open(pkl_path, "rb") as f:
            rd = pickle.load(f)
        def _to_json(v):
            if v is None: return None
            if hasattr(v, "item"):
                x = v.item()
                if isinstance(x, float) and (x != x or abs(x) == 1e300): return None
                return _to_json(x) if isinstance(x, (dict, list, tuple)) else x
            if hasattr(v, "tolist"): return [_to_json(x) for x in v.tolist()]
            if isinstance(v, (list, tuple)): return [_to_json(x) for x in v]
            if isinstance(v, dict): return {{k: _to_json(x) for k, x in v.items()}}
            if isinstance(v, float) and (v != v or abs(v) == 1e300): return None
            if isinstance(v, (_dt.date, _dt.datetime)): return str(v)[:10]
            if hasattr(v, "start_date") and hasattr(v, "end_date"): return {{"start_date": str(v.start_date), "end_date": str(v.end_date)}}
            try: json.dumps(v); return v
            except (TypeError, ValueError): return str(v)
        summary = rd.get("summary") or {{}}
        out = {{"summary": {{k: _to_json(v) for k, v in summary.items()}}}}
        if "portfolio" in rd and rd["portfolio"] is not None:
            try:
                pf = rd["portfolio"]
                if hasattr(pf, "index"):
                    dates = [str(d)[:10] for d in pf.index]
                    nav = pf["unit_net_value"] if "unit_net_value" in getattr(pf, "columns", []) else pf.iloc[:, 0]
                    out["curve"] = [{{"date": d, "value": float(x) if x == x else None}} for d, x in zip(dates, nav)]
            except Exception:
                out["curve"] = []
        else:
            out["curve"] = []
        out["buyZones"] = []
        out["sellZones"] = []
        out["signals"] = []
        out["holdCurve"] = []
        out["kline"] = []
        out["futureProbability"] = {{"up": None, "sideways": None, "down": None}}
        out["futurePriceRange"] = {{"low": None, "high": None, "horizonDays": 5}}
        # Phase 4: 简单未来区间与概率（ATR 区间 + 占位概率）
        def _future_from_kline(kline_list, horizon_days=5):
            if not kline_list or len(kline_list) < 5: return None, None
            k = kline_list
            last_close = float(k[-1].get("close", 0))
            if last_close <= 0: return None, None
            n = min(14, len(k) - 1)
            ranges = [abs(float(k[-1-i].get("high", 0)) - float(k[-1-i].get("low", 0))) for i in range(n)]
            atr = sum(ranges) / len(ranges) if ranges else last_close * 0.02
            low = round(last_close - 2 * atr, 2)
            high = round(last_close + 2 * atr, 2)
            price_range = {{"low": low, "high": high, "horizonDays": horizon_days}}
            trend = (float(k[-1].get("close", 0)) - float(k[-5].get("close", 0))) / float(k[-5].get("close", 1)) if k[-5].get("close") else 0
            if trend > 0.02: prob = {{"up": 0.5, "sideways": 0.3, "down": 0.2}}
            elif trend < -0.02: prob = {{"up": 0.2, "sideways": 0.3, "down": 0.5}}
            else: prob = {{"up": 0.33, "sideways": 0.34, "down": 0.33}}
            return price_range, prob
        # Phase 1: K 线 + 持有曲线 + 从成交推导买卖区间与信号
        if stock_code:
            try:
                sys.path.insert(0, root)
                from database.db_schema import StockDatabase
                db = StockDatabase(os.path.join(root, "data", "astock.db"))
                df = db.get_daily_bars(stock_code, start_date, end_date)
                if df is not None and len(df) > 0:
                    kline = []
                    for idx, row in df.iterrows():
                        d = str(idx)[:10]
                        kline.append({{"date": d, "open": float(row.get("open", 0)), "high": float(row.get("high", 0)), "low": float(row.get("low", 0)), "close": float(row.get("close", 0)), "volume": float(row.get("volume", 0))}})
                    out["kline"] = kline
                    nav = 1.0
                    out["holdCurve"] = [{{"date": kline[0]["date"], "value": 1.0}}]
                    for i in range(1, len(kline)):
                        if kline[i-1]["close"] and kline[i-1]["close"] != 0:
                            nav *= kline[i]["close"] / kline[i-1]["close"]
                        out["holdCurve"].append({{"date": kline[i]["date"], "value": round(nav, 6)}})
                    pr, prob = _future_from_kline(out["kline"])
                    if pr: out["futurePriceRange"] = pr
                    if prob: out["futureProbability"] = prob
                    # 标准化信号与趋势预测（core.signals / core.prediction）
                    try:
                        from core.signals import generate_signals
                        from core.prediction import predict_trend
                        df["date"] = df.index.astype(str).str[:10]
                        df["ma5"] = df["close"].rolling(5, min_periods=1).mean()
                        df["ma20"] = df["close"].rolling(20, min_periods=1).mean()
                        tech_signals = generate_signals(df)
                        out["signals"] = [{{"date": s["date"], "type": s["type"].lower(), "price": float(s["price"]), "reason": s["reason"], "reasons": [s["reason"]]}} for s in tech_signals]
                        out["prediction"] = predict_trend(df)
                        out["markers"] = [{{"name": s["type"], "value": s["type"], "coord": [s["date"], float(s["price"])], "itemStyle": {{"color": "green" if s["type"] == "BUY" else "red"}}, "reason": s["reason"]}} for s in tech_signals]
                        s = summary
                        _wr = s.get("win_rate")
                        _md = s.get("max_drawdown")
                        _ret = s.get("total_returns") or s.get("return_rate")
                        out["stats"] = {{"winRate": float(_wr) if _wr is not None else None, "tradeCount": len(tech_signals), "maxDrawdown": float(_md) if _md is not None else None, "return": float(_ret) if _ret is not None else 0.0}}
                    except Exception as _e:
                        out["markers"] = []
                        out["prediction"] = {{"trend": "SIDEWAYS", "score": 0.0}}
                        out["stats"] = {{"winRate": None, "tradeCount": 0, "maxDrawdown": None, "return": 0.0}}
            except Exception as _e:
                pass
        if "markers" not in out:
            out["markers"] = []
        if "prediction" not in out:
            out["prediction"] = {{"trend": "SIDEWAYS", "score": 0.0}}
        if "stats" not in out:
            out["stats"] = {{"winRate": None, "tradeCount": 0, "maxDrawdown": None, "return": 0.0}}
        # 从 trades 推导 buyZones / sellZones（仅区间高亮；signals 已由 core.signals 标准化）
        try:
            trades = rd.get("trades") or (rd.get("sys_analyser") or {{}}).get("trades")
            if trades is not None and hasattr(trades, "iterrows"):
                buy_dates = []
                sell_dates = []
                for _, row in trades.iterrows():
                    dt = row.get("datetime") or row.get("trading_datetime") or row.get("date")
                    if dt is None: continue
                    d = str(dt)[:10]
                    qty = row.get("quantity", 0) or row.get("amount", 0) or 0
                    try: qty = float(qty)
                    except (TypeError, ValueError): continue
                    if qty > 0: buy_dates.append(d)
                    elif qty < 0: sell_dates.append(d)
                def _merge_zones(dates):
                    if not dates: return []
                    dates = sorted(set(dates))
                    zones = []
                    start = end = dates[0]
                    for d in dates[1:]:
                        try:
                            delta = (_dt.datetime.strptime(d, "%Y-%m-%d") - _dt.datetime.strptime(end, "%Y-%m-%d")).days
                            if delta <= 3: end = d
                            else:
                                zones.append({{"start": start, "end": end}})
                                start = end = d
                        except Exception: start = end = d
                    zones.append({{"start": start, "end": end}})
                    return zones
                out["buyZones"] = _merge_zones(buy_dates)
                out["sellZones"] = _merge_zones(sell_dates)
        except Exception:
            pass
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"\\n⚠️  回测过程出错: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

    env = {**os.environ}
    env["PYTHONPATH"] = site

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd="/tmp",
            env=env,
        )
        sys.exit(result.returncode)
    except Exception as e:
        print(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
