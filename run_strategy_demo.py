#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机构级策略模块 demo：加载数据、运行策略、输出选股、ETF 配置、组合权重与交易信号。
缺数据时自动拉取补齐。
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def _order_book_id(code: str) -> str:
    """6/51/58 开头为沪市，其余深市。"""
    if code.startswith("6") or (len(code) >= 2 and code[:2] in ("51", "58")):
        return f"{code}.XSHG"
    return f"{code}.XSHE"


def _ensure_symbol_data(symbol: str, days: int) -> bool:
    """若本地数据不足则从 AKShare 拉取并写入数据库。返回是否已补齐。"""
    import pandas as pd
    code = symbol.split(".")[0] if "." in symbol else symbol
    end = datetime.now().date()
    start = (end - timedelta(days=days + 30)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    start_ymd = start.replace("-", "")
    end_ymd = end_str.replace("-", "")
    try:
        from database.duckdb_backend import get_db_backend
        order_book_id = symbol if "." in symbol else _order_book_id(code)
        db = get_db_backend()
        existing = db.get_daily_bars(order_book_id, start, end_str)
        if existing is not None and len(existing) >= min(60, days):
            return False
        print(f"   补齐数据: {code} ({order_book_id})")
        df = None
        # ETF 优先用 fund_etf_hist_em
        if code in ("510300", "510500", "159915", "159919", "512000", "512100"):
            try:
                import akshare as ak
                raw = ak.fund_etf_hist_em(
                    symbol=code, period="daily",
                    start_date=start_ymd, end_date=end_ymd, adjust="qfq"
                )
                if raw is not None and len(raw) >= 60:
                    df = raw.rename(columns={
                        "日期": "date", "开盘": "open", "收盘": "close",
                        "最高": "high", "最低": "low", "成交量": "volume",
                    })
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        if df is None or len(df) < 60:
            from data.data_loader import load_kline
            df = load_kline(code, start, end_str, source="akshare")
        if df is None or len(df) < 60:
            return False
        # db.add_daily_bars 需要中文列名
        df_db = df.copy()
        if "date" in df_db.columns:
            df_db["日期"] = pd.to_datetime(df_db["date"])
        for en, cn in [("open", "开盘"), ("high", "最高"), ("low", "最低"), ("close", "收盘"), ("volume", "成交量")]:
            if en in df_db.columns and cn not in df_db.columns:
                df_db[cn] = df_db[en]
        if "成交额" not in df_db.columns:
            df_db["成交额"] = 0.0
        db.add_stock(order_book_id=order_book_id, symbol=code, name=None, market="CN", listed_date=None, de_listed_date=None, type="CS")
        db.add_daily_bars(order_book_id, df_db)
        return True
    except Exception:
        return False


def load_data_for_symbol(symbol: str, days: int = 120) -> "pd.DataFrame":
    """加载单标的 K 线；不足时先自动拉取再读。"""
    import pandas as pd
    end = datetime.now().date()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    code = symbol.split(".")[0] if "." in symbol else symbol
    try:
        from data.data_loader import load_kline
        df = load_kline(symbol, start, end_str, source="database")
        if df is None or len(df) < 60:
            _ensure_symbol_data(symbol, days)
            df = load_kline(symbol, start, end_str, source="database")
        if df is not None and len(df) >= 60:
            if "date" not in df.columns and df.index is not None:
                df = df.copy()
                df["date"] = df.index.astype(str).str[:10]
            return df
    except Exception:
        pass
    return pd.DataFrame()


def load_multi_symbols(symbols: list[str], days: int = 120) -> dict[str, "pd.DataFrame"]:
    """多标的 K 线；缺数据则自动拉取补齐。"""
    out = {}
    for s in symbols:
        code = s.split(".")[0] if "." in s else s
        df = load_data_for_symbol(code, days)
        if df is not None and len(df) > 0:
            key = s if "." in s else (s + ".XSHG" if s.startswith("6") else s + ".XSHE")
            out[key] = df
    return out


def load_index_data(days: int = 120, fallback_from: dict | None = None) -> "pd.DataFrame | None":
    """加载指数数据；无 000300 时用 510300 沪深300ETF 代替并自动拉取；仍无则用 fallback_from 中首个标的合成。"""
    import pandas as pd
    end = datetime.now().date()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    try:
        from data.data_loader import load_kline
        df = load_kline("000300", start, end_str, source="database")
        if df is None or len(df) < 60:
            df = load_kline("510300", start, end_str, source="database")
        if df is None or len(df) < 60:
            _ensure_symbol_data("510300", days)
            df = load_kline("510300", start, end_str, source="database")
        if df is not None and len(df) >= 60:
            if "date" not in df.columns and df.index is not None:
                df = df.copy()
                df["date"] = df.index.astype(str).str[:10]
            return df
    except Exception:
        pass
    # 无指数时用已有标的合成一个简易指数（仅用于 demo 展示）
    if fallback_from and len(fallback_from) > 0:
        first_key = next(iter(fallback_from))
        synth = fallback_from[first_key]
        if synth is not None and len(synth) >= 60:
            if "date" not in synth.columns and synth.index is not None:
                synth = synth.copy()
                synth["date"] = synth.index.astype(str).str[:10]
            print("   无指数数据，使用标的 " + first_key + " 合成指数")
            return synth
    return None


def main() -> None:
    import pandas as pd
    from strategies_pro import (
        TrendBreakoutStrategy,
        StrongPullbackStrategy,
        ETFRotationStrategy,
        MarketRegimeDetector,
        StrategyManager,
    )

    print("=" * 60)
    print("A股机构级策略模块 strategies_pro 示例")
    print("=" * 60)

    symbols = ["000001", "600519", "000858", "300750", "600745"]
    print("\n1. 加载数据（示例标的）...")
    market_data = load_multi_symbols(symbols, days=120)
    if not market_data:
        print("   无本地数据，使用模拟数据演示")
        import numpy as np
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now().date(), periods=100, freq="D")
        for s in ["000001.XSHE", "600519.XSHG"]:
            close = 100 * np.cumprod(1 + np.random.randn(100) * 0.02)
            market_data[s] = pd.DataFrame({
                "date": [d.strftime("%Y-%m-%d") for d in dates],
                "open": close * 0.99, "high": close * 1.01, "low": close * 0.98,
                "close": close, "volume": np.random.randint(1_000_000, 5_000_000, 100),
            })

    print(f"   已加载 {len(market_data)} 只标的")

    print("\n2. 市场环境识别...")
    index_df = load_index_data(days=120, fallback_from=market_data)
    detector = MarketRegimeDetector()
    if index_df is not None:
        regime = detector.detect(index_df)
        print(f"   当前市场: {regime.value}")
    else:
        print("   无指数数据，默认 NEUTRAL")

    print("\n3. 运行策略...")
    manager = StrategyManager()
    if index_df is not None:
        manager.set_index_data(index_df)
    combined = manager.get_combined_signals(market_data)

    print("\n4. 选股结果（各策略）...")
    trend = TrendBreakoutStrategy()
    pullback = StrongPullbackStrategy()
    etf = ETFRotationStrategy()
    trend_stocks = trend.select_stocks(market_data)
    pullback_stocks = pullback.select_stocks(market_data)
    etf_stocks = etf.select_stocks(market_data)
    print(f"   趋势突破: {trend_stocks or '(无)'}")
    print(f"   强势回调: {pullback_stocks or '(无)'}")
    print(f"   ETF轮动:  {etf_stocks or '(无)'}")

    print("\n5. ETF 配置...")
    print(f"   {etf_stocks or '无'}")

    print("\n6. 组合权重与交易信号...")
    if len(combined) > 0:
        print(combined.to_string(index=False))
    else:
        print("   (当前无信号)")

    print("\n完成。")


if __name__ == "__main__":
    main()
