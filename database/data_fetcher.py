#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取器 - 从 AKShare 获取数据并存储到数据库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from akshare.stock_feature.stock_hist_em import stock_zh_a_hist
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import List
from database.db_schema import StockDatabase


def get_all_a_share_symbols() -> List[str]:
    """获取沪深京 A 股全部股票代码（6 位字符串）。"""
    try:
        from akshare.stock.stock_info import stock_info_a_code_name
        df = stock_info_a_code_name()
        if df is None or df.empty:
            return []
        if "code" not in df.columns:
            return []
        codes = df["code"].astype(str).str.strip().str.zfill(6)
        return [c for c in codes.unique().tolist() if c.isdigit() and len(c) == 6]
    except Exception as e:
        print(f"⚠️  获取 A 股列表失败: {e}")
        return []


def get_pool_symbols(data_dir: str = "data") -> List[str]:
    """从策略用到的所有 CSV 股票池中收集唯一股票代码（纯数字，如 600745）。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, data_dir) if not os.path.isabs(data_dir) else data_dir
    symbols = set()
    files_columns = [
        ("industry_stock_map.csv", "代码"),
        ("tech_leader_stocks.csv", "代码"),
        ("consume_leader_stocks.csv", "代码"),
        ("etf_list.csv", "代码"),
    ]
    for filename, col in files_columns:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            if col not in df.columns:
                continue
            for v in df[col].dropna().astype(str):
                v = v.strip()
                if not v or v in ("nan", "None"):
                    continue
                # 去掉 .XSHG / .XSHE 得到纯代码
                if "." in v:
                    v = v.split(".")[0]
                if v.isdigit() and len(v) == 6:
                    symbols.add(v)
        except Exception:
            continue
    return sorted(symbols)


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, db_path="data/astock.db"):
        self.db = StockDatabase(db_path)
    
    def fetch_stock_data(self, symbol: str, start_date: str = None, end_date: str = None, 
                        adjust: str = "qfq"):
        """
        获取单只股票数据并存储
        
        Args:
            symbol: 股票代码（如 "600745"）
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            adjust: 复权类型 "qfq"前复权/"hfq"后复权/""不复权
        """
        if not start_date:
            start_date = "20200101"
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        print(f"获取 {symbol} 数据: {start_date} 至 {end_date}")
        
        try:
            # 获取数据
            df = stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df is None or len(df) == 0:
                print(f"⚠️  {symbol} 未获取到数据")
                return False
            
            # 确定交易所和 order_book_id
            if symbol.startswith('6'):
                order_book_id = f"{symbol}.XSHG"
                market = "CN"
            else:
                order_book_id = f"{symbol}.XSHE"
                market = "CN"
            
            # 保存股票基本信息
            self.db.add_stock(
                order_book_id=order_book_id,
                symbol=symbol,
                name=None,  # 可以从其他接口获取
                market=market,
                listed_date=None,
                de_listed_date=None,
                type="CS"
            )
            
            # 保存日线数据
            self.db.add_daily_bars(order_book_id, df)
            
            print(f"✅ {symbol} ({order_book_id}) 数据获取成功: {len(df)} 条")
            return True
            
        except Exception as e:
            print(f"❌ 获取 {symbol} 数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def fetch_multiple_stocks(self, symbols: List[str], start_date: str = None, 
                             end_date: str = None, delay: float = 0.1):
        """批量获取多只股票数据"""
        print(f"\n开始批量获取 {len(symbols)} 只股票数据...")
        success_count = 0
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 处理 {symbol}...")
            if self.fetch_stock_data(symbol, start_date, end_date):
                success_count += 1
            
            # 避免请求过快
            if i < len(symbols):
                time.sleep(delay)
        
        print(f"\n✅ 批量获取完成: {success_count}/{len(symbols)} 成功")
        return success_count
    
    def fetch_wentai_data(self):
        """获取闻泰科技数据（示例）"""
        return self.fetch_stock_data("600745", "20200101", datetime.now().strftime("%Y%m%d"))

    def fetch_pool_stocks(self, start_date: str = None, end_date: str = None, data_dir: str = "data",
                          delay: float = 0.15) -> int:
        """
        全量同步股票池：从 data 目录下所有策略用到的 CSV 中收集股票代码，并拉取这些股票的日线数据写入数据库。
        用于多标的策略（如策略2/策略1）回测前补全数据，减少「No market data」。
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        symbols = get_pool_symbols(data_dir)
        if not symbols:
            print("未找到任何股票池文件或代码，请先确保 data/ 下存在 industry_stock_map.csv 或 tech_leader_stocks.csv 等")
            return 0
        print(f"股票池共 {len(symbols)} 只，将拉取 {start_date} 至 {end_date} 的日线数据")
        return self.fetch_multiple_stocks(symbols, start_date, end_date, delay=delay)

    def fetch_all_a_stocks(
        self,
        start_date: str = None,
        end_date: str = None,
        delay: float = 0.12,
        skip_existing: bool = True,
    ) -> int:
        """
        全量导入 A 股日线：获取沪深京全部股票列表，逐只拉取日线并写入数据库。
        skip_existing=True 时，若某只股票在区间内已有数据则跳过，便于断点续传。
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        symbols = get_all_a_share_symbols()
        if not symbols:
            return 0
        to_fetch = symbols
        if skip_existing:
            start_d = start_date[:4] + "-" + start_date[4:6] + "-" + start_date[6:8]
            end_d = end_date[:4] + "-" + end_date[4:6] + "-" + end_date[6:8]
            to_fetch = []
            for sym in symbols:
                ob = f"{sym}.XSHG" if sym.startswith("6") else f"{sym}.XSHE"
                bars = self.db.get_daily_bars(ob, start_d, end_d)
                if bars is None or (hasattr(bars, "__len__") and len(bars) < 10):
                    to_fetch.append(sym)
            print(f"共 {len(symbols)} 只 A 股，其中 {len(to_fetch)} 只需拉取（已跳过有数据的）")
        else:
            print(f"共 {len(symbols)} 只 A 股，将拉取 {start_date} 至 {end_date} 的日线数据")
        if not to_fetch:
            print("无需拉取新数据")
            return 0
        return self.fetch_multiple_stocks(to_fetch, start_date, end_date, delay=delay)
    
    def update_trading_calendar(self, start_date: str = "20200101", end_date: str = None):
        """更新交易日历（简化版：使用工作日作为代理）"""
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        dates = []
        current = start
        while current <= end:
            # 简单判断：周一到周五为交易日（实际应使用真实交易日历）
            if current.weekday() < 5:  # 0-4 为周一到周五
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        self.db.add_trading_dates(dates)
        print(f"✅ 交易日历已更新: {len(dates)} 个交易日")


if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # 获取闻泰科技数据
    print("=" * 60)
    print("获取闻泰科技（600745）数据")
    print("=" * 60)
    fetcher.fetch_wentai_data()
    
    # 更新交易日历
    print("\n" + "=" * 60)
    print("更新交易日历")
    print("=" * 60)
    fetcher.update_trading_calendar()
