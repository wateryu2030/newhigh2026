#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完善 AI 训练用数据：全 A 股（不含退市）补齐至指定天数（默认 400 天）并写入数据库。
先运行本脚本再运行 train_ai_model.py，可得到全市场、长周期训练数据。
支持断点续传：已有足够数据的标的将跳过。
"""
from __future__ import annotations
import os
import sys
import time
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def _order_book_id(code: str) -> str:
    if code.startswith("6") or (len(code) >= 2 and code[:2] in ("51", "58")):
        return f"{code}.XSHG"
    return f"{code}.XSHE"


def _ensure_one_symbol(
    code: str,
    days: int,
    db_path: str,
) -> bool:
    """单只标的：若本地不足 days 条则从 AKShare 拉取并写入 DB。返回是否执行了拉取。"""
    import pandas as pd
    from database.db_schema import StockDatabase
    from data.data_loader import load_kline

    end = datetime.now().date()
    start = (end - timedelta(days=days + 60)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    order_book_id = _order_book_id(code)
    try:
        db = StockDatabase(db_path)
        existing = db.get_daily_bars(order_book_id, start, end_str)
        if existing is not None and len(existing) >= days:
            return False
    except Exception:
        pass

    df = load_kline(code, start, end_str, source="akshare")
    if df is None or len(df) < days:
        return False

    try:
        from database.db_schema import StockDatabase
        db = StockDatabase(db_path)
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


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="完善 AI 训练数据：全 A 股补齐至指定天数")
    parser.add_argument("--days", type=int, default=400, help="目标历史天数（默认 400）")
    parser.add_argument("--delay", type=float, default=0.15, help="每只请求间隔(秒)，避免限流")
    parser.add_argument("--limit", type=int, default=None, help="仅处理前 N 只（测试用）")
    parser.add_argument("--no-skip", action="store_true", help="不跳过已有数据，强制重新拉取")
    args = parser.parse_args()

    days = max(60, args.days)
    db_path = os.path.join(ROOT, "data", "astock.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print("1. 获取 A 股列表（不含退市）...")
    symbols = []
    try:
        from data.stock_pool import get_a_share_symbols
        symbols = get_a_share_symbols(exclude_delisted=True)
    except Exception as e:
        print(f"   stock_pool 获取失败: {e}")
    if not symbols:
        try:
            from database.data_fetcher import get_all_a_share_symbols
            symbols = get_all_a_share_symbols()
        except Exception as e2:
            print(f"   data_fetcher 获取失败: {e2}")
    if not symbols:
        print("   未获取到股票列表，请检查网络与 akshare")
        return 1
    if args.limit:
        symbols = symbols[: args.limit]
        print(f"   共 {len(symbols)} 只（已限制前 {args.limit} 只）")
    else:
        print(f"   共 {len(symbols)} 只")

    if not args.no_skip:
        from database.db_schema import StockDatabase
        start = (datetime.now().date() - timedelta(days=days + 60)).strftime("%Y-%m-%d")
        end_str = datetime.now().date().strftime("%Y-%m-%d")
        db = StockDatabase(db_path)
        need_fetch = []
        for code in symbols:
            ob = _order_book_id(code)
            bars = db.get_daily_bars(ob, start, end_str)
            if bars is None or len(bars) < days:
                need_fetch.append(code)
        print(f"2. 其中 {len(need_fetch)} 只需补齐至 {days} 天（已跳过已有数据的）")
        symbols = need_fetch
    else:
        print(f"2. 将逐只拉取/覆盖至 {days} 天...")

    if not symbols:
        print("无需拉取新数据。可直接运行: python train_ai_model.py")
        return 0

    fetched = 0
    for i, code in enumerate(symbols, 1):
        if _ensure_one_symbol(code, days, db_path):
            fetched += 1
            print(f"   [{i}/{len(symbols)}] 补齐 {code} ({_order_book_id(code)})")
        elif i % 100 == 0 or i == len(symbols):
            print(f"   [{i}/{len(symbols)}] 已检查...")
        if i < len(symbols):
            time.sleep(args.delay)

    print(f"\n完成。本次补齐 {fetched} 只。可运行: python train_ai_model.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
