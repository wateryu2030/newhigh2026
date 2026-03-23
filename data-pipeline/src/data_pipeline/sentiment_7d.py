"""
全市场 7 维情绪评分（0–100），思路对齐 ClawHub「A Stock Monitor」描述，
数据源：a_stock_realtime 最新快照或 akshare 全市场现货。
不含 GUI 自动化、无硬编码密钥。
"""
from __future__ import annotations

import math
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
    if n < 100:
        return {"error": "too_few_rows", "count": n}

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
    try:
        import akshare as ak
    except ImportError:
        return {"error": "akshare_not_installed"}
    try:
        df = ak.stock_zh_a_spot_em()
    except Exception as e:
        return {"error": "akshare_failed", "detail": str(e)[:200]}
    if df is None or df.empty:
        return {"error": "empty_spot"}
    return _from_spot_df(df)


def compute_sentiment_7d_from_duckdb() -> Optional[Dict[str, Any]]:
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

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
    优先用库内最新实时快照（与管道一致）；失败或非交易时段数据过旧时拉 akshare。
    """
    if prefer_db:
        out = compute_sentiment_7d_from_duckdb()
        if out and "error" not in out:
            out["data_source"] = "duckdb_a_stock_realtime"
            return out
    out = compute_sentiment_7d_from_akshare()
    if "error" in out:
        return out
    out["data_source"] = "akshare_stock_zh_a_spot_em"
    return out
