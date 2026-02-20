#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步工具 - 增量更新股票数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.data_fetcher import DataFetcher
from database.db_schema import StockDatabase
from datetime import datetime, timedelta
import argparse


def sync_stock(symbol: str, days: int = 365):
    """同步单只股票数据"""
    fetcher = DataFetcher()
    
    # 计算日期范围
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    print(f"同步 {symbol} 数据（最近 {days} 天）...")
    return fetcher.fetch_stock_data(symbol, start_date, end_date)


def sync_stock_list(symbols: list, days: int = 365):
    """批量同步股票列表"""
    fetcher = DataFetcher()
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    return fetcher.fetch_multiple_stocks(symbols, start_date, end_date, delay=0.2)


def sync_wentai():
    """同步闻泰科技数据（示例）"""
    return sync_stock("600745", days=730)  # 2年数据


def sync_strategy_stocks():
    """同步策略中使用的股票数据"""
    # 从策略文件中提取股票代码
    strategy_stocks = [
        "600745",  # 闻泰科技
        "000001",  # 平安银行
        "600519",  # 贵州茅台
        "000858",  # 五粮液
    ]
    
    print("同步策略股票数据...")
    return sync_stock_list(strategy_stocks, days=730)


def update_all(days: int = 365):
    """更新所有已存储股票的数据"""
    db = StockDatabase()
    stocks = db.get_stocks()
    
    if len(stocks) == 0:
        print("数据库中没有股票，请先使用 sync_stock 或 sync_stock_list 添加股票")
        return
    
    symbols = [s[1] for s in stocks]  # 提取 symbol
    print(f"更新 {len(symbols)} 只股票的数据...")
    return sync_stock_list(symbols, days=days)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数据同步工具")
    parser.add_argument("--symbol", "-s", help="股票代码（如 600745）")
    parser.add_argument("--days", "-d", type=int, default=365, help="同步天数（默认365）")
    parser.add_argument("--wentai", action="store_true", help="同步闻泰科技数据")
    parser.add_argument("--strategy", action="store_true", help="同步策略股票数据")
    parser.add_argument("--update-all", action="store_true", help="更新所有股票数据")
    
    args = parser.parse_args()
    
    if args.wentai:
        sync_wentai()
    elif args.strategy:
        sync_strategy_stocks()
    elif args.update_all:
        update_all(args.days)
    elif args.symbol:
        sync_stock(args.symbol, args.days)
    else:
        print("使用示例:")
        print("  python sync_data.py --wentai              # 同步闻泰科技")
        print("  python sync_data.py --symbol 600745      # 同步指定股票")
        print("  python sync_data.py --strategy            # 同步策略股票")
        print("  python sync_data.py --update-all          # 更新所有股票")
