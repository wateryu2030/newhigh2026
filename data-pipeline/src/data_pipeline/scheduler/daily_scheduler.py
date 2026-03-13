"""每日调度：股票池、资金流、龙虎榜；可选全量日K线。建议 18:00 执行。"""
from __future__ import annotations
import os

def run_daily(
    update_all_kline: bool = False, 
    kline_codes_limit: int = 0, 
    collect_news: bool = True,
    use_tushare: bool = False,
    tushare_days_back: int = 30
) -> None:
    from ..collectors.stock_list import update_stock_list
    from ..collectors.fund_flow import update_fundflow
    from ..collectors.longhubang import update_longhubang

    n1 = update_stock_list()
    print(f"股票池更新: {n1} 只")
    n2 = update_fundflow()
    print(f"资金流更新: {n2} 条")
    n3 = update_longhubang()
    print(f"龙虎榜更新: {n3} 条")
    
    # Tushare 日 K 线数据更新（可选）
    if use_tushare:
        try:
            from ..collectors.tushare_daily import update_all_tushare_daily
            n_tushare = update_all_tushare_daily(days_back=tushare_days_back)
            print(f"Tushare 日 K 线更新: {n_tushare} 条")
        except ImportError as e:
            print(f"Tushare 收集器未找到: {e}")
            print("请确保已安装 tushare: pip install tushare")
        except Exception as e:
            print(f"Tushare 数据更新失败: {e}")
    
    # 新闻采集（可选）
    if collect_news:
        try:
            from ..collectors.caixin_news import update_caixin_news
            # 从环境变量获取配置，默认采集最近3天新闻
            news_keywords = os.environ.get("NEWS_KEYWORDS", "经济 金融 股票")
            news_days_back = int(os.environ.get("NEWS_DAYS_BACK", "3"))
            n4 = update_caixin_news(keywords=news_keywords, days_back=news_days_back)
            print(f"财新新闻采集: {n4} 条")
        except ImportError as e:
            print(f"财新新闻采集器未找到: {e}")
        except Exception as e:
            print(f"财新新闻采集失败: {e}")
    
    # 使用 akshare 更新日 K 线（备用）
    if update_all_kline and kline_codes_limit > 0:
        from ..collectors.daily_kline import update_daily_kline
        from ..storage.duckdb_manager import get_conn
        conn = get_conn()
        codes = conn.execute("SELECT code FROM a_stock_basic LIMIT ?", [kline_codes_limit]).fetchdf()
        conn.close()
        if codes is not None and not codes.empty:
            for code in codes["code"].tolist():
                try:
                    update_daily_kline(str(code))
                except Exception as e:
                    print(f"K线 {code}: {e}")
            print("日K线批量更新完成")
    print("每日数据更新完成")
