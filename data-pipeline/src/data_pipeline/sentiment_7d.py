"""
全市场 7 维情绪评分（0–100），思路对齐 ClawHub「A Stock Monitor」描述，
数据源（按优先级）：
  1) a_stock_realtime（东财口径快照，UPDATE_REALTIME_FIRST 等）
  2) AkShare stock_zh_a_spot_em（东财全市场现货，SENTIMENT_7D_AKSHARE_ENABLE）
  3) 可选 AkShare 新浪现货（SENTIMENT_7D_USE_SINA_SPOT，默认关）
  4) a_stock_daily（Tushare 等日 K，依赖 MAX(date) 及时增量）
不含 GUI 自动化、无硬编码密钥。
"""
from __future__ import annotations

import concurrent.futures
import math
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


WEIGHTS = {
    "gain_loss_ratio": 0.20,
    "avg_change": 0.20,
    "limit_ratio": 0.15,
    "strong_ratio": 0.15,
    "volume_activity": 0.10,
    "volatility": 0.10,
    "trend_strength": 0.10,
}

LEVELS: List[Tuple[float, float, str, str]] = [
    (80, 100, "极度乐观", "🔴"),
    (65, 79, "乐观", "🟠"),
    (55, 64, "偏乐观", "🟢"),
    (45, 54, "中性", "⚪"),
    (35, 44, "偏悲观", "🔵"),
    (20, 34, "悲观", "🟣"),
    (0, 19, "极度悲观", "⚫"),
]


def _level(score: float) -> Tuple[str, str]:
    for lo, hi, name, emoji in LEVELS:
        if lo <= score <= hi:
            return name, emoji
    return "中性", "⚪"


def _from_spot_df(df: pd.DataFrame) -> Dict[str, Any]:
    """东方财富现货列：涨跌幅、成交额等。"""
    pct_col = "涨跌幅" if "涨跌幅" in df.columns else "change_pct"
    amt_col = "成交额" if "成交额" in df.columns else "amount"
    code_col = "代码" if "代码" in df.columns else "code"
    if pct_col not in df.columns:
        return {"error": "missing_change_pct_column", "columns": list(df.columns)}

    s = df[pct_col].astype(float)
    # 仅 A 股六位代码
    if code_col in df.columns:
        codes = df[code_col].astype(str).str.replace(".SZ", "").str.replace(".SH", "")
        mask = codes.str.match(r"^\d{6}$")
        s = s[mask]
        df = df[mask].copy()
    n = len(s)
    min_n = max(30, int(os.environ.get("SENTIMENT_7D_MIN_STOCKS", "50")))
    if n < min_n:
        return {"error": "too_few_rows", "count": n, "min_required": min_n}

    gainers = (s > 0.01).sum()
    losers = (s < -0.01).sum()
    flat = n - gainers - losers
    gl_total = gainers + losers
    r_gl = (gainers / max(losers, 1)) if losers else 2.0
    sub_gl = min(100, max(0, 50 + (r_gl - 1) * 35))

    mean_pct = float(s.mean())
    sub_avg = min(100, max(0, 50 + mean_pct * 18))

    pre = df[code_col].astype(str).str[:2] if code_col in df.columns else pd.Series(["00"] * len(s))
    is_20pct = pre.isin(["30", "68"])
    lu = int(((~is_20pct) & (s >= 9.8)).sum() + (is_20pct & (s >= 19.5)).sum())
    ld = int(((~is_20pct) & (s <= -9.8)).sum() + (is_20pct & (s <= -19.5)).sum())
    if ld == 0:
        sub_lim = min(100, 50 + min(lu, 50) * 1.0)
    else:
        sub_lim = min(100, max(0, 45 + (lu / ld) * 12))

    strong = (s > 3.0).sum()
    sub_strong = min(100, (strong / n) * 500)

    amt = df[amt_col].astype(float) if amt_col in df.columns else pd.Series([0.0] * n)
    total_amt = float(amt.sum())
    per_m = total_amt / max(n, 1) / 1e6
    sub_vol = min(100, math.log1p(max(per_m, 0.1)) * 12)

    std_pct = float(s.std()) if n > 1 else 0.0
    sub_vola = min(100, max(0, 25 + std_pct * 28))

    trend_n = (s > 1.0).sum()
    sub_trend = min(100, (trend_n / n) * 180)

    score = (
        sub_gl * WEIGHTS["gain_loss_ratio"]
        + sub_avg * WEIGHTS["avg_change"]
        + sub_lim * WEIGHTS["limit_ratio"]
        + sub_strong * WEIGHTS["strong_ratio"]
        + sub_vol * WEIGHTS["volume_activity"]
        + sub_vola * WEIGHTS["volatility"]
        + sub_trend * WEIGHTS["trend_strength"]
    )
    score = round(float(min(100, max(0, score))), 2)
    level, emoji = _level(score)

    return {
        "score": score,
        "level": level,
        "emoji": emoji,
        "description": f"全市场约 {n} 只标的综合情绪",
        "dimensions": {
            "gain_loss_ratio": round(sub_gl, 2),
            "avg_change": round(sub_avg, 2),
            "limit_up_down": round(sub_lim, 2),
            "strong_stock_ratio": round(sub_strong, 2),
            "volume_activity": round(sub_vol, 2),
            "volatility": round(sub_vola, 2),
            "trend_strength": round(sub_trend, 2),
        },
        "weights": WEIGHTS,
        "stats": {
            "total": int(n),
            "gainers": int(gainers),
            "losers": int(losers),
            "flat": int(flat),
            "limit_up_approx": int(lu),
            "limit_down_approx": int(ld),
            "strong_gt_3pct": int(strong),
            "avg_change_pct": round(mean_pct, 3),
            "total_amount_bn": round(total_amt / 1e8, 2),
        },
        "source_rows": int(n),
    }


def compute_sentiment_7d_from_akshare() -> Dict[str, Any]:
    """
    拉东财全市场现货；在服务器或隧道环境可能极慢，使用线程超时避免 Gateway 长时间挂起。
    超时秒数：环境变量 SENTIMENT_7D_AKSHARE_TIMEOUT_SEC（默认 12，失败则尽快走日 K 兜底）。
    默认临时剥离 *proxy* 环境变量（与 ashare_daily_kline 一致），避免本机坏代理导致 HTTPSConnectionPool 失败。
    若必须走公司代理，设 SENTIMENT_7D_STRIP_PROXY=0。
    """
    timeout = float(os.environ.get("SENTIMENT_7D_AKSHARE_TIMEOUT_SEC", "12"))

    def _fetch():
        import akshare as ak

        from data_pipeline.data_sources.ashare_daily_kline import (
            _pop_proxy_env_vars,
            _restore_env,
        )

        strip = os.environ.get("SENTIMENT_7D_STRIP_PROXY", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        saved = _pop_proxy_env_vars() if strip else {}
        try:
            return ak.stock_zh_a_spot_em()
        finally:
            _restore_env(saved)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_fetch)
            df = fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return {
            "error": "akshare_timeout",
            "detail": f"东财现货接口 {timeout:.0f}s 内未返回（常见于境外机房或被限速）。"
            "请在本机或同域服务器执行：UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py，"
            "将快照写入 DuckDB 后本接口将优先走库内数据。",
            "score": 0,
        }
    except Exception as e:
        return {"error": "akshare_failed", "detail": str(e)[:200]}
    if df is None or df.empty:
        return {"error": "empty_spot"}
    return _from_spot_df(df)


def compute_sentiment_7d_from_akshare_sina() -> Dict[str, Any]:
    """
    新浪财经全市场 A 股现货（列名含 涨跌幅/成交额/代码，与 _from_spot_df 兼容）。
    整表需分页抓取，默认超时较长；勿高频调用以免触发风控。
    """
    timeout = float(os.environ.get("SENTIMENT_7D_SINA_TIMEOUT_SEC", "120"))

    def _fetch():
        import akshare as ak

        return ak.stock_zh_a_spot()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_fetch)
            df = fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return {
            "error": "sina_spot_timeout",
            "detail": f"新浪现货 {timeout:.0f}s 内未返回（全市场约 60～90s+）。可适当调大 SENTIMENT_7D_SINA_TIMEOUT_SEC。",
            "score": 0,
        }
    except Exception as e:
        return {"error": "sina_spot_failed", "detail": str(e)[:220], "score": 0}
    if df is None or df.empty:
        return {"error": "empty_sina_spot", "score": 0}
    return _from_spot_df(df)


def compute_sentiment_7d_from_daily() -> Optional[Dict[str, Any]]:
    """
    用统一 DuckDB 中 **最近一个交易日** 的 close 与 **前一交易日** close 推算涨跌幅，
    再走与现货相同的 7 维加权逻辑。不访问东财，仅 SQL + 本地表。
    失败时返回 {"error": ...} 以便接口拼接原因（不再静默 None）。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not os.path.isfile(path):
            return {
                "error": "daily_no_database",
                "detail": f"DuckDB 文件不存在: {path}（请设置 QUANT_SYSTEM_DUCKDB_PATH）",
            }
        conn = get_conn(read_only=False)
        # 最近若干 DISTINCT 交易日，从中找「相邻两日 + 有效 join 行数 ≥ 阈值」的第一对。
        # 避免仅个别标的写入最新 date（增量未跑完）时全局 MAX(date) 只有 1 行、情绪整条链路失败。
        min_n = max(30, int(os.environ.get("SENTIMENT_7D_MIN_STOCKS", "50")))
        max_pairs = max(3, int(os.environ.get("SENTIMENT_7D_DAILY_DATE_LOOKBACK", "25")))
        date_rows = conn.execute(
            """
            SELECT DISTINCT date FROM a_stock_daily ORDER BY date DESC LIMIT ?
            """,
            [max_pairs + 1],
        ).fetchall()
        dates = [r[0] for r in date_rows if r and r[0] is not None]
        if not dates:
            conn.close()
            return {"error": "daily_empty_table", "detail": "a_stock_daily 无数据，请先 Tushare 回补"}
        if len(dates) < 2:
            conn.close()
            return {
                "error": "daily_single_date_only",
                "detail": "a_stock_daily 仅有一个交易日，无法算涨跌",
            }
        d_last = d_prev = None
        best_diag: List[str] = []
        for i in range(min(len(dates) - 1, max_pairs)):
            dl, dp = dates[i], dates[i + 1]
            cnt_row = conn.execute(
                """
                SELECT COUNT(*) FROM a_stock_daily AS a
                INNER JOIN a_stock_daily AS b
                  ON a.code = b.code AND a.date = ? AND b.date = ?
                WHERE b.close IS NOT NULL AND b.close > 0 AND a.close IS NOT NULL
                """,
                [dl, dp],
            ).fetchone()
            cnt = int(cnt_row[0]) if cnt_row else 0
            if len(best_diag) < 5:
                best_diag.append(f"{str(dl)[:10]}/{str(dp)[:10]}:{cnt}")
            if cnt >= min_n:
                d_last, d_prev = dl, dp
                break
        if d_last is None or d_prev is None:
            conn.close()
            return {
                "error": "daily_no_valid_date_pair",
                "detail": (
                    f"最近 {len(dates)} 个交易日无相邻两日同时满足 ≥{min_n} 只有效涨跌样本（"
                    f"示例计数 {', '.join(best_diag)}）；请补全最新交易日全市场日 K 或稍后重试。"
                ),
            }
        df = conn.execute(
            """
            SELECT
                a.code::VARCHAR AS code,
                (a.close - b.close) / NULLIF(b.close, 0) * 100.0 AS change_pct,
                COALESCE(a.amount, 0.0) AS amount
            FROM a_stock_daily AS a
            INNER JOIN a_stock_daily AS b
              ON a.code = b.code AND a.date = ? AND b.date = ?
            WHERE b.close IS NOT NULL AND b.close > 0 AND a.close IS NOT NULL
            """,
            [d_last, d_prev],
        ).df()
        conn.close()
        if df is None or df.empty:
            return {
                "error": "daily_no_rows_latest_date",
                "detail": f"最新交易日 {str(d_last)[:10]} 无有效涨跌行（缺前一日 close？）",
            }
        df = df.rename(columns={"change_pct": "涨跌幅", "amount": "成交额"})
        out = _from_spot_df(df)
        if "error" in out:
            return {
                "error": "daily_spot_rules_failed",
                "detail": str(out.get("error"))
                + (f" count={out.get('count')}" if out.get("count") is not None else ""),
            }
        d_s = str(d_last)[:10]
        out["trade_date"] = d_s
        try:
            d_ld = d_last if isinstance(d_last, date) else date.fromisoformat(d_s)
            lag = (date.today() - d_ld).days
            out["calendar_lag_days"] = max(0, lag)
        except Exception:
            lag = None
            out["calendar_lag_days"] = None
        lag_hint = ""
        if lag is not None and lag >= 2:
            lag_hint = (
                f" 提醒：日 K 最新收盘日为 {d_s}，距今已 {lag} 个自然日；"
                "请跑 Tushare 增量（scripts/run_tushare_incremental.py 或调度），"
                "或交易时段写入东财实时表（UPDATE_REALTIME_FIRST=1 …）。"
            )
        out["description"] = (
            f"基于交易日 {d_s} 收盘相对前一日的全市场近似情绪（日 K，非盘中快照）；"
            f"样本约 {out.get('stats', {}).get('total', '?')} 只。{lag_hint}"
        )
        return out
    except Exception as ex:
        return {"error": "daily_exception", "detail": str(ex)[:220]}


def compute_sentiment_7d_from_duckdb() -> Optional[Dict[str, Any]]:
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return None
        conn = get_conn(read_only=False)
        row = conn.execute(
            "SELECT MAX(snapshot_time) FROM a_stock_realtime"
        ).fetchone()
        if not row or row[0] is None:
            conn.close()
            return None
        t = row[0]
        df = conn.execute(
            """
            SELECT code, change_pct, amount, volume
            FROM a_stock_realtime
            WHERE snapshot_time = ?
            """,
            [t],
        ).df()
        conn.close()
        if df is None or df.empty:
            return None
        df = df.rename(columns={"change_pct": "涨跌幅", "amount": "成交额"})
        return _from_spot_df(df)
    except Exception:
        return None


def get_market_sentiment_7d(prefer_db: bool = True) -> Dict[str, Any]:
    """
    顺序（可配）：

    - 默认（``SENTIMENT_7D_DAILY_BEFORE_SPOT=1``）：库内实时 → **日 K 快路径** → 东财现货 → 新浪 → 兜底。
      日 K 查询已优化为仅扫最近两个交易日，避免全表 LAG 卡死；东财 ``spot_em`` 在弱网可能跑数分钟，
      故默认先给可响应的 DuckDB 结果。
    - 设 ``SENTIMENT_7D_DAILY_BEFORE_SPOT=0``：恢复「实时 → 东财 → 新浪 → 日 K」，优先盘中现货。
    """
    errors: List[str] = []

    daily_on = os.environ.get("SENTIMENT_7D_DAILY_FALLBACK", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    daily_before_spot = os.environ.get("SENTIMENT_7D_DAILY_BEFORE_SPOT", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )

    if prefer_db:
        out = compute_sentiment_7d_from_duckdb()
        if out and "error" not in out:
            out["data_source"] = "duckdb_a_stock_realtime"
            return out

    if daily_before_spot and daily_on:
        out_d = compute_sentiment_7d_from_daily()
        if out_d:
            if "error" not in out_d:
                out_d["data_source"] = "duckdb_a_stock_daily"
                return out_d
            err = str(out_d.get("error", "daily"))
            tail = out_d.get("detail") or ""
            errors.append(f"{err}:{tail[:80]}")

    # 默认关：东财 spot_em 全市场抓取在弱网/境外常数分钟且线程难中断；有日 K 时由 DAILY_BEFORE_SPOT 已足够。
    # 需要盘中全市场现货时再设 SENTIMENT_7D_AKSHARE_ENABLE=1（可配合 DAILY_BEFORE_SPOT=0）。
    ak_em = os.environ.get("SENTIMENT_7D_AKSHARE_ENABLE", "0").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    if ak_em:
        out = compute_sentiment_7d_from_akshare()
        if out and "error" not in out:
            out["data_source"] = "akshare_stock_zh_a_spot_em"
            return out
        if out and out.get("error"):
            errors.append(str(out.get("error")))

    sina_on = os.environ.get("SENTIMENT_7D_USE_SINA_SPOT", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if sina_on:
        out_s = compute_sentiment_7d_from_akshare_sina()
        if out_s and "error" not in out_s:
            out_s["data_source"] = "akshare_stock_zh_a_spot_sina"
            return out_s
        if out_s and out_s.get("error"):
            errors.append(str(out_s.get("error")))

    if (not daily_before_spot) and daily_on:
        out_d = compute_sentiment_7d_from_daily()
        if out_d:
            if "error" not in out_d:
                out_d["data_source"] = "duckdb_a_stock_daily"
                return out_d
            err = str(out_d.get("error", "daily"))
            tail = out_d.get("detail") or ""
            errors.append(f"{err}:{tail[:80]}")

    detail = (
        "东财现货失败且日 K 不可用：若为本机代理问题可保持 SENTIMENT_7D_STRIP_PROXY=1（默认）；"
        "确认 Gateway 使用的 DuckDB 路径与写入 Tushare 的库一致；"
        "或 UPDATE_REALTIME_FIRST=1 写入东财快照；境外仅东财不通时可设 SENTIMENT_7D_USE_SINA_SPOT=1。"
    )
    if errors:
        detail = f"尝试记录: {', '.join(errors)}。{detail}"
    return {
        "error": "all_sources_exhausted",
        "detail": detail,
        "score": 0,
        "level": "未知",
        "emoji": "❓",
    }
