"""A 股数据连接器：通过 Tushare 拉取 A 股/北交所日线/分钟线，归一化为 core.OHLCV。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os

from core import OHLCV

try:
    import tushare as ts
    import pandas as pd
except ImportError:
    ts = None
    pd = None


def _normalize_symbol(code: str) -> str:
    """A 股/北交所代码转为带交易所后缀：600519->600519.SH, 000001->000001.SZ, 830799->830799.BSE。"""
    code = str(code).strip().split(".")[0]
    if not code:
        return code
    # 北交所：4/8/9 开头或 8 位
    if code.startswith(("4", "8", "9")) or len(code) == 8:
        return f"{code}.BSE"
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def _to_utc(dt: datetime) -> datetime:
    """若为 naive 则视为本地时间并转为 UTC（A 股 15:00 收盘）。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _init_tushare() -> bool:
    """初始化Tushare，设置token"""
    if ts is None:
        return False
    
    # 从环境变量获取token
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("警告: 未设置TUSHARE_TOKEN环境变量，Tushare连接器将无法使用")
        return False
    
    try:
        ts.set_token(token)
        return True
    except Exception as e:
        print(f"Tushare初始化失败: {e}")
        return False


def _fetch_hist_df(code: str, start_date: str, end_date: str, period: str, adjust: str = ""):
    """拉取日/周/月 K 线 DataFrame，使用Tushare接口"""
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")
    
    if not _init_tushare():
        raise RuntimeError("Tushare初始化失败")
    
    # 初始化pro接口
    pro = ts.pro_api()
    
    # 标准化代码格式
    normalized_code = _normalize_symbol(code)
    
    try:
        if period == "daily":
            # 日线数据
            df = pro.daily(ts_code=normalized_code, start_date=start_date, end_date=end_date)
            if df.empty:
                raise ValueError(f"未找到{normalized_code}在{start_date}到{end_date}的数据")
            
            # 重命名列以匹配标准格式
            df = df.rename(columns={
                'trade_date': 'date',
                'ts_code': 'code',
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date', ascending=False)
            
            return df
            
        elif period == "weekly":
            # 周线数据
            df = pro.weekly(ts_code=normalized_code, start_date=start_date, end_date=end_date)
            if df.empty:
                raise ValueError(f"未找到{normalized_code}周线数据")
            
            df = df.rename(columns={
                'trade_date': 'date',
                'ts_code': 'code',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })
            
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date', ascending=False)
            
            return df
            
        elif period == "monthly":
            # 月线数据
            df = pro.monthly(ts_code=normalized_code, start_date=start_date, end_date=end_date)
            if df.empty:
                raise ValueError(f"未找到{normalized_code}月线数据")
            
            df = df.rename(columns={
                'trade_date': 'date',
                'ts_code': 'code',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount'
            })
            
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date', ascending=False)
            
            return df
            
        else:
            raise ValueError(f"不支持的周期: {period}")
            
    except Exception as e:
        print(f"Tushare获取数据失败: {e}")
        raise


def fetch_ohlcv(
    code: str,
    start_date: str,
    end_date: str,
    period: str = "daily",
    adjust: str = "",
) -> List[OHLCV]:
    """
    拉取 A 股/北交所历史 K 线数据，返回 OHLCV 对象列表。
    
    Args:
        code: 股票代码，如 "000001" 或 "600519"
        start_date: 开始日期，格式 "YYYYMMDD"
        end_date: 结束日期，格式 "YYYYMMDD"
        period: 周期，"daily"（日线）、"weekly"（周线）、"monthly"（月线）
        adjust: 复权类型，"qfq"（前复权）、"hfq"（后复权）、""（不复权）
    
    Returns:
        List[OHLCV]: OHLCV 对象列表，按时间倒序排列（最新在前）
    
    Raises:
        ImportError: Tushare 未安装
        ValueError: 参数错误或数据为空
        RuntimeError: Tushare 初始化失败
    """
    if ts is None:
        raise ImportError("Tushare 未安装，请运行: pip install tushare")
    
    # 拉取 DataFrame
    df = _fetch_hist_df(code, start_date, end_date, period, adjust)
    
    if df.empty:
        raise ValueError(f"未找到 {code} 在 {start_date} 到 {end_date} 的{period}数据")
    
    # 转换为 OHLCV 对象列表
    ohlcv_list = []
    for _, row in df.iterrows():
        dt = _to_utc(row["date"].to_pydatetime())
        ohlcv = OHLCV(
            timestamp=dt,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", 0)),
            amount=float(row.get("amount", 0)),
            code=row.get("code", _normalize_symbol(code)),
        )
        ohlcv_list.append(ohlcv)
    
    return ohlcv_list


def fetch_stock_basic() -> pd.DataFrame:
    """
    获取股票基本信息
    
    Returns:
        pd.DataFrame: 包含股票基本信息的DataFrame
    """
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")
    
    if not _init_tushare():
        raise RuntimeError("Tushare初始化失败")
    
    pro = ts.pro_api()
    
    try:
        # 获取所有上市股票
        df = pro.stock_basic(
            exchange='', 
            list_status='L', 
            fields='ts_code,symbol,name,area,industry,list_date,market,is_hs'
        )
        return df
    except Exception as e:
        print(f"获取股票基本信息失败: {e}")
        raise


def fetch_realtime_quotes(codes: List[str]) -> pd.DataFrame:
    """
    获取实时行情数据
    
    Args:
        codes: 股票代码列表，如 ["000001", "600519"]
    
    Returns:
        pd.DataFrame: 实时行情数据
    """
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")
    
    try:
        # 注意：此函数可能需要相应权限
        normalized_codes = [_normalize_symbol(code).split('.')[0] for code in codes]
        df = ts.get_realtime_quotes(normalized_codes)
        return df
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        raise


def fetch_financial_data(code: str, report_type: str = "income", start_date: str = "", end_date: str = "") -> pd.DataFrame:
    """
    获取财务数据
    
    Args:
        code: 股票代码
        report_type: 报表类型，"income"(利润表), "balancesheet"(资产负债表), "cashflow"(现金流量表)
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        pd.DataFrame: 财务数据
    """
    if ts is None or pd is None:
        raise ImportError("Tushare或pandas未安装")
    
    if not _init_tushare():
        raise RuntimeError("Tushare初始化失败")
    
    pro = ts.pro_api()
    normalized_code = _normalize_symbol(code)
    
    try:
        if report_type == "income":
            df = pro.income(ts_code=normalized_code, start_date=start_date, end_date=end_date)
        elif report_type == "balancesheet":
            df = pro.balancesheet(ts_code=normalized_code, start_date=start_date, end_date=end_date)
        elif report_type == "cashflow":
            df = pro.cashflow(ts_code=normalized_code, start_date=start_date, end_date=end_date)
        else:
            raise ValueError(f"不支持的报表类型: {report_type}")
        
        return df
    except Exception as e:
        print(f"获取财务数据失败: {e}")
        raise


# 测试函数
def test_tushare_connector():
    """测试Tushare连接器"""
    print("测试Tushare连接器...")
    
    # 检查环境变量
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("⚠ 未设置TUSHARE_TOKEN环境变量")
        print("请设置: export TUSHARE_TOKEN='你的token'")
        return False
    
    try:
        # 测试初始化
        if not _init_tushare():
            print("✗ Tushare初始化失败")
            return False
        
        print("✓ Tushare初始化成功")
        
        # 测试获取股票基本信息
        print("测试获取股票基本信息...")
        pro = ts.pro_api()
        df = pro.stock_basic(ts_code='000001.SZ', fields='ts_code,name,industry,list_date')
        if not df.empty:
            print(f"✓ 获取股票信息成功: {df.iloc[0]['name']}")
        else:
            print("⚠ 获取股票信息返回空数据")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 直接运行测试
    if test_tushare_connector():
        print("Tushare连接器测试通过！")
    else:
        print("Tushare连接器测试失败，请检查配置。")