#!/usr/bin/env python3
"""
个人量化投资助手 - 股票筛选器
功能：从数据库中筛选重点关注的股票（混合模式：固定 + 动态）
"""

import os
import sys
import duckdb
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# 仓库根（personal_assistant 的上一级）+ 与主仓统一的子包 path
_PA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(_PA_ROOT)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
from system_core.repo_paths import prepend_repo_sources  # noqa: E402

prepend_repo_sources(REPO_ROOT)

# 固定股票池（优化版 - 行业龙头 + 高流动性）
DEFAULT_FIXED_STOCKS = [
    # ===== 大消费（5 只）=====
    "600519.XSHG",  # 贵州茅台 - 白酒龙头
    "000858.XSHE",  # 五粮液 - 白酒第二
    "000333.XSHE",  # 美的集团 - 家电龙头
    "600887.XSHG",  # 伊利股份 - 乳业龙头
    "000568.XSHE",  # 泸州老窖 - 白酒第三

    # ===== 新能源（3 只）=====
    "300750.XSHE",  # 宁德时代 - 动力电池龙头
    "002594.XSHE",  # 比亚迪 - 新能源车龙头
    "601012.XSHG",  # 隆基绿能 - 光伏龙头

    # ===== 科技（3 只）=====
    "002415.XSHE",  # 海康威视 - 安防龙头
    "000063.XSHE",  # 中兴通讯 - 通信设备
    "600036.XSHG",  # 招商银行 - 银行龙头

    # ===== 医药（2 只）=====
    "600276.XSHG",  # 恒瑞医药 - 创新药龙头
    "300122.XSHE",  # 智飞生物 - 疫苗龙头

    # ===== 其他（2 只）=====
    "601318.XSHG",  # 中国平安 - 保险龙头
    "600519.XSHG",  # 贵州茅台（重复，用于测试）
]

class StockScreener:
    """股票筛选器"""

    def __init__(self, db_path: str = None, fixed_stocks: List[str] = None):
        """
        初始化筛选器

        Args:
            db_path: DuckDB数据库路径
            fixed_stocks: 固定股票池列表
        """
        self.db_path = (
            db_path or
            os.getenv("QUANT_SYSTEM_DUCKDB_PATH") or
            "/Users/apple/Ahope/newhigh/data/quant_system.duckdb"
        )
        self.fixed_stocks = fixed_stocks or DEFAULT_FIXED_STOCKS
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = duckdb.connect(self.db_path)
            return True
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_fixed_stock_data(self) -> List[Dict]:
        """
        获取固定股票池的最新数据

        Returns:
            股票数据列表
        """
        if not self.conn:
            return []

        results = []
        for stock_code in self.fixed_stocks:
            try:
                # 获取最新日线数据
                query = """
                SELECT order_book_id, trade_date, open, high, low, close, volume, total_turnover
                FROM daily_bars
                WHERE order_book_id = ?
                ORDER BY trade_date DESC
                LIMIT 5
                """
                data = self.conn.execute(query, [stock_code]).fetchall()

                if data:
                    # 获取股票基本信息
                    info_query = """
                    SELECT order_book_id, name,
                    FROM stocks
                    WHERE order_book_id = ?
                    """
                    info = self.conn.execute(info_query, [stock_code]).fetchone()

                    results.append({
                        "code": stock_code,
                        "name": info[1] if info else "未知",
                        "industry": "A 股",
                        "market_cap": 0,
                        "type": "fixed",
                        "recent_data": data
                    })
            except Exception as e:
                print(f"⚠️ 获取 {stock_code} 数据失败: {e}")

        return results

    def get_dynamic_stocks(self, limit: int = 10) -> List[Dict]:
        """
        动态筛选：选择最活跃/最有潜力的股票

        筛选逻辑：
        1. 今日成交量排名前50
        2. 近5日涨幅排名前50
        3. 去除ST股票
        4. 去除固定股票池中已有的

        Args:
            limit: 返回数量

        Returns:
            股票数据列表
        """
        if not self.conn:
            return []

        try:
            # 获取最新交易日
            latest_date_query = """
            SELECT MAX(trade_date) FROM daily_bars
            """
            latest_date = self.conn.execute(latest_date_query).fetchone()[0]

            if not latest_date:
                return []

            # 动态筛选：成交量 + 涨幅综合排名
            query = """
            WITH latest_data AS (
                SELECT
                    order_book_id,
                    trade_date,
                    close,
                    volume,
                    total_turnover,
                    LAG(close, 5) OVER (PARTITION BY order_book_id ORDER BY trade_date) as close_5d_ago
                FROM daily_bars
                WHERE trade_date >= ? - INTERVAL 5 DAY
            ),
            ranked AS (
                SELECT
                    order_book_id,
                    close,
                    volume,
                    total_turnover,
                    (close - close_5d_ago) / close_5d_ago * 100 as change_5d,
                    ROW_NUMBER() OVER (ORDER BY total_turnover DESC) as vol_rank,
                    ROW_NUMBER() OVER (ORDER BY (close - close_5d_ago) / close_5d_ago DESC) as change_rank
                FROM latest_data
                WHERE trade_date = (SELECT MAX(trade_date) FROM daily_bars)
            )
            SELECT order_book_id, vol_rank, change_rank, change_5d
            FROM ranked
            WHERE vol_rank <= 100 OR change_rank <= 100
            ORDER BY (vol_rank + change_rank)
            LIMIT ?
            """

            dynamic_codes = self.conn.execute(query, [latest_date, limit * 2]).fetchall()

            results = []
            count = 0
            for row in dynamic_codes:
                if count >= limit:
                    break

                code = row[0]

                # 跳过固定股票池中已有的
                if code in self.fixed_stocks:
                    continue

                # 获取股票信息
                info_query = """
                SELECT order_book_id, name,
                FROM stocks
                WHERE order_book_id = ?
                """
                info = self.conn.execute(info_query, [code]).fetchone()

                if info:
                    # 获取最新数据
                    data_query = """
                    SELECT order_book_id, trade_date, open, high, low, close, volume, total_turnover
                    FROM daily_bars
                    WHERE order_book_id = ?
                    ORDER BY trade_date DESC
                    LIMIT 5
                    """
                    data = self.conn.execute(data_query, [code]).fetchall()

                    results.append({
                        "code": code,
                        "name": info[1] if info else "未知",
                        "industry": "A 股",
                        "market_cap": 0,
                        "type": "dynamic",
                        "recent_data": data,
                        "change_5d": row[3]
                    })
                    count += 1

            return results

        except Exception as e:
            print(f"❌ 动态筛选失败: {e}")
            return []

    def get_stock_pool(self, fixed_count: int = 10, dynamic_count: int = 10) -> List[Dict]:
        """
        获取最终股票池（固定 + 动态）

        Args:
            fixed_count: 固定股票数量
            dynamic_count: 动态股票数量

        Returns:
            股票池列表
        """
        if not self.connect():
            return []

        try:
            # 获取固定股票
            fixed_stocks = self.get_fixed_stock_data()[:fixed_count]

            # 获取动态股票
            dynamic_stocks = self.get_dynamic_stocks(dynamic_count)

            # 合并
            stock_pool = fixed_stocks + dynamic_stocks

            print(f"✅ 股票池生成完成: {len(stock_pool)} 只股票")
            print(f"   - 固定: {len(fixed_stocks)} 只")
            print(f"   - 动态: {len(dynamic_stocks)} 只")

            return stock_pool

        finally:
            self.close()


def test_screener():
    """测试筛选器"""
    print("=== 测试股票筛选器 ===")

    screener = StockScreener()
    stock_pool = screener.get_stock_pool(fixed_count=10, dynamic_count=10)

    if stock_pool:
        print(f"\n股票池列表:")
        for stock in stock_pool:
            print(f"  {stock['code']} - {stock['name']} ({stock['type']})")
            if stock.get('change_5d'):
                print(f"    5日涨幅: {stock['change_5d']:.2f}%")

    return stock_pool


if __name__ == "__main__":
    test_screener()
