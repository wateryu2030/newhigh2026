"""
股票数据服务
封装 akshare 股票数据接口
创建时间：2026-03-26
"""
import akshare as ak
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StockService:
    """股票数据服务"""
    
    def __init__(self):
        self.cache = {}  # 简单内存缓存
        self.cache_ttl = 300  # 5 分钟
    
    def get_stock_quote(self, symbol: str) -> Optional[dict]:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码（如 600519）
            
        Returns:
            行情数据字典
        """
        try:
            # 检查缓存
            cache_key = f"quote_{symbol}"
            if cache_key in self.cache:
                data, timestamp = self.cache[cache_key]
                if (datetime.now() - timestamp).seconds < self.cache_ttl:
                    logger.info(f"使用缓存数据：{symbol}")
                    return data
            
            # 调用 akshare 获取实时行情
            # 使用 stock_zh_a_spot_em 获取 A 股实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 查找指定股票
            stock_data = df[df['代码'] == symbol]
            
            if stock_data.empty:
                logger.warning(f"未找到股票：{symbol}")
                return None
            
            row = stock_data.iloc[0]
            
            result = {
                "symbol": symbol,
                "name": row.get('名称', ''),
                "price": float(row.get('最新价', 0)),
                "change": float(row.get('涨跌额', 0)),
                "change_percent": float(row.get('涨跌幅', 0)),
                "open": float(row.get('今开', 0)),
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "pre_close": float(row.get('昨收', 0)),
                "volume": int(row.get('成交量', 0)),
                "amount": float(row.get('成交额', 0)),
                "timestamp": datetime.now()
            }
            
            # 更新缓存
            self.cache[cache_key] = (result, datetime.now())
            
            logger.info(f"获取行情成功：{symbol} - {result['name']}")
            return result
            
        except Exception as e:
            logger.error(f"获取行情失败：{symbol}, 错误：{str(e)}")
            return None
    
    def get_stock_history(
        self, 
        symbol: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily"
    ) -> List[dict]:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            period: 周期（daily/weekly/monthly）
            
        Returns:
            历史数据列表
        """
        try:
            # 默认获取最近 1 年数据
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            # 转换日期格式
            start_date = start_date.replace("-", "")
            end_date = end_date.replace("-", "")
            
            # 调用 akshare 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            # 转换为字典列表
            result = []
            for _, row in df.iterrows():
                result.append({
                    "symbol": symbol,
                    "date": str(row.get('日期', '')),
                    "open": float(row.get('开盘', 0)),
                    "high": float(row.get('最高', 0)),
                    "low": float(row.get('最低', 0)),
                    "close": float(row.get('收盘', 0)),
                    "volume": int(row.get('成交量', 0)),
                    "amount": float(row.get('成交额', 0))
                })
            
            logger.info(f"获取历史数据成功：{symbol}, {len(result)}条记录")
            return result
            
        except Exception as e:
            logger.error(f"获取历史数据失败：{symbol}, 错误：{str(e)}")
            return []
    
    def search_stocks(self, keyword: str) -> List[dict]:
        """
        搜索股票
        
        Args:
            keyword: 关键词（代码/名称/拼音）
            
        Returns:
            搜索结果列表
        """
        try:
            # 获取所有 A 股列表
            df = ak.stock_info_a_code_name()
            
            # 搜索（支持代码或名称模糊匹配）
            mask = df['code'].str.contains(keyword, case=False, na=False) | \
                   df['name'].str.contains(keyword, case=False, na=False)
            
            result_df = df[mask]
            
            result = []
            for _, row in result_df.iterrows():
                result.append({
                    "symbol": row['code'],
                    "name": row['name'],
                    "market": "SH" if row['code'].startswith('6') else "SZ"
                })
            
            logger.info(f"搜索股票成功：{keyword}, 找到{len(result)}条记录")
            return result
            
        except Exception as e:
            logger.error(f"搜索股票失败：{keyword}, 错误：{str(e)}")
            return []


# 单例
stock_service = StockService()
