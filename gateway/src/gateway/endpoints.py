"""API endpoints: market, strategy, backtest, portfolio, risk, trade, ai-lab."""
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException

router = APIRouter()


def _is_ashare_symbol(symbol: str) -> bool:
    code = (symbol or "").strip().split(".")[0]
    return len(code) == 6 and code.isdigit()


@router.get("/market/klines")
def get_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """K 线：A 股优先从 astock DuckDB 读，否则 stub/akshare。"""
    # A 股日线：从 newhigh 本地 DuckDB 读（与 astock 独立）
    if _is_ashare_symbol(symbol) and (interval in ("1d", "daily") or not interval):
        try:
            from data_engine import get_astock_duckdb_available, fetch_klines_from_astock_duckdb
            if get_astock_duckdb_available():
                rows = fetch_klines_from_astock_duckdb(symbol, start_date=start_date, end_date=end_date, limit=limit)
                if rows:
                    # 前端兼容：同时返回 c 与 close
                    data = [
                        {"t": r.timestamp.isoformat(), "o": r.open, "h": r.high, "l": r.low, "c": r.close, "close": r.close, "v": r.volume}
                        for r in rows
                    ]
                    return {"symbol": rows[0].symbol, "interval": "1d", "limit": len(data), "data": data}
        except Exception:
            pass
    return {"symbol": symbol, "interval": interval, "limit": limit, "data": []}


@router.get("/data/status")
def get_data_status() -> dict:
    """数据状态：标的数、日线条数、日期范围，供前端「数据」页与 Dashboard 展示。"""
    try:
        from data_engine import get_astock_duckdb_available, get_duckdb_data_status
        if get_astock_duckdb_available():
            st = get_duckdb_data_status()
            return {"ok": True, "source": "duckdb", **st}
    except Exception:
        pass
    return {"ok": False, "source": None, "stocks": 0, "daily_bars": 0, "date_min": None, "date_max": None}


@router.get("/market/ashare/stocks")
def get_ashare_stocks() -> dict:
    """A 股标的列表（来自 newhigh 本地 DuckDB），供前端 Market 页标的选择与 K 线请求。"""
    try:
        from data_engine import get_astock_duckdb_available, get_stocks_for_api
        if get_astock_duckdb_available():
            stocks = get_stocks_for_api()
            return {"stocks": stocks, "source": "duckdb"}
    except Exception:
        pass
    return {"stocks": [], "source": None}


# --- Data Service 层：DuckDB → API 稳定通道（MVP Data Bridge）---

@router.get("/stocks")
def get_stocks(limit: int = 200) -> list:
    """A 股股票列表，供前端 Stocks 页表格。优先 stocks 表，空时回退 a_stock_basic。"""
    try:
        from core.data_service import get_stock_list
        out = get_stock_list(limit=limit)
        if out:
            return out
    except Exception:
        pass
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=True)
            try:
                df = conn.execute(
                    "SELECT code, name FROM a_stock_basic ORDER BY code LIMIT ?",
                    [limit],
                ).fetchdf()
                if df is not None and not df.empty:
                    return [
                        {"ts_code": str(row.get("code", "")), "name": str(row.get("name") or row.get("code") or ""), "industry": ""}
                        for _, row in df.iterrows()
                    ]
            finally:
                conn.close()
    except Exception:
        pass
    return []


@router.get("/market/summary")
def get_market_summary() -> dict:
    """市场概览：标的数、日线条数、日期范围，供 Dashboard 与前端。"""
    try:
        from core.data_service import get_market_summary as svc_summary
        return svc_summary()
    except Exception:
        return {"total_stocks": 0, "market": "A-share", "daily_bars": 0, "date_min": None, "date_max": None}


# --- 数据管道 Data Pipeline（quant_system.duckdb：实时/涨停/资金流）---

@router.get("/data/sources")
def get_data_sources() -> dict:
    """已注册数据源 id 列表（支持增量更新的数据源）。"""
    try:
        from data_pipeline import list_sources
        return {"sources": list_sources()}
    except Exception as e:
        return {"sources": [], "error": str(e)}


@router.post("/data/ensure-stocks")
def ensure_stocks() -> dict:
    """拉取 A 股股票池写入 a_stock_basic（akshare），数据不足时由前端或定时任务调用。"""
    try:
        from data_pipeline.collectors.stock_list import update_stock_list
        n = update_stock_list()
        return {"ok": True, "rows": n}
    except Exception as e:
        return {"ok": False, "rows": 0, "error": str(e)}


# ---------- OpenClaw A股 Skill（Tushare：行情、基本面、技术指标）----------
def _ashare_skill():
    from skills.a_share_skill import load_skill
    return load_skill()


def _record_skill_call() -> None:
    """Skill 调用时增加 skill_stats 计数，供系统监控展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return
        conn = get_conn(read_only=False)
        try:
            n = conn.execute("SELECT COUNT(*) FROM skill_stats").fetchone()[0]
            if n == 0:
                conn.execute("INSERT INTO skill_stats (call_count, last_call_time) VALUES (0, NULL)")
        except Exception:
            pass
        conn.execute("UPDATE skill_stats SET call_count = call_count + 1, last_call_time = CURRENT_TIMESTAMP")
        conn.close()
    except Exception:
        pass


@router.get("/skill/ashare/stock-basic")
def skill_ashare_stock_basic(ts_code: Optional[str] = None, name: Optional[str] = None) -> Any:
    """A股股票基本信息（代码、名称、行业、上市日期）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_stock_basic(ts_code=ts_code, name=name)


@router.get("/skill/ashare/daily")
def skill_ashare_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """A股日线行情（开高低收、成交量、涨跌幅）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_daily_price(ts_code=ts_code, start_date=start_date, end_date=end_date)


@router.get("/skill/ashare/tech-indicator")
def skill_ashare_tech_indicator(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """A股技术指标（MA5、MA10、MACD）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_tech_indicator(ts_code=ts_code, start_date=start_date, end_date=end_date)


@router.get("/skill/ashare/finance-indicator")
def skill_ashare_finance_indicator(ts_code: str, year: Optional[int] = None) -> Any:
    """A股财务指标（PE、PB、ROE、毛利率）。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_finance_indicator(ts_code=ts_code, year=year)


@router.get("/skill/ashare/limit-up-down")
def skill_ashare_limit_up_down(trade_date: Optional[str] = None) -> Any:
    """A股涨停/跌停股票列表。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_limit_up_down(trade_date=trade_date)


@router.get("/skill/ashare/industry-ranking")
def skill_ashare_industry_ranking(trade_date: Optional[str] = None, top_n: int = 10) -> Any:
    """A股行业涨幅排行。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_industry_ranking(trade_date=trade_date, top_n=top_n)


@router.get("/skill/ashare/market-overview")
def skill_ashare_market_overview(trade_date: Optional[str] = None) -> Any:
    """A股市场概览数据。需 TUSHARE_TOKEN。"""
    _record_skill_call()
    return _ashare_skill().get_market_overview(trade_date=trade_date)


@router.get("/skill/stats")
def get_skill_stats() -> dict:
    """Skill 调用统计：总次数、最近调用时间，供系统监控页展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {"call_count": 0, "last_call_time": None}
        conn = get_conn(read_only=True)
        row = conn.execute("SELECT call_count, last_call_time FROM skill_stats LIMIT 1").fetchone()
        conn.close()
        if not row:
            return {"call_count": 0, "last_call_time": None}
        last_ts = row[1]
        if hasattr(last_ts, "isoformat"):
            last_call_time = last_ts.isoformat()
        else:
            last_call_time = str(last_ts) if last_ts else None
        return {"call_count": int(row[0] or 0), "last_call_time": last_call_time}
    except Exception:
        return {"call_count": 0, "last_call_time": None}


@router.post("/data/incremental")
def run_data_incremental(source_id: str = "ashare_daily_kline", force_full: bool = False) -> dict:
    """执行指定数据源增量更新。source_id 见 GET /api/data/sources。"""
    try:
        from data_pipeline import run_incremental, list_sources
        if source_id not in list_sources():
            raise HTTPException(status_code=400, detail=f"unknown source_id: {source_id}")
        n = run_incremental(source_id, force_full=force_full)
        return {"ok": True, "source_id": source_id, "rows_written": n}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _market_db_query(table: str, order_by: str, limit: int = 100) -> list:
    """从 data_pipeline 的 market.duckdb 读表，返回 list[dict]。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(f"SELECT * FROM {table} ORDER BY {order_by} LIMIT ?", [limit]).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/realtime")
def get_market_realtime(limit: int = 100) -> list:
    """实时行情快照（数据管道 a_stock_realtime），按成交额降序。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT code, name, latest_price, change_pct, volume, amount, snapshot_time FROM a_stock_realtime ORDER BY amount DESC NULLS LAST LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/limitup")
def get_market_limitup(limit: int = 100) -> list:
    """涨停池（数据管道 a_stock_limitup），情绪/连板分析。"""
    return _market_db_query("a_stock_limitup", "limit_up_times DESC NULLS LAST", limit)


@router.get("/market/fundflow")
def get_market_fundflow(limit: int = 100) -> list:
    """个股资金流排名（数据管道 a_stock_fundflow）。"""
    return _market_db_query("a_stock_fundflow", "main_net_inflow DESC NULLS LAST", limit)


@router.get("/market/emotion")
def get_market_emotion() -> dict:
    """情绪周期状态：优先 market_emotion（每日指标+状态），否则 market_emotion_state。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {"state": "unknown", "stage": "—", "limit_up_count": 0, "score": 0, "trade_date": None, "max_height": 0, "market_volume": 0}
        conn = get_conn(read_only=True)
        row = conn.execute(
            "SELECT trade_date, limitup_count, max_height, market_volume, emotion_state FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
        ).fetchone()
        if row:
            conn.close()
            return {
                "state": row[4] or "—",
                "stage": row[4] or "—",
                "limit_up_count": int(row[1] or 0),
                "score": 50.0,
                "trade_date": str(row[0]) if row[0] else None,
                "max_height": int(row[2] or 0),
                "market_volume": float(row[3] or 0),
            }
        row = conn.execute(
            "SELECT state, stage, limit_up_count, score FROM market_emotion_state ORDER BY snapshot_time DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            return {"state": row[0], "stage": row[1], "limit_up_count": row[2] or 0, "score": float(row[3] or 0), "trade_date": None, "max_height": 0, "market_volume": 0}
    except Exception:
        pass
    return {"state": "unknown", "stage": "—", "limit_up_count": 0, "score": 0, "trade_date": None, "max_height": 0, "market_volume": 0}


@router.get("/strategy/signals")
def get_strategy_signals(limit: int = 50) -> list:
    """交易信号（trade_signals 表，含 signal_score），供终端与自动交易。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT code, signal, confidence, target_price, stop_loss, strategy_id, signal_score, snapshot_time FROM trade_signals ORDER BY snapshot_time DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/hotmoney")
def get_market_hotmoney(limit: int = 50) -> list:
    """龙虎榜游资席位胜率（top_hotmoney_seats），供终端「跟谁」。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT seat_name, trade_count, win_rate, avg_return, snapshot_time FROM top_hotmoney_seats ORDER BY win_rate DESC NULLS LAST LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/main-themes")
def get_market_main_themes(limit: int = 10) -> list:
    """主线题材（main_themes），供终端「买什么」。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT sector, total_volume, rank, snapshot_time FROM main_themes ORDER BY rank LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


@router.get("/market/sniper-candidates")
def get_sniper_candidates(limit: int = 50) -> list:
    """游资狙击候选池（sniper_candidates），Sniper Score > 0.7 的潜在连板龙头。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT code, theme, sniper_score, confidence, snapshot_time FROM sniper_candidates ORDER BY sniper_score DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


def _status_to_state(s: str) -> str:
    """将 system_status 短串转为 running/error/idle。"""
    if not s or s == "not_run":
        return "idle"
    if s.startswith("error:"):
        return "error"
    return "running"


@router.get("/ai/decision")
def get_ai_decision() -> dict:
    """
    AI 决策解释：聚合情绪、交易信号、游资、主线，返回当前信号与理由，供前端「AI 决策解释」区块展示。
    返回：signal (BUY/SELL/HOLD), reason (文案), factors (标签列表)。
    """
    signal = "HOLD"
    reason_parts: List[str] = []
    factors: List[str] = []
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {"signal": signal, "reason": "暂无数据", "factors": []}
        conn = get_conn(read_only=True)
        try:
            row = conn.execute(
                "SELECT emotion_state, limitup_count FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            if row:
                stage = str(row[0] or "—")
                limitup = int(row[1] or 0)
                reason_parts.append(f"情绪阶段: {stage}; 涨停数 {limitup}")
                factors.append(f"emotion_{stage[:2]}" if stage != "—" else "emotion")
            df_sig = conn.execute(
                "SELECT signal FROM trade_signals ORDER BY snapshot_time DESC LIMIT 20"
            ).fetchdf()
            if df_sig is not None and not df_sig.empty:
                sig_str = str(df_sig.iloc[0].get("signal", "")).upper()
                if "BUY" in sig_str or "LONG" in sig_str or "买" in sig_str or "多" in sig_str:
                    signal = "BUY"
                elif "SELL" in sig_str or "SHORT" in sig_str or "卖" in sig_str or "空" in sig_str:
                    signal = "SELL"
                n = len(df_sig)
                reason_parts.append(f"交易信号 {n} 条，最新: {sig_str or '—'}")
                factors.append("trade_signals")
            hot = conn.execute("SELECT COUNT(*) FROM top_hotmoney_seats").fetchone()
            hot_n = int(hot[0]) if hot and hot[0] is not None else 0
            if hot_n > 0:
                reason_parts.append(f"游资席位 {hot_n} 个")
                factors.append("hotmoney")
            th = conn.execute("SELECT COUNT(*) FROM main_themes").fetchone()
            th_n = int(th[0]) if th and th[0] is not None else 0
            if th_n > 0:
                reason_parts.append(f"主线题材 {th_n} 个")
                factors.append("themes")
        finally:
            conn.close()
        reason = "；".join(reason_parts) if reason_parts else "暂无情绪与信号数据，建议先运行 system_core。"
    except Exception as e:
        reason = str(e)
    return {"signal": signal, "reason": reason, "factors": factors}


@router.get("/system/status")
def get_system_status(limit: int = 10):
    """
    统一运行核心状态（system_status 表），由 system_core 写入。
    返回：summary（data_pipeline, scanner, ai_models, strategy_engine, last_update）+ history 列表。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {
                "data_pipeline": "idle",
                "scanner": "idle",
                "ai_models": "idle",
                "strategy_engine": "idle",
                "last_update": None,
                "history": [],
            }
        conn = get_conn(read_only=True)
        try:
            df = conn.execute(
                """SELECT data_status, scanner_status, ai_status, strategy_status, snapshot_time,
                          evolution_task_id, evolution_status, evolution_result, skill_call_count, skill_last_call_time
                   FROM system_status ORDER BY snapshot_time DESC LIMIT ?""",
                [limit],
            ).fetchdf()
        except Exception:
            df = conn.execute(
                "SELECT data_status, scanner_status, ai_status, strategy_status, snapshot_time FROM system_status ORDER BY snapshot_time DESC LIMIT ?",
                [limit],
            ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {
                "data_pipeline": "idle",
                "scanner": "idle",
                "ai_models": "idle",
                "strategy_engine": "idle",
                "last_update": None,
                "history": [],
                "evolution_task_id": None,
                "evolution_status": None,
                "skill_call_count": 0,
                "skill_last_call_time": None,
            }
        row = df.iloc[0]
        last_ts = row.get("snapshot_time")
        if hasattr(last_ts, "isoformat"):
            last_update = last_ts.isoformat()
        else:
            last_update = str(last_ts) if last_ts else None
        summary = {
            "data_pipeline": _status_to_state(str(row.get("data_status", ""))),
            "scanner": _status_to_state(str(row.get("scanner_status", ""))),
            "ai_models": _status_to_state(str(row.get("ai_status", ""))),
            "strategy_engine": _status_to_state(str(row.get("strategy_status", ""))),
            "last_update": last_update,
        }
        if "evolution_task_id" in row:
            summary["evolution_task_id"] = row.get("evolution_task_id")
            summary["evolution_status"] = row.get("evolution_status")
        if "skill_call_count" in row:
            summary["skill_call_count"] = int(row.get("skill_call_count") or 0)
            st = row.get("skill_last_call_time")
            summary["skill_last_call_time"] = st.isoformat() if hasattr(st, "isoformat") else (str(st) if st else None)
        history = df.to_dict(orient="records")
        for h in history:
            if "snapshot_time" in h and hasattr(h["snapshot_time"], "isoformat"):
                h["snapshot_time"] = h["snapshot_time"].isoformat()
        return {**summary, "history": history}
    except Exception:
        return {
            "data_pipeline": "idle",
            "scanner": "idle",
            "ai_models": "idle",
            "strategy_engine": "idle",
            "last_update": None,
            "history": [],
            "evolution_task_id": None,
            "evolution_status": None,
            "skill_call_count": 0,
            "skill_last_call_time": None,
        }


def _news_fallback_akshare(symbol: Optional[str] = None, limit: int = 50) -> List[dict]:
    """当 DuckDB 无新闻时，从 akshare 东方财富拉取个股/财经新闻作为补充（需安装 akshare）。"""
    try:
        import akshare as ak  # type: ignore
        code = (symbol or "000001").strip().split(".")[0]
        if len(code) < 5:
            code = "000001"
        df = ak.stock_news_em(symbol=code)
        if df is None or df.empty:
            return []
        out = []
        cols = [str(c) for c in df.columns.tolist()]
        title_col = next((c for c in ["新闻标题", "title"] if c in cols), cols[0] if cols else None)
        content_col = next((c for c in ["新闻内容", "content"] if c in cols), None)
        time_col = next((c for c in ["发布时间", "publish_time"] if c in cols), None)
        url_col = next((c for c in ["新闻链接", "url"] if c in cols), None)
        source_col = next((c for c in ["文章来源", "source"] if c in cols), None)
        for _, row in df.head(limit).iterrows():
            item = {
                "symbol": code,
                "title": str(row.get(title_col, "")) if title_col else "",
                "content": (str(row.get(content_col, ""))[:500]) if content_col else "",
                "publish_time": str(row.get(time_col, "")) if time_col else "",
                "url": str(row.get(url_col, "")) if url_col else "",
                "source": str(row.get(source_col, "东方财富")) if source_col else "东方财富",
                "source_site": "eastmoney",
                "sentiment_score": None,
                "sentiment_label": None,
            }
            out.append(item)
        return out
    except Exception:
        return []


@router.get("/news")
def get_news(symbol: Optional[str] = None, limit: int = 100) -> dict:
    """新闻列表：优先 DuckDB news_items；为空时从 akshare 东方财富补充。"""
    items: List[dict] = []
    source: Optional[str] = None
    try:
        from data_engine import get_astock_duckdb_available, get_news_from_astock_duckdb
        if get_astock_duckdb_available():
            items = get_news_from_astock_duckdb(symbol=symbol, limit=limit)
            if items:
                source = "duckdb"
    except Exception:
        pass
    if not items:
        items = _news_fallback_akshare(symbol=symbol, limit=min(limit, 50))
        if items:
            source = "akshare"
    sentiment = _news_sentiment_summary(items)
    return {"news": items, "source": source, "sentiment": sentiment}


def _news_sentiment_summary(items: List[dict]) -> Optional[dict]:
    """从新闻列表计算情感汇总：条数、均值、正面占比。"""
    if not items:
        return None
    scores = [float(x["sentiment_score"]) for x in items if x.get("sentiment_score") is not None]
    if not scores:
        return {"count": len(items), "avg_score": None, "positive_ratio": None}
    import statistics
    avg = statistics.mean(scores)
    positive = sum(1 for s in scores if s > 0) / len(scores)
    return {"count": len(items), "avg_score": round(avg, 2), "positive_ratio": round(positive, 2)}


@router.get("/strategies")
def list_strategies() -> dict:
    """List strategy types (stub)."""
    return {
        "strategies": [
            {"id": "trend_following", "name": "Trend Following"},
            {"id": "mean_reversion", "name": "Mean Reversion"},
            {"id": "breakout", "name": "Breakout"},
        ]
    }


def _save_backtest_to_strategy_market(strategy_id: str, name: str, result: dict) -> bool:
    """将回测结果写入 strategy_market 表。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables
        conn = get_conn(read_only=False)
        ensure_tables(conn)
        tr = result.get("total_return")
        return_pct = float(tr * 100) if tr is not None else None
        sharpe = result.get("sharpe_ratio")
        max_dd = result.get("max_drawdown")
        conn.execute("""
            INSERT INTO strategy_market (strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status, updated_at)
            VALUES (?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            ON CONFLICT (strategy_id) DO UPDATE SET
            name=EXCLUDED.name, return_pct=EXCLUDED.return_pct, sharpe_ratio=EXCLUDED.sharpe_ratio,
            max_drawdown=EXCLUDED.max_drawdown, status=EXCLUDED.status, updated_at=CURRENT_TIMESTAMP
        """, [strategy_id, name or strategy_id.replace("_", " ").title(), return_pct, sharpe, max_dd])
        conn.close()
        return True
    except Exception:
        return False


@router.get("/strategies/market")
def get_strategies_market(limit: int = 50) -> dict:
    """
    策略市场列表：id、名称、收益、Sharpe、回撤、状态。
    优先从 strategy_market 表读（回测结果写入）；再补 trade_signals 中 distinct strategy_id；最后补 stub。
    """
    items: List[dict] = []
    seen: set = set()
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=True)
            try:
                df = conn.execute(
                    """SELECT strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status
                       FROM strategy_market ORDER BY updated_at DESC LIMIT ?""",
                    [limit],
                ).fetchdf()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        sid = str(row.get("strategy_id") or "")
                        if not sid:
                            continue
                        seen.add(sid)
                        items.append({
                            "id": sid,
                            "name": str(row.get("name") or sid.replace("_", " ").title()),
                            "return_pct": float(row["return_pct"]) if row.get("return_pct") is not None else None,
                            "sharpe_ratio": float(row["sharpe_ratio"]) if row.get("sharpe_ratio") is not None else None,
                            "max_drawdown": float(row["max_drawdown"]) if row.get("max_drawdown") is not None else None,
                            "status": str(row.get("status") or "active"),
                        })
                df2 = conn.execute(
                    """SELECT DISTINCT COALESCE(strategy_id, 'ai_fusion') AS strategy_id
                       FROM trade_signals ORDER BY strategy_id LIMIT ?""",
                    [limit],
                ).fetchdf()
                if df2 is not None and not df2.empty:
                    for sid in df2["strategy_id"].astype(str).tolist():
                        if not sid or sid == "None":
                            sid = "ai_fusion"
                        if sid in seen:
                            continue
                        seen.add(sid)
                        items.append({
                            "id": sid,
                            "name": sid.replace("_", " ").title(),
                            "return_pct": None,
                            "sharpe_ratio": None,
                            "max_drawdown": None,
                            "status": "active",
                        })
            finally:
                conn.close()
    except Exception:
        pass
    stub = [
        {"id": "trend_following", "name": "Trend Following", "return_pct": 12.5, "sharpe_ratio": 2.1, "max_drawdown": 5.0, "status": "live"},
        {"id": "mean_reversion", "name": "Mean Reversion", "return_pct": 8.2, "sharpe_ratio": 1.8, "max_drawdown": 6.0, "status": "test"},
        {"id": "breakout", "name": "Breakout", "return_pct": 15.0, "sharpe_ratio": 1.9, "max_drawdown": 5.5, "status": "live"},
    ]
    for s in stub:
        if s["id"] not in seen:
            items.append(s)
    return {"items": items}


def _run_backtest_internal(
    symbol: str,
    start_date: Optional[str],
    end_date: Optional[str],
    signal_source: str = "trade_signals",
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
) -> dict:
    """Shared logic for POST and GET backtest. symbols 为逗号分隔多标的时走组合回测。"""
    import os
    import sys
    from datetime import datetime, timedelta
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    from backtest_engine import run_backtest_from_db, run_backtest_multi_from_db
    end = end_date or datetime.now().strftime("%Y-%m-%d")
    start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    sym_list = [s.strip() for s in (symbols or symbol).split(",") if s.strip()]
    if len(sym_list) > 1:
        out = run_backtest_multi_from_db(
            symbols=sym_list,
            start_date=start,
            end_date=end,
            signal_source=signal_source,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        base = {"symbols": sym_list, "start_date": start, "end_date": end, "signal_source": signal_source}
    else:
        sym = sym_list[0] if sym_list else symbol
        out = run_backtest_from_db(
            symbol=sym,
            start_date=start,
            end_date=end,
            signal_source=signal_source,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        base = {"symbol": sym, "start_date": start, "end_date": end, "signal_source": signal_source}
    return {
        **base,
        "equity_curve": out.get("equity_curve") or [],
        "sharpe_ratio": out.get("sharpe_ratio"),
        "max_drawdown": out.get("max_drawdown"),
        "total_return": out.get("total_return"),
        "win_rate_pct": out.get("win_rate_pct"),
        "profit_factor": out.get("profit_factor"),
        "total_profit": out.get("total_profit"),
        "trade_count": out.get("trade_count"),
        "error": out.get("error"),
    }


@router.post("/backtest/run")
def run_backtest_api(
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    signal_source: str = "trade_signals",
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
    strategy_id: Optional[str] = None,
    strategy_name: Optional[str] = None,
) -> dict:
    """
    回测：从 quant_system.duckdb 读日 K 与信号，返回资金曲线与风险指标。
    若提供 strategy_id（及可选 strategy_name），回测成功后写入 strategy_market 表，供策略市场页展示。
    """
    try:
        out = _run_backtest_internal(
            symbol, start_date, end_date,
            signal_source=signal_source, init_cash=init_cash, fees=fees,
            slippage=slippage, symbols=symbols,
        )
        if strategy_id and not out.get("error"):
            _save_backtest_to_strategy_market(strategy_id, strategy_name or strategy_id, out)
        return out
    except Exception as e:
        return {
            "symbol": symbol,
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "win_rate_pct": None,
            "profit_factor": None,
            "total_profit": None,
            "trade_count": None,
            "error": str(e),
        }


@router.post("/backtest/portfolio")
def run_backtest_portfolio_api(
    strategy_ids: List[str] = Body(..., description="Strategy IDs from strategy_market / trade_signals"),
    weights: Optional[List[float]] = Body(None),
    start_date: Optional[str] = Body(None),
    end_date: Optional[str] = Body(None),
    init_cash: float = Body(10000.0),
    fees: float = Body(0.001),
    slippage: float = Body(0.0),
) -> dict:
    """
    多策略组合回测：按 strategy_ids 与可选 weights 分配资金，各策略独立回测后按权重合并资金曲线与指标。
    """
    from datetime import datetime, timedelta
    import os
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    try:
        from backtest_engine.portfolio_backtest import run_portfolio_backtest
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        out = run_portfolio_backtest(
            strategy_ids=strategy_ids,
            start_date=start,
            end_date=end,
            weights=weights,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        return out
    except Exception as e:
        return {
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "per_strategy": [],
            "error": str(e),
        }


@router.get("/backtest/result")
def get_backtest_result(
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    signal_source: str = "trade_signals",
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
) -> dict:
    """GET 回测结果：便于前端直接拉取资金曲线与指标，参数同 POST /backtest/run。"""
    try:
        return _run_backtest_internal(
            symbol, start_date, end_date,
            signal_source=signal_source, fees=fees, slippage=slippage, symbols=symbols,
        )
    except Exception as e:
        return {
            "symbol": symbol,
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "win_rate_pct": None,
            "profit_factor": None,
            "total_profit": None,
            "trade_count": None,
            "error": str(e),
        }


@router.get("/portfolio/weights")
def get_portfolio_weights() -> dict:
    """Current portfolio weights (stub)."""
    return {"weights": {}, "capital": 0}


@router.get("/risk/status")
def risk_status() -> dict:
    """Risk checks status (stub)."""
    return {
        "drawdown_ok": True,
        "exposure_ok": True,
        "volatility_ok": True,
    }


def _risk_engine_module():
    """Lazy import risk_engine (requires risk-engine/src + data-pipeline on path)."""
    import os
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    for _d in ["risk-engine/src", "data-pipeline/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    from risk_engine import load_rules, evaluate, save_rule
    return load_rules, evaluate, save_rule


@router.get("/risk/rules")
def get_risk_rules() -> dict:
    """风控规则列表（从 risk_rules 表读取）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {"rules": []}
        conn = get_conn(read_only=True)
        load_rules, _, _ = _risk_engine_module()
        rules = load_rules(conn)
        conn.close()
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/rules")
def post_risk_rule(
    rule_type: str,
    value: float,
    enabled: bool = True,
    id: Optional[int] = None,
) -> dict:
    """新增或更新一条风控规则。rule_type: single_position_pct_max | max_drawdown_pct | max_exposure_pct。"""
    try:
        _, _, save_rule = _risk_engine_module()
        ok = save_rule(rule_type=rule_type, value=value, enabled=enabled, rule_id=id)
        return {"ok": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/check")
def post_risk_check(body: dict = Body(default={})) -> dict:
    """风控检查：body 含 positions（列表）、total_assets（float）、可选 equity_curve（列表），返回 pass 与 violations。"""
    try:
        _, evaluate, _ = _risk_engine_module()
        body = body or {}
        positions = body.get("positions") or []
        total_assets = float(body.get("total_assets") or 0)
        equity_curve = body.get("equity_curve")
        out = evaluate(positions=positions, total_assets=total_assets, equity_curve=equity_curve)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 认证与审计 ---

@router.post("/auth/login")
def post_auth_login(username: str = "", password: str = "") -> dict:
    """登录：校验通过后签发 JWT（可选；无 users 表时接受任意用户名返回 token）。"""
    try:
        from .auth.jwt_auth import create_access_token
        token = create_access_token(subject=username or "demo")
        return {"token": token, "user": username or "demo"}
    except Exception:
        return {
            "token": "stub_token_placeholder",
            "user": username or "demo",
        }


@router.get("/audit/logs")
def get_audit_logs(limit: int = 100) -> dict:
    """审计日志：最近请求记录。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {"logs": []}
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT id, method, path, client_host, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {"logs": []}
        return {"logs": df.to_dict("records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 执行模式与统一经纪接口 (execution-engine brokers) ---

def _execution_broker_module():
    import os
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    _p = os.path.join(_root, "execution-engine/src")
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
    from execution_engine.brokers import execution_mode, set_execution_mode, get_broker
    return execution_mode, set_execution_mode, get_broker


@router.get("/execution/mode")
def get_execution_mode() -> dict:
    """当前执行模式：simulated（模拟盘）或 live（实盘）。"""
    try:
        execution_mode, _, _ = _execution_broker_module()
        return {"mode": execution_mode()}
    except Exception as e:
        return {"mode": "simulated", "error": str(e)}


@router.post("/execution/mode")
def post_execution_mode(mode: str = "simulated") -> dict:
    """设置执行模式（仅当前进程/请求生效；持久化需配置 EXECUTION_MODE 环境变量）。"""
    try:
        _, set_execution_mode, _ = _execution_broker_module()
        set_execution_mode(mode)
        return {"ok": True, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 模拟盘 Simulated Execution (execution-engine) ---

def _simulated_module():
    """Lazy import execution_engine.simulated (requires execution-engine/src on path)."""
    import os
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    _p = os.path.join(_root, "execution-engine/src")
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
    from execution_engine.simulated import (
        step_simulated,
        get_positions as sim_get_positions,
        get_orders as sim_get_orders,
        get_account_snapshots as sim_get_account_snapshots,
    )
    return step_simulated, sim_get_positions, sim_get_orders, sim_get_account_snapshots


@router.post("/simulated/step")
def post_simulated_step(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    lot_size: int = 100,
    max_buys: int = 10,
    max_sells: int = 10,
) -> dict:
    """
    执行一步模拟盘：根据 trade_signals 生成模拟订单，更新持仓与资金快照。
    返回本步 orders_created、cash、equity、total_assets。
    """
    try:
        step_simulated, _, _, _ = _simulated_module()
        return step_simulated(
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            lot_size=lot_size,
            max_buys=max_buys,
            max_sells=max_sells,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/positions")
def get_simulated_positions(limit: int = 100) -> dict:
    """模拟盘当前持仓列表。"""
    try:
        _, sim_get_positions, _, _ = _simulated_module()
        positions = sim_get_positions(limit=limit)
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/orders")
def get_simulated_orders(limit: int = 100, status: Optional[str] = None) -> dict:
    """模拟盘订单列表；status 可选 pending/filled。"""
    try:
        _, _, sim_get_orders, _ = _simulated_module()
        orders = sim_get_orders(limit=limit, status=status)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulated/account_snapshots")
def get_simulated_account_snapshots(limit: int = 100) -> dict:
    """模拟盘资金快照历史。"""
    try:
        _, _, _, sim_get_account_snapshots = _simulated_module()
        snapshots = sim_get_account_snapshots(limit=limit)
        return {"snapshots": snapshots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/equity_curve")
def get_execution_equity_curve(limit: int = 200) -> dict:
    """执行层资金曲线：从 sim_account_snapshots 聚合，供前端资金曲线图。"""
    try:
        _, _, _, sim_get_account_snapshots = _simulated_module()
        snapshots = sim_get_account_snapshots(limit=limit)
        # 按时间正序返回 [{ date, value }, ...]
        curve = []
        for s in reversed(snapshots):
            ts = s.get("snapshot_time")
            v = s.get("total_assets")
            if ts is not None and v is not None:
                dt = ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
                curve.append({"date": dt, "value": float(v)})
        return {"equity_curve": curve}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
def get_positions() -> dict:
    """Current positions (stub)."""
    return {"positions": []}


@router.post("/ai/generate-strategies")
def generate_strategies(count: int = 5) -> dict:
    """Generate strategies via AI (stub)."""
    return {"generated": [], "count": count}


# --- Frontend API (Dashboard, Evolution, Trades) ---

def _dashboard_from_duckdb() -> Optional[dict]:
    """当 newhigh 本地 DuckDB 可用时，用 A 股日线聚合出真实收益曲线与今日收益。"""
    try:
        from data_engine import get_astock_duckdb_available, get_stocks_for_api, fetch_klines_from_astock_duckdb
        if not get_astock_duckdb_available():
            return None
        stocks = get_stocks_for_api()
        if not stocks:
            return None
        # 选一只有日线数据的标的（首只可能无 bar，如 60081.SH）
        rows = []
        sym = None
        for s in stocks[:50]:
            sym = s["symbol"]
            rows = fetch_klines_from_astock_duckdb(sym, limit=60)
            if len(rows) >= 2:
                break
        if len(rows) < 2:
            return None
        closes = [r.close for r in rows]
        # 收益曲线：归一化到 10M 起，按收益率缩放
        base = closes[0]
        if base <= 0:
            return None
        equity_curve = [10e6 * (c / base) for c in closes]
        last_close, prev_close = closes[-1], closes[-2]
        daily_return_pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
        total_equity = equity_curve[-1] if equity_curve else 10e6
        return {
            "total_equity": total_equity,
            "daily_return_pct": round(daily_return_pct, 2),
            "sharpe_ratio": 2.1,
            "max_drawdown_pct": 6.3,
            "equity_curve": equity_curve,
            "top_strategies": [
                {"id": "STR_001", "name": "Strategy A", "return_pct": 32},
                {"id": "STR_002", "name": "Strategy B", "return_pct": 28},
                {"id": "STR_003", "name": "Strategy C", "return_pct": 21},
            ],
            "ai_generated_today": 1243,
            "strategies_alive": 63,
            "strategies_live": 12,
        }
    except Exception:
        return None


@router.get("/dashboard")
def get_dashboard() -> dict:
    """Dashboard：有 DuckDB 时用 A 股日线算真实 equity_curve / daily_return_pct / total_equity，其余可 stub。"""
    out = _dashboard_from_duckdb()
    if out is not None:
        return out
    return {
        "total_equity": 12_340_000,
        "daily_return_pct": 2.34,
        "sharpe_ratio": 2.1,
        "max_drawdown_pct": 6.3,
        "equity_curve": [10e6, 10.2e6, 10.5e6, 11e6, 11.8e6, 12.34e6],
        "top_strategies": [
            {"id": "STR_001", "name": "Strategy A", "return_pct": 32},
            {"id": "STR_002", "name": "Strategy B", "return_pct": 28},
            {"id": "STR_003", "name": "Strategy C", "return_pct": 21},
        ],
        "ai_generated_today": 1243,
        "strategies_alive": 63,
        "strategies_live": 12,
    }


@router.get("/evolution")
def get_evolution() -> dict:
    """Evolution: generation, best strategy, tree (stub)."""
    return {
        "current_generation": 3,
        "best_strategy": {"id": "STR_0034", "sharpe": 2.6, "return_pct": 41},
        "generations": [{"gen": 1}, {"gen": 2}, {"gen": 3}],
    }


@router.post("/evolution/run")
def post_evolution_run(
    population_limit: int = 10,
    symbol: str = "000001.SZ",
) -> dict:
    """执行一轮 OpenClaw 进化：从策略市场加载种群，遗传+回测评估，优秀个体写回 strategy_market。"""
    try:
        import os
        import sys
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        for _d in ["openclaw_engine", "backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = os.path.join(_root, _d)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from openclaw_engine import run_evolution_cycle
        return run_evolution_cycle(population_limit=population_limit, symbol=symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_evolution_background(task_id: str, population_limit: int, symbol: str) -> None:
    """后台执行进化并更新 evolution_tasks 表。"""
    import json
    try:
        import os
        import sys
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        for _d in ["openclaw_engine", "backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = os.path.join(_root, _d)
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)
        from openclaw_engine import run_evolution_cycle
        result = run_evolution_cycle(population_limit=population_limit, symbol=symbol)
        status, res_str = "success", json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        status, res_str = "failed", json.dumps({"error": str(e)}, ensure_ascii=False)
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        if __import__("os").path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            conn.execute(
                "UPDATE evolution_tasks SET status = ?, result = ? WHERE task_id = ?",
                [status, res_str, task_id],
            )
            conn.close()
    except Exception:
        pass


@router.post("/evolution/trigger")
def post_evolution_trigger(
    task_type: str = "strategy_generation",
    population_limit: int = 10,
    symbol: str = "000001.SZ",
) -> dict:
    """触发 OpenClaw 进化任务（异步），返回 task_id；前端可轮询 GET /api/evolution/status/{task_id}。"""
    import uuid
    import threading
    task_id = str(uuid.uuid4())
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            conn.execute(
                "INSERT INTO evolution_tasks (task_id, status, result) VALUES (?, ?, ?)",
                [task_id, "pending", None],
            )
            conn.close()
    except Exception:
        pass
    t = threading.Thread(
        target=_run_evolution_background,
        args=(task_id, population_limit, symbol),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id, "status": "pending"}


@router.get("/evolution/status/{task_id}")
def get_evolution_status(task_id: str) -> dict:
    """查询 OpenClaw 进化任务状态与结果。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        import json
        if not os.path.isfile(get_db_path()):
            return {"task_id": task_id, "status": "PENDING", "result": None}
        conn = get_conn(read_only=True)
        row = conn.execute(
            "SELECT status, result FROM evolution_tasks WHERE task_id = ?",
            [task_id],
        ).fetchone()
        conn.close()
        if not row:
            return {"task_id": task_id, "status": "PENDING", "result": None}
        status, res_str = row[0], row[1]
        result = None
        if res_str:
            try:
                result = json.loads(res_str)
            except Exception:
                result = res_str
        return {"task_id": task_id, "status": status.upper(), "result": result}
    except Exception:
        return {"task_id": task_id, "status": "PENDING", "result": None}


@router.get("/evolution/tasks")
def get_evolution_tasks(limit: int = 5) -> dict:
    """最近若干次进化任务列表，供系统监控页展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os
        if not os.path.isfile(get_db_path()):
            return {"tasks": []}
        conn = get_conn(read_only=True)
        df = conn.execute(
            "SELECT task_id, status, result, created_at FROM evolution_tasks ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {"tasks": []}
        tasks = []
        for _, row in df.iterrows():
            tasks.append({
                "id": str(row.get("task_id", "")),
                "status": str(row.get("status", "pending")),
                "result": row.get("result"),
                "created_at": row.get("created_at").isoformat() if hasattr(row.get("created_at"), "isoformat") else str(row.get("created_at")) if row.get("created_at") else None,
            })
        return {"tasks": tasks}
    except Exception:
        return {"tasks": []}


@router.get("/trades")
def get_trades(limit: int = 50) -> dict:
    """Recent trades (stub)."""
    return {
        "trades": [
            {"time": "2025-03-07T10:00:00Z", "strategy": "STR_001", "symbol": "BTCUSDT", "side": "BUY", "qty": 0.1, "price": 95000},
            {"time": "2025-03-07T09:30:00Z", "strategy": "STR_002", "symbol": "ETHUSDT", "side": "SELL", "qty": 1.0, "price": 3500},
        ][:limit],
    }


@router.get("/alpha-lab")
def get_alpha_lab() -> dict:
    """Alpha Lab funnel (stub)."""
    return {
        "generated_today": 1243,
        "passed_backtest": 217,
        "passed_risk": 64,
        "deployed": 12,
    }
