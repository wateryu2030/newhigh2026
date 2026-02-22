#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为自进化系统准备数据：自动下载并清洗指定标的、区间的 K 线，写入数据库或本地 CSV。
确保 train/val/test 有足够数据，满足 evolution 运行要求。
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)


def main():
    # 默认：平安银行 + 茅台，最近 400 个交易日约 1.5 年
    symbols = os.environ.get("EVOLUTION_SYMBOLS", "000001,600519").strip().split(",")
    days = int(os.environ.get("EVOLUTION_DAYS", "400"))
    end = datetime.now().date()
    start = (end - timedelta(days=days + 100)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    from data.data_loader import load_kline
    from evolution.data_split import ensure_ohlcv

    print("确保自进化数据（下载并清洗）")
    print(f"标的: {symbols}, 区间: {start} ~ {end_str}")
    print("-" * 50)

    for code in symbols:
        code = code.strip()
        if not code:
            continue
        df = load_kline(code, start, end_str, source="database")
        if df is None or len(df) < 200:
            df = load_kline(code, start, end_str, source="akshare")
        if df is None or len(df) < 200:
            print(f"  [SKIP] {code} 数据不足 200 条")
            continue
        df = ensure_ohlcv(df)
        if "date" not in df.columns and hasattr(df.index, "str"):
            df["date"] = df.index.astype(str).str[:10]
        # 写入 data/evolution 目录供 evolution 直接读
        os.makedirs(os.path.join(_ROOT, "data", "evolution"), exist_ok=True)
        path = os.path.join(_ROOT, "data", "evolution", f"{code}.csv")
        df.to_csv(path, index=False)
        print(f"  [OK] {code} -> {path} ({len(df)} 行)")
    print("-" * 50)
    print("完成。运行 evolution 时将从 data/evolution/*.csv 或数据库加载。")


if __name__ == "__main__":
    main()
