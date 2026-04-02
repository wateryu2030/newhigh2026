"""每日调度：股票池、资金流、龙虎榜；可选 Tushare / akshare 日 K。

建议 18:00 执行。生产环境推荐配置 TUSHARE_TOKEN + TUSHARE_DAILY_DAYS_BACK（如 7），
由 start_schedulers 在有 Token 时默认跳过 akshare 批量日 K，避免代理超时拖垮整轮任务。

日内刷新 `run_intraday_refresh`：由 scripts/start_schedulers.py 在 08:30、12:00、22:00 触发（可关），
优先补齐 **trade_signals / 游资 / 模拟持仓** 相关标的的东财新闻与日 K，缓解前端 Alpha 工坊穿透面板「无 K 线、无新闻」。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta


def _intraday_priority_codes(conn: object, max_n: int) -> list[str]:
    """近线活跃标的：信号、游资席位维度个股、模拟持仓（6 位代码，去重）。"""
    seen: set[str] = set()
    out: list[str] = []

    def pull(sql: str, params: list) -> None:
        nonlocal out
        if len(out) >= max_n:
            return
        try:
            rows = conn.execute(sql, params).fetchall()
        except Exception:
            return
        for row in rows:
            if not row:
                continue
            c = str(row[0] or "").strip()
            if len(c) < 5 or c in seen:
                continue
            seen.add(c)
            out.append(c)
            if len(out) >= max_n:
                return

    pull(
        """
        SELECT DISTINCT split_part(UPPER(TRIM(CAST(code AS VARCHAR))), '.', 1)
        FROM trade_signals
        WHERE snapshot_time >= CURRENT_TIMESTAMP - INTERVAL 45 DAY
          AND code IS NOT NULL AND LENGTH(TRIM(CAST(code AS VARCHAR))) >= 5
        LIMIT ?
        """,
        [max_n],
    )
    pull(
        """
        SELECT DISTINCT split_part(UPPER(TRIM(CAST(code AS VARCHAR))), '.', 1)
        FROM hotmoney_signals
        WHERE code IS NOT NULL AND LENGTH(TRIM(CAST(code AS VARCHAR))) >= 5
        LIMIT ?
        """,
        [max_n],
    )
    pull(
        """
        SELECT DISTINCT split_part(UPPER(TRIM(CAST(code AS VARCHAR))), '.', 1)
        FROM sim_positions
        WHERE code IS NOT NULL AND ABS(COALESCE(qty, 0)) > 1e-6
        LIMIT ?
        """,
        [max_n],
    )
    return out[:max_n]


def run_intraday_refresh(slot_label: str = "") -> None:
    """
    日内定时任务：Tushare 增量（可选）+ 东财个股新闻（优先活跃标的）+ 优先标的日 K（AkShare，短窗口）+ 可选全市场现货。
    依赖本机可访问东财/Tushare；云主机境外不通东财时需 Tushare 或隧道。
    """
    label = (slot_label or "intraday").strip()
    print(f"=== 日内数据刷新 [{label}] {datetime.now().isoformat(timespec='seconds')} ===")

    if (os.environ.get("INTRADAY_RSS_REFRESH", "1") or "1").strip().lower() not in ("0", "false", "no"):
        try:
            from ..collectors.rss_macro_news import update_rss_macro_news

            n_rss = update_rss_macro_news()
            if n_rss:
                print(f"[{label}] RSS 宏观快讯新写入: {n_rss}")
        except Exception as e:
            print(f"[{label}] RSS 宏观采集失败: {e}")

    token = (os.environ.get("TUSHARE_TOKEN") or "").strip()
    tb = int(os.environ.get("INTRADAY_TUSHARE_DAYS_BACK", "3"))
    if token and os.environ.get("INTRADAY_TUSHARE_REFRESH", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    ):
        try:
            from ..collectors.tushare_daily import update_all_tushare_daily

            n = update_all_tushare_daily(days_back=max(1, min(tb, 30)))
            print(f"[{label}] Tushare 增量日 K: {n} 条（days_back={tb}）")
        except Exception as e:
            print(f"[{label}] Tushare 日内更新失败: {e}")

    from ..storage.duckdb_manager import get_conn, ensure_tables

    conn = get_conn()
    ensure_tables(conn)
    pri_max = int(os.environ.get("INTRADAY_PRIORITY_CODES_MAX", "220"))
    priority = _intraday_priority_codes(conn, pri_max)
    conn.close()
    print(f"[{label}] 优先标的（信号/游资/模拟持仓）: {len(priority)} 只")

    news_lim = int(os.environ.get("INTRADAY_NEWS_EM_CODES_LIMIT", "120"))
    news_per = int(os.environ.get("INTRADAY_NEWS_EM_PER_CODE", "10"))
    try:
        from ..collectors.em_stock_news import update_em_stock_news

        n_news = update_em_stock_news(
            codes_limit=news_lim,
            per_code_limit=news_per,
            extra_codes_first=priority or None,
        )
        print(f"[{label}] 东财个股新闻新写入: {n_news} 条")
    except Exception as e:
        print(f"[{label}] 东财新闻采集失败: {e}")

    klim = int(os.environ.get("INTRADAY_KLINE_CODES_LIMIT", "80"))
    if klim > 0:
        from ..collectors.daily_kline import update_daily_kline

        k_days = int(os.environ.get("INTRADAY_KLINE_DAYS_BACK", "150"))
        end_d = datetime.now().strftime("%Y%m%d")
        start_d = (datetime.now() - timedelta(days=max(30, k_days))).strftime("%Y%m%d")
        seen_k: set[str] = set()
        k_codes: list[str] = []
        for c in priority:
            c6 = str(c).split(".", maxsplit=1)[0].strip()
            if len(c6) < 5 or c6 in seen_k:
                continue
            seen_k.add(c6)
            k_codes.append(c6)
            if len(k_codes) >= klim:
                break
        if len(k_codes) < klim:
            conn = get_conn()
            try:
                df = conn.execute(
                    "SELECT code FROM a_stock_basic ORDER BY code LIMIT ?",
                    [max(klim * 2, 400)],
                ).fetchdf()
                if df is not None and not df.empty:
                    for raw in df["code"].astype(str).tolist():
                        c6 = raw.split(".", maxsplit=1)[0].strip()
                        if len(c6) < 5 or c6 in seen_k:
                            continue
                        seen_k.add(c6)
                        k_codes.append(c6)
                        if len(k_codes) >= klim:
                            break
            finally:
                conn.close()

        ok = 0
        for c6 in k_codes[:klim]:
            try:
                update_daily_kline(c6, start_date=start_d, end_date=end_d)
                ok += 1
            except Exception as e:
                print(f"[{label}] K线 {c6}: {e}")
        print(f"[{label}] AkShare 日 K 更新 {ok}/{min(len(k_codes), klim)} 只（{start_d}~{end_d}）")

    if os.environ.get("INTRADAY_UPDATE_SPOT_EM", "0").strip().lower() in ("1", "true", "yes"):
        try:
            from ..collectors.realtime_quotes import update_realtime_quotes

            n_sp = update_realtime_quotes()
            print(f"[{label}] 东财现货快照写入: {n_sp} 行")
        except Exception as e:
            print(f"[{label}] 东财现货快照失败: {e}")

    print(f"=== 日内数据刷新 [{label}] 结束 ===")


def run_daily(
    update_all_kline: bool = False,
    kline_codes_limit: int = 0,
    collect_news: bool = True,
    use_tushare: bool = False,
    tushare_days_back: int = 30,
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
            from ..collectors.rss_macro_news import update_rss_macro_news

            n_rss = update_rss_macro_news()
            if n_rss:
                print(f"RSS 宏观快讯: {n_rss} 条")
        except Exception as e:
            print(f"RSS 宏观采集失败: {e}")
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
        codes = conn.execute(
            "SELECT code FROM a_stock_basic LIMIT ?", [kline_codes_limit]
        ).fetchdf()
        conn.close()
        if codes is not None and not codes.empty:
            for code in codes["code"].tolist():
                try:
                    update_daily_kline(str(code))
                except Exception as e:
                    print(f"K线 {code}: {e}")
            print("日K线批量更新完成")
    print("每日数据更新完成")
