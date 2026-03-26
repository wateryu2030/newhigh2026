"""
股票行情 API - 集成 akshare
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date, datetime
import akshare as ak
import pandas as pd

from app.db import get_db
from sqlalchemy.orm import Session
from app.models.database import Stock, StockDailyBar
from app.services.cache import cache

router = APIRouter()


# ============== 实时行情 ==============

@router.get("/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """
    获取股票实时行情
    
    - symbol: 股票代码，如 600519
    """
    # 尝试从缓存获取
    cached = cache.get_stock_quote(symbol)
    if cached:
        return cached
    
    try:
        # 使用 akshare 获取实时行情
        stock_info = ak.stock_zh_a_spot_em()
        stock_data = stock_info[stock_info['代码'] == symbol]
        
        if stock_data.empty:
            raise HTTPException(status_code=404, detail="股票未找到")
        
        row = stock_data.iloc[0]
        
        result = {
            "symbol": symbol,
            "name": row['名称'],
            "current_price": float(row['最新价']),
            "change": float(row['涨跌额']),
            "change_percent": float(row['涨跌幅']),
            "open": float(row['今开']),
            "high": float(row['最高']),
            "low": float(row['最低']),
            "pre_close": float(row['昨收']),
            "volume": int(row['成交量']),
            "amount": float(row['成交额']),
            "timestamp": datetime.now().isoformat()
        }
        
        # 写入缓存 (1 分钟)
        cache.set_stock_quote(symbol, result, ttl=60)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"


@router.get("/quotes")
async def get_multiple_quotes(symbols: str = Query(..., description="逗号分隔的股票代码列表")):
    """批量获取股票行情"""
    symbol_list = [s.strip() for s in symbols.split(',')]
    results = []
    
    for symbol in symbol_list:
        try:
            quote = await get_stock_quote(symbol)
            results.append(quote)
        except HTTPException:
            continue
    
    return {"quotes": results, "count": len(results)}


@router.get("/{symbol}/history")


# ============== 历史行情 ==============

@router.get("/{symbol}/history")
async def get_stock_history(
    symbol: str,
    start_date: date = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="结束日期 YYYY-MM-DD"),
    adjust: str = Query("qfq", description="复权类型：qfq-前复权，hfq-后复权，none-不复权")
):
    """获取股票历史行情（日线）"""
    try:
        # 使用 akshare 获取历史行情
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust=adjust
        )
        
        if df.empty:
            return {"data": [], "count": 0}
        
        # 转换为列表
        records = []
        for _, row in df.iterrows():
            records.append({
                "date": str(row['日期']),
                "open": float(row['开盘']),
                "high": float(row['最高']),
                "low": float(row['最低']),
                "close": float(row['收盘']),
                "volume": int(row['成交量']),
                "amount": float(row['成交额']),
                "change_percent": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
            })
        
        return {"data": records, "count": len(records)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史行情失败：{str(e)}")


# ============== K 线数据 ==============

@router.get("/{symbol}/kline")
async def get_kline_data(
    symbol: str,
    period: str = Query("daily", description="周期：daily-日线，weekly-周线，monthly-月线"),
    limit: int = Query(100, description="返回数据条数", le=1000)
):
    """获取 K 线数据"""
    try:
        # 计算日期范围
        end_date = datetime.now()
        start_date = datetime.now()
        
        if period == "daily":
            start_date = datetime(end_date.year, end_date.month, end_date.day - limit)
        elif period == "weekly":
            start_date = datetime(end_date.year - limit // 52, end_date.month, end_date.day)
        else:
            start_date = datetime(end_date.year - limit // 12, end_date.month, end_date.day)
        
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq"
        )
        
        if df.empty:
            return {"data": [], "count": 0}
        
        # 取最近 limit 条
        df = df.tail(limit)
        
        # 转换为 K 线格式
        kline_data = []
        for _, row in df.iterrows():
            kline_data.append({
                "time": str(row['日期']),
                "open": float(row['开盘']),
                "high": float(row['最高']),
                "low": float(row['最低']),
                "close": float(row['收盘']),
                "volume": int(row['成交量'])
            })
        
        return {"data": kline_data, "count": len(kline_data)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 K 线数据失败：{str(e)}")


# ============== 股票信息 ==============

@router.get("/{symbol}/info")
async def get_stock_info(symbol: str):
    """获取股票基本信息"""
    try:
        # 获取股票基本信息
        stock_info = ak.stock_individual_info_em(symbol=symbol)
        
        # 获取实时行情用于补充数据
        quote = await get_stock_quote(symbol)
        
        # 转换信息为字典
        info_dict = {}
        for _, row in stock_info.iterrows():
            info_dict[row['item']] = row['value']
        
        return {
            "symbol": symbol,
            "name": quote['name'],
            "exchange": "SH" if symbol.startswith('6') else "SZ",
            "industry": info_dict.get('行业', ''),
            "sector": info_dict.get('板块', ''),
            "list_date": info_dict.get('上市日期', ''),
            "total_shares": info_dict.get('总股本', ''),
            "circulating_shares": info_dict.get('流通股', ''),
            "pe_ratio": info_dict.get('市盈率 - 动态', ''),
            "pb_ratio": info_dict.get('市净率', ''),
            "current_price": quote['current_price']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票信息失败：{str(e)}")


# ============== 股票搜索 ==============

@router.get("/search")
async def search_stocks(keyword: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索股票"""
    try:
        # 获取 A 股列表
        stock_list = ak.stock_info_a_code_name()
        
        # 搜索代码或名称
        results = stock_list[
            stock_list['code'].str.contains(keyword, case=False) |
            stock_list['name'].str.contains(keyword, case=False, na=False)
        ].head(20)
        
        return {
            "data": [
                {"symbol": row['code'], "name": row['name']}
                for _, row in results.iterrows()
            ],
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")
