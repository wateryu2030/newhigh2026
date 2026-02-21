# -*- coding: utf-8 -*-
"""
新闻采集：东方财富、财新、抖音（占位）。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

try:
    import pandas as pd
except ImportError:
    pd = None


def _to_records(df) -> List[Dict[str, Any]]:
    """DataFrame 转记录列表。"""
    if df is None or (pd is not None and not isinstance(df, pd.DataFrame)):
        return []
    if hasattr(df, "to_dict") and callable(getattr(df, "to_dict", None)):
        return df.to_dict(orient="records")
    if isinstance(df, list):
        return df
    return []


def _norm_col(df, col_map: Dict[str, str]) -> None:
    """统一列名。"""
    if df is None or not hasattr(df, "rename"):
        return
    df.rename(columns=col_map, inplace=True)


# ----- 东方财富 -----


def fetch_eastmoney_news(
    symbol: str,
    limit: int = 100,
    delay: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    采集东方财富个股/关键词新闻。
    :param symbol: 股票代码或关键词，如 "600519" 或 "茅台"
    :param limit: 最大条数
    :param delay: 请求间隔（秒），建议 >= 1 避免反爬
    """
    try:
        try:
            from akshare.news.news_stock import stock_news_em
        except ImportError:
            from akshare import stock_news_em
        time.sleep(delay)
        code = symbol.split(".")[0] if "." in symbol else symbol
        df = stock_news_em(symbol=code)
        recs = _to_records(df)
        col_map = {
            "关键词": "keyword",
            "新闻标题": "title",
            "新闻内容": "content",
            "发布时间": "publish_time",
            "文章来源": "source",
            "新闻链接": "url",
        }
        out = []
        for r in recs[:limit]:
            if isinstance(r, dict) and r.get("error"):
                continue
            row = {"source_site": "eastmoney"}
            for cn, en in col_map.items():
                row[en] = str(r.get(cn, r.get(en, "")) or "")
            out.append(row)
        return out
    except Exception as e:
        return [{"error": str(e), "source_site": "eastmoney"}]


# ----- 财新 -----


def fetch_caixin_news(
    limit: int = 100,
    delay: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    采集财新网热点新闻。
    :param limit: 最大条数
    :param delay: 请求间隔
    """
    try:
        try:
            from akshare.stock.stock_news_cx import stock_news_main_cx
        except ImportError:
            from akshare import stock_news_main_cx
        time.sleep(delay)
        df = stock_news_main_cx()
        recs = _to_records(df)
        out = []
        for r in recs[:limit]:
            if isinstance(r, dict) and r.get("error"):
                continue
            s = str(r.get("summary", r.get("content", "")) or "")
            out.append({
                "title": s[:100] if s else "",
                "content": s,
                "url": str(r.get("url", "") or ""),
                "tag": str(r.get("tag", "") or ""),
                "source_site": "caixin",
                "keyword": "",
                "publish_time": "",
                "source": "财新",
            })
        return out
    except Exception as e:
        return [{"error": str(e), "source_site": "caixin"}]


# ----- 抖音（占位） -----


def fetch_douyin_news_placeholder(
    keyword: str = "",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    抖音热点/舆情采集占位。
    抖音官方 API 需企业认证，此处返回空列表或模拟数据结构。
    可后续接入：第三方舆情数据商、爬虫（注意合规）、开放平台 API。
    """
    return [
        {
            "title": "[抖音占位] 需接入开放平台或第三方数据",
            "content": "抖音数据需企业开放平台申请。",
            "url": "",
            "source_site": "douyin",
            "keyword": keyword,
            "publish_time": "",
            "source": "douyin",
        }
    ]


# ----- 汇总 -----


def fetch_all_news(
    symbol: str = "",
    sources: Optional[List[str]] = None,
    limit_per_source: int = 50,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    从多源采集新闻。
    :param symbol: 股票代码（东方财富用）
    :param sources: 来源列表 ["eastmoney","caixin","douyin"]，None 表示全部
    :param limit_per_source: 每源最大条数
    """
    sources = sources or ["eastmoney", "caixin", "douyin"]
    out = {}
    if "eastmoney" in sources and symbol:
        out["eastmoney"] = fetch_eastmoney_news(symbol, limit=limit_per_source)
    if "caixin" in sources:
        out["caixin"] = fetch_caixin_news(limit=limit_per_source)
    if "douyin" in sources:
        out["douyin"] = fetch_douyin_news_placeholder(keyword=symbol, limit=limit_per_source)
    return out
