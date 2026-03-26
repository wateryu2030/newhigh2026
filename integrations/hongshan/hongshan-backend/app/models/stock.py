"""
股票数据模型
创建时间：2026-03-26
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StockBase(BaseModel):
    """股票基础信息"""
    symbol: str = Field(..., description="股票代码", example="600519")
    name: str = Field(..., description="股票名称", example="贵州茅台")


class StockQuote(StockBase):
    """股票行情"""
    price: float = Field(..., description="最新价", example=1688.00)
    change: float = Field(..., description="涨跌额", example=12.30)
    change_percent: float = Field(..., description="涨跌幅%", example=0.73)
    open: float = Field(..., description="开盘价", example=1680.00)
    high: float = Field(..., description="最高价", example=1695.00)
    low: float = Field(..., description="最低价", example=1675.00)
    pre_close: float = Field(..., description="昨收", example=1675.70)
    volume: int = Field(..., description="成交量", example=1234567)
    amount: float = Field(..., description="成交额", example=2080000000.00)
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class StockHistory(BaseModel):
    """股票历史数据"""
    symbol: str = Field(..., description="股票代码")
    date: str = Field(..., description="日期", example="2026-03-26")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")


class StockSearchResult(StockBase):
    """股票搜索结果"""
    market: str = Field(..., description="市场", example="SH")
    industry: Optional[str] = Field(None, description="行业", example="白酒")
