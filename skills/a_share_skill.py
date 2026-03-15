# -*- coding: utf-8 -*-
"""
OpenClaw A股数据 Skill — 红山量化平台集成
功能：A股行情、基本面、技术指标查询（Tushare）
依赖：tushare、pandas、numpy；Token 从环境变量 TUSHARE_TOKEN 读取（.env 或 export）
"""

from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

# 可选：在独立运行时加载 .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# 缓存配置
CACHE_DIR = Path("/tmp/ashare_skill_cache")
CACHE_TTL = 3600  # 1小时缓存


def _get_pro():
    """获取 Tushare pro_api 实例（需已设置 TUSHARE_TOKEN）。"""
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        raise ValueError("未设置 TUSHARE_TOKEN，请在 .env 或环境变量中配置")
    import tushare as ts

    ts.set_token(token)
    return ts.pro_api()


def _get_cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_str = f"{func_name}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_from_cache(cache_key: str) -> Optional[Any]:
    """从缓存获取数据"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            if datetime.now().timestamp() - mtime < CACHE_TTL:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
    except Exception:
        pass
    return None


def _save_to_cache(cache_key: str, data: Any) -> None:
    """保存数据到缓存"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except Exception:
        pass


def _with_cache(func):
    """缓存装饰器"""

    def wrapper(*args, **kwargs):
        # 跳过缓存的情况
        if kwargs.get("no_cache", False):
            return func(*args, **kwargs)

        cache_key = _get_cache_key(
            func.__name__, *args, **{k: v for k, v in kwargs.items() if k != "no_cache"}
        )
        cached = _get_from_cache(cache_key)
        if cached is not None:
            return cached

        result = func(*args, **kwargs)
        if result and not isinstance(result, dict) or "error" not in result:
            _save_to_cache(cache_key, result)
        return result

    return wrapper


class AShareSkill:
    """A股数据查询 Skill：行情、基本面、技术指标。"""

    def __init__(self) -> None:
        self.name = "a_share_skill"
        self.description = "A股数据查询Skill，支持行情、基本面、技术指标查询（Tushare）"

    @_with_cache
    def get_stock_basic(
        self,
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        no_cache: bool = False,
    ) -> Any:
        """
        获取股票基本信息（代码、名称、行业、上市日期等）
        :param ts_code: 股票代码（如 600000.SH）
        :param name: 股票名称（如 浦发银行）
        :param no_cache: 是否跳过缓存
        :return: 股票基本信息列表或错误字典
        """
        try:
            pro = _get_pro()
            df = pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,industry,list_date,market,area",
            )
            if df is None or df.empty:
                return {"msg": "未找到股票信息", "data": []}
            if ts_code:
                df = df[df["ts_code"] == ts_code]
            if name:
                df = df[df["name"].astype(str).str.contains(name, na=False)]
            return {
                "data": df.to_dict("records") if not df.empty else [],
                "count": len(df),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": f"获取股票基本信息失败：{str(e)}", "data": []}

    @_with_cache
    def get_daily_price(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        no_cache: bool = False,
    ) -> Any:
        """
        获取A股日线行情（开盘价、收盘价、成交量等）
        :param ts_code: 股票代码（如 600519.SH）
        :param start_date: 开始日期（格式 20240101）
        :param end_date: 结束日期（格式 20240131）
        :param no_cache: 是否跳过缓存
        :return: 日线行情列表或错误字典
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            pro = _get_pro()
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return {"msg": "无日线数据", "data": []}
            df = df.sort_values("trade_date", ascending=True)
            if "pct_chg" in df.columns:
                df["pct_chg"] = df["pct_chg"].round(2)
            if "vol" in df.columns:
                df["vol"] = df["vol"].astype(int)
            return {
                "data": df[
                    ["trade_date", "open", "high", "low", "close", "vol", "pct_chg"]
                ].to_dict("records"),
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "count": len(df),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": f"获取日线行情失败：{str(e)}", "data": []}

    def get_tech_indicator(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Any:
        """
        计算基础技术指标（MA5、MA10、MACD）
        :param ts_code: 股票代码
        :param start_date/end_date: 时间范围（可选）
        :return: 带技术指标的行情数据或错误字典
        """
        try:
            import pandas as pd
        except ImportError:
            return {"error": "需要安装 pandas"}
        try:
            price_data = self.get_daily_price(ts_code, start_date, end_date)
            if isinstance(price_data, dict) and ("error" in price_data or "msg" in price_data):
                return price_data
            df = pd.DataFrame(price_data)
            if df.empty:
                return {"msg": "无日线数据，无法计算技术指标"}
            df["close"] = df["close"].astype(float)
            df["MA5"] = df["close"].rolling(window=5).mean().round(2)
            df["MA10"] = df["close"].rolling(window=10).mean().round(2)
            ema12 = df["close"].ewm(span=12, adjust=False).mean()
            ema26 = df["close"].ewm(span=26, adjust=False).mean()
            df["DIF"] = (ema12 - ema26).round(4)
            df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean().round(4)
            df["MACD"] = (2 * (df["DIF"] - df["DEA"])).round(4)
            return df.to_dict("records")
        except Exception as e:
            return {"error": f"计算技术指标失败：{str(e)}"}

    @_with_cache
    def get_finance_indicator(
        self, ts_code: str, year: Optional[int] = None, no_cache: bool = False
    ) -> Any:
        """
        获取财务指标（市盈率、市净率、净资产收益率等）
        :param ts_code: 股票代码
        :param year: 年份（如 2023），默认最新
        :param no_cache: 是否跳过缓存
        :return: 财务指标字典或错误信息
        """
        try:
            pro = _get_pro()
            df = pro.fina_indicator(ts_code=ts_code)
            if df is None or df.empty:
                return {"msg": "未找到财务指标数据", "data": {}}
            if year is not None:
                df = df[df["end_date"].astype(str).str.startswith(str(year))]
            if df.empty:
                return {"msg": f"未找到 {year} 年财务指标", "data": {}}
            latest = df.iloc[0]
            result = {
                "ts_code": str(latest.get("ts_code", "")),
                "end_date": str(latest.get("end_date", "")),
                "pe": round(float(latest.get("pe") or 0), 2),
                "pb": round(float(latest.get("pb") or 0), 2),
                "roe": round(float(latest.get("roe") or 0), 2),
                "profit_rate": round(float(latest.get("profit_rate") or 0), 2),
                "gross_profit_margin": round(float(latest.get("gross_profit_margin") or 0), 2),
                "net_profit_margin": round(float(latest.get("net_profit_margin") or 0), 2),
                "total_revenue": round(float(latest.get("total_revenue") or 0), 2),
                "net_profit": round(float(latest.get("n_income") or 0), 2),
                "timestamp": datetime.now().isoformat(),
            }
            return {"data": result}
        except Exception as e:
            return {"error": f"获取财务指标失败：{str(e)}", "data": {}}

    @_with_cache
    def get_limit_up_down(self, trade_date: Optional[str] = None, no_cache: bool = False) -> Any:
        """
        获取涨停/跌停股票列表
        :param trade_date: 交易日期（格式 20240310），默认最新
        :param no_cache: 是否跳过缓存
        :return: 涨停跌停股票列表
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            pro = _get_pro()
            df = pro.limit_list(trade_date=trade_date)
            if df is None or df.empty:
                return {"msg": f"{trade_date} 无涨停跌停数据", "data": []}

            # 分类统计
            limit_up = df[df["up_down"] == "U"]
            limit_down = df[df["up_down"] == "D"]

            return {
                "data": df.to_dict("records"),
                "summary": {
                    "trade_date": trade_date,
                    "total": len(df),
                    "limit_up_count": len(limit_up),
                    "limit_down_count": len(limit_down),
                    "limit_up_ratio": round(len(limit_up) / len(df) * 100, 2) if len(df) > 0 else 0,
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": f"获取涨停跌停数据失败：{str(e)}", "data": []}

    @_with_cache
    def get_industry_ranking(
        self, trade_date: Optional[str] = None, top_n: int = 10, no_cache: bool = False
    ) -> Any:
        """
        获取行业涨幅排行
        :param trade_date: 交易日期（格式 20240310），默认最新
        :param top_n: 返回前N名
        :param no_cache: 是否跳过缓存
        :return: 行业排行列表
        """
        try:
            if not trade_date:
                trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            pro = _get_pro()
            df = pro.index_daily(ts_code="", trade_date=trade_date)
            if df is None or df.empty:
                return {"msg": f"{trade_date} 无行业指数数据", "data": []}

            # 过滤行业指数（以CI开头）
            industry_df = df[df["ts_code"].str.startswith("CI")]
            if industry_df.empty:
                return {"msg": "无行业指数数据", "data": []}

            industry_df = industry_df.sort_values("pct_chg", ascending=False).head(top_n)

            return {
                "data": industry_df[["ts_code", "trade_date", "close", "pct_chg", "vol"]].to_dict(
                    "records"
                ),
                "trade_date": trade_date,
                "top_n": top_n,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": f"获取行业排行失败：{str(e)}", "data": []}

    @_with_cache
    def get_market_overview(self, trade_date: Optional[str] = None, no_cache: bool = False) -> Any:
        """
        获取市场概览数据
        :param trade_date: 交易日期（格式 20240310），默认最新
        :param no_cache: 是否跳过缓存
        :return: 市场概览数据
        """
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")

            pro = _get_pro()

            # 获取主要指数
            indices = ["000001.SH", "399001.SZ", "399006.SZ"]  # 上证、深证、创业板
            index_data = []
            for ts_code in indices:
                try:
                    df = pro.index_daily(ts_code=ts_code, trade_date=trade_date)
                    if df is not None and not df.empty:
                        index_data.append(df.iloc[0].to_dict())
                except:
                    continue

            # 获取市场统计
            try:
                market_stats = pro.daily_basic(trade_date=trade_date)
                if market_stats is not None and not market_stats.empty:
                    total_market_cap = market_stats["total_mv"].sum()
                    circ_market_cap = market_stats["circ_mv"].sum()
                    pe_ratio = market_stats["pe"].mean()
                else:
                    total_market_cap = circ_market_cap = pe_ratio = 0
            except:
                total_market_cap = circ_market_cap = pe_ratio = 0

            return {
                "data": {
                    "trade_date": trade_date,
                    "indices": index_data,
                    "market_stats": {
                        "total_market_cap": round(total_market_cap / 1e12, 2),  # 万亿
                        "circ_market_cap": round(circ_market_cap / 1e12, 2),  # 万亿
                        "avg_pe_ratio": round(pe_ratio, 2),
                    },
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": f"获取市场概览失败：{str(e)}", "data": {}}


def load_skill() -> AShareSkill:
    """OpenClaw Skill 加载入口。"""
    return AShareSkill()


if __name__ == "__main__":
    skill = load_skill()
    print("=== 茅台基本信息 ===")
    print(skill.get_stock_basic(name="贵州茅台"))
    print("\n=== 茅台最近日线 ===")
    print(skill.get_daily_price("600519.SH"))
    print("\n=== 茅台技术指标 ===")
    print(skill.get_tech_indicator("600519.SH"))
    print("\n=== 茅台财务指标 ===")
    print(skill.get_finance_indicator("600519.SH"))
