#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件策略 + 多周期回测入口。
根据 strategy / timeframe 参数加载日线、重采样、运行策略生成 signals，并计算净值曲线与驾驶舱数据。
"""
import os
import sys
import json
import argparse

_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(_root)
sys.path.insert(0, _root)


def run_plugin_backtest(
    strategy_id: str,
    stock_code: str,
    start_date: str,
    end_date: str,
    timeframe: str = "D",
    param_overrides: dict = None,
) -> dict:
    """
    执行插件策略回测，返回与 run_backtest_db 输出兼容的 result 字典（含 strategy_name, timeframe）。
    param_overrides: 可选，策略构造参数，如 {"fast": 10, "slow": 30} 用于参数优化。
    """
    from database.db_schema import StockDatabase
    from core.timeframe import resample_kline, normalize_timeframe
    from strategies import get_plugin_strategy
    from core.prediction import predict_trend
    from core.scoring import score_strategy

    tf = normalize_timeframe(timeframe)
    strategy = get_plugin_strategy(strategy_id, **(param_overrides or {}))
    if strategy is None:
        return {"error": f"未知策略: {strategy_id}", "strategy_name": strategy_id, "timeframe": tf}

    db_path = os.path.join(_root, "data", "astock.db")
    if not os.path.exists(db_path):
        return {"error": "数据库不存在", "strategy_name": strategy.name, "timeframe": tf}

    db = StockDatabase(db_path)
    df = db.get_daily_bars(stock_code, start_date, end_date)
    if df is None or len(df) == 0:
        return {"error": "无日线数据", "strategy_name": strategy.name, "timeframe": tf}

    df = resample_kline(df, tf)
    if len(df) == 0:
        return {"error": "重采样后无数据", "strategy_name": strategy.name, "timeframe": tf}

    if "date" not in df.columns and df.index is not None:
        df["date"] = df.index.astype(str).str[:10]

    # 对需要指数数据的策略（如 swing_newhigh）加载沪深300
    index_df = None
    if strategy_id == "swing_newhigh":
        index_df = db.get_daily_bars("000300.XSHG", start_date, end_date)
        if index_df is not None and len(index_df) >= 60:
            index_df = index_df.copy()
            if "date" not in index_df.columns and index_df.index is not None:
                index_df["date"] = index_df.index.astype(str).str[:10]

    kwargs = {}
    if index_df is not None:
        kwargs["index_df"] = index_df
    signals = strategy.generate_signals(df, **kwargs)
    signals = [s for s in signals if s.get("type") in ("BUY", "SELL") and s.get("date")]

    # 按信号简单计算净值：有 BUY 则持仓，SELL 则空仓；持仓时净值 = 净值 * (close/prev_close)
    signal_dates = {s["date"]: s["type"] for s in signals}
    dates = df["date"].tolist()
    closes = df["close"].tolist()
    nav = 1.0
    curve = []
    position = 0
    for i, d in enumerate(dates):
        action = signal_dates.get(d)
        if action == "BUY":
            position = 1
        elif action == "SELL":
            position = 0
        if i > 0 and position == 1 and closes[i - 1] and closes[i - 1] != 0:
            nav *= closes[i] / closes[i - 1]
        curve.append({"date": d, "value": round(nav, 6)})

    # K 线列表（与现有格式一致）
    kline = []
    for idx, row in df.iterrows():
        d = str(row.get("date", idx))[:10]
        kline.append({
            "date": d,
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "close": float(row.get("close", 0)),
            "volume": float(row.get("volume", 0)),
        })

    # 持有净值
    hold_curve = [{"date": kline[0]["date"], "value": 1.0}]
    for i in range(1, len(kline)):
        prev_c, cur_c = kline[i - 1]["close"], kline[i]["close"]
        if prev_c and prev_c != 0:
            nav_hold = hold_curve[-1]["value"] * (cur_c / prev_c)
        else:
            nav_hold = hold_curve[-1]["value"]
        hold_curve.append({"date": kline[i]["date"], "value": round(nav_hold, 6)})

    # 统一 signals 格式（与 core.signals 一致供前端）
    out_signals = []
    for s in signals:
        out_signals.append({
            "date": s["date"],
            "type": s["type"].lower(),
            "price": float(s.get("price", 0)),
            "reason": s.get("reason", ""),
            "reasons": [s.get("reason", "")],
        })

    markers = [
        {
            "name": s["type"],
            "value": s["type"],
            "coord": [s["date"], float(s.get("price", 0))],
            "itemStyle": {"color": "green" if s["type"] == "BUY" else "red"},
            "reason": s.get("reason", ""),
        }
        for s in signals
    ]

    try:
        prediction = predict_trend(df)
    except Exception:
        prediction = {"trend": "SIDEWAYS", "score": 0.0}

    # 简单统计
    trade_count = len([x for x in signals if x.get("type") in ("BUY", "SELL")])
    final_nav = curve[-1]["value"] if curve else 1.0
    total_return = (final_nav - 1.0) if curve else 0.0
    hold_final = hold_curve[-1]["value"] if hold_curve else 1.0
    max_dd = 0.0
    peak = 1.0
    for p in curve:
        v = p["value"]
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

    out = {
        "summary": {"total_returns": total_return, "return_rate": total_return, "win_rate": None, "max_drawdown": max_dd},
        "curve": curve,
        "holdCurve": hold_curve,
        "kline": kline,
        "signals": out_signals,
        "markers": markers,
        "prediction": prediction,
        "stats": {
            "tradeCount": trade_count,
            "winRate": None,
            "maxDrawdown": max_dd,
            "return": total_return,
        },
        "buyZones": [],
        "sellZones": [],
        "futureProbability": {"up": None, "sideways": None, "down": None},
        "futurePriceRange": {"low": None, "high": None, "horizonDays": 5},
        "strategy_name": strategy.name,
        "timeframe": tf,
    }

    try:
        strategy_score, strategy_grade = score_strategy(out["stats"])
        out["strategy_score"] = strategy_score
        out["strategy_grade"] = strategy_grade
    except Exception:
        out["strategy_score"] = None
        out["strategy_grade"] = None

    # 未来区间（与 run_backtest_db 一致）
    if len(kline) >= 5:
        last_close = float(kline[-1]["close"])
        if last_close > 0:
            n = min(14, len(kline) - 1)
            ranges = [abs(float(kline[-1 - i]["high"]) - float(kline[-1 - i]["low"])) for i in range(n)]
            atr = sum(ranges) / len(ranges) if ranges else last_close * 0.02
            out["futurePriceRange"] = {"low": round(last_close - 2 * atr, 2), "high": round(last_close + 2 * atr, 2), "horizonDays": 5}
            trend = (last_close - float(kline[-5]["close"])) / float(kline[-5]["close"]) if kline[-5]["close"] else 0
            if trend > 0.02:
                out["futureProbability"] = {"up": 0.5, "sideways": 0.3, "down": 0.2}
            elif trend < -0.02:
                out["futureProbability"] = {"up": 0.2, "sideways": 0.3, "down": 0.5}
            else:
                out["futureProbability"] = {"up": 0.33, "sideways": 0.34, "down": 0.33}

    return out


def main():
    parser = argparse.ArgumentParser(description="插件策略多周期回测")
    parser.add_argument("strategy", help="策略 id: ma_cross, rsi, macd, breakout")
    parser.add_argument("stock_code", help="股票代码")
    parser.add_argument("start_date", nargs="?", default="2024-01-01", help="开始日期")
    parser.add_argument("end_date", nargs="?", default="2024-12-31", help="结束日期")
    parser.add_argument("-t", "--timeframe", default="D", choices=["D", "W", "M"], help="周期: D=日线 W=周线 M=月线")
    args = parser.parse_args()

    result = run_plugin_backtest(args.strategy, args.stock_code, args.start_date, args.end_date, args.timeframe)
    if result.get("error"):
        print(result["error"])
        sys.exit(1)
    os.makedirs("output", exist_ok=True)
    json_path = os.path.join(_root, "output", "last_backtest_result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("strategy_name:", result.get("strategy_name"))
    print("timeframe:", result.get("timeframe"))
    print("signals count:", len(result.get("signals", [])))
    print("output:", json_path)


if __name__ == "__main__":
    main()
