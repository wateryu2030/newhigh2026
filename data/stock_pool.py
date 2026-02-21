# -*- coding: utf-8 -*-
"""
A 股股票池与 K 线数据加载。
优先使用 AKShare；可选 Tushare 等备用。
"""
from typing import List, Dict, Any, Optional
import pandas as pd


def get_a_share_list() -> List[Dict[str, str]]:
    """
    获取 A 股全部股票列表。
    优先使用 AKShare；失败时返回空列表或从本地数据库补全。
    :return: [{"symbol": "000001", "name": "平安银行"}, ...]
    """
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        stocks = []
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            name = str(row.get("name", "")).strip()
            if not code or code == "nan":
                continue
            stocks.append({"symbol": code, "name": name or code})
        return stocks
    except Exception:
        pass
    return []


def get_a_share_symbols(exclude_delisted: bool = True) -> List[str]:
    """
    获取沪深京 A 股全部股票代码（6 位），不含退市股。
    :param exclude_delisted: 是否排除名称含「退市」的标的
    :return: ["000001", "600519", ...]
    """
    lst = get_a_share_list()
    codes = []
    for item in lst:
        code = (item.get("symbol") or "").strip()
        if not code or len(code) != 6 or not code.isdigit():
            continue
        code = code.zfill(6)
        if exclude_delisted:
            name = (item.get("name") or "")
            if "退市" in name:
                continue
        codes.append(code)
    return list(dict.fromkeys(codes))  # 去重保序


def load_kline(
    symbol: str,
    period: str = "daily",
    adjust: str = "qfq",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    加载单只股票 K 线（AKShare）。
    :param symbol: 股票代码，如 000001（不含后缀）
    :param period: daily / weekly / monthly
    :param adjust: qfq 前复权 / hfq 后复权 / 空字符串不复权
    :param start_date: 开始日期 YYYYMMDD
    :param end_date: 结束日期 YYYYMMDD
    :return: DataFrame 列 date, open, high, low, close, volume
    """
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            adjust=adjust,
            start=start_date,
            end=end_date,
        )
        if df is None or len(df) == 0:
            return pd.DataFrame()
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
        })
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df
    except Exception:
        return pd.DataFrame()
