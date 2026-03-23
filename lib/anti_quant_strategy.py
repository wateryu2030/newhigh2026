"""
反量化长线选股策略 - 核心计算模块

供 scripts/anti_quant_long_term_strategy.py 与 gateway API 共用。
基于 5 年十大股东数据计算股东稳定性、机构纯度、换主频率等因子。
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

# =============================================================================
# 可调优参数
# =============================================================================
CONFIG = {
    "top10_ratio_std_max": 5.0,
    "long_term_institution_min": 3,
    "turnover_avg_max": 2.0,
    "market_cap_min_yi": 100.0,
    "long_term_institution_keywords": [
        "社保", "养老", "QFII", "易方达", "华夏", "嘉实", "博时", "广发",
        "南方", "汇添富", "富国", "招商", "工银", "中欧", "兴证全球",
        "香港中央结算", "境外", "全国社保", "UBS", "摩根", "高盛", "中央汇金",
    ],
    "long_term_min_quarters": 8,
    "long_term_partial_quarters": 4,
    "years_back": 5,
    "min_reports": 4,
    # 稀疏数据下的放宽阈值
    "relaxed_top10_ratio_min": 50.0,
    "relaxed_institution_count_min": 2,
}


def _is_long_term_institution(name: str, stype: str) -> bool:
    t = (name + " " + str(stype)).lower()
    for kw in CONFIG["long_term_institution_keywords"]:
        if kw.lower() in t:
            return True
    return False


def load_data_from_duckdb(db_path: Optional[str] = None) -> pd.DataFrame:
    """从 DuckDB 加载十大股东数据"""
    from lib.database import get_connection, get_db_path
    path = db_path or get_db_path()
    conn = get_connection(read_only=False)
    if conn is None:
        raise RuntimeError("数据库连接失败")
    try:
        df = conn.execute("""
            SELECT stock_code, report_date, rank, shareholder_name, shareholder_type,
                   share_ratio as shareholding_ratio
            FROM top_10_shareholders
            WHERE share_ratio IS NOT NULL AND share_ratio > 0
            ORDER BY stock_code, report_date, rank
        """).fetchdf()
    finally:
        conn.close()
    df["report_date"] = pd.to_datetime(df["report_date"])
    df["shareholder_name"] = df["shareholder_name"].fillna("").astype(str).str.strip()
    df["shareholder_type"] = df["shareholder_type"].fillna("").astype(str).str.strip()
    return df


def calc_top10_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """计算每只股票每报告期的 top10_ratio"""
    agg = df.groupby(["stock_code", "report_date"])["shareholding_ratio"].sum().reset_index()
    agg.columns = ["stock_code", "report_date", "top10_ratio"]
    return agg


def calc_top10_ratio_std(ratio_df: pd.DataFrame) -> pd.DataFrame:
    """计算 top10_ratio 的标准差（需至少 2 个报告期）"""
    std_df = ratio_df.groupby("stock_code")["top10_ratio"].std().reset_index()
    std_df.columns = ["stock_code", "top10_ratio_std"]
    return std_df


def calc_long_term_institution_count(df: pd.DataFrame) -> pd.DataFrame:
    """长期机构家数：匹配关键词且连续出现 8+ 季度"""
    mask = df.apply(
        lambda r: _is_long_term_institution(r["shareholder_name"], r["shareholder_type"]),
        axis=1
    )
    inst_df = df[mask][["stock_code", "report_date", "shareholder_name"]].drop_duplicates()
    inst_df = inst_df.sort_values(["stock_code", "shareholder_name", "report_date"])
    reports = inst_df.groupby(["stock_code", "shareholder_name"])["report_date"].apply(
        lambda x: len(x.drop_duplicates())
    ).reset_index()
    reports.columns = ["stock_code", "shareholder_name", "quarter_count"]

    def _score(cnt: int) -> float:
        if cnt >= CONFIG["long_term_min_quarters"]:
            return 1.0
        if cnt >= CONFIG["long_term_partial_quarters"]:
            return 0.5
        return 0.0

    reports["score"] = reports["quarter_count"].map(_score)
    agg = reports.groupby("stock_code")["score"].sum().reset_index()
    agg.columns = ["stock_code", "long_term_institution_count"]
    return agg


def calc_institution_count_current(df: pd.DataFrame) -> pd.DataFrame:
    """
    当前报告期机构数量（无连续性要求）。
    用于数据稀疏时替代 long_term_institution_count。
    """
    latest_dates = df.groupby("stock_code")["report_date"].max().reset_index()
    latest_dates.columns = ["stock_code", "latest_date"]
    merged = df.merge(latest_dates, left_on=["stock_code", "report_date"], right_on=["stock_code", "latest_date"])
    mask = merged.apply(
        lambda r: _is_long_term_institution(r["shareholder_name"], r["shareholder_type"]),
        axis=1
    )
    inst = merged[mask].groupby("stock_code")["shareholder_name"].nunique().reset_index()
    inst.columns = ["stock_code", "institution_count_current"]
    return inst


def calc_turnover_avg(df: pd.DataFrame) -> pd.DataFrame:
    """相邻报告期股东更换家数的平均值"""
    dates = sorted(df["report_date"].unique())
    if len(dates) < 2:
        return pd.DataFrame(columns=["stock_code", "turnover_avg"])

    out = []
    for sc, g in df.groupby("stock_code"):
        g = g.sort_values("report_date")
        periods = g.groupby("report_date")["shareholder_name"].apply(set).to_dict()
        dates_sc = sorted(periods.keys())
        turnovers = []
        for i in range(1, len(dates_sc)):
            prev = periods[dates_sc[i - 1]]
            curr = periods[dates_sc[i]]
            new_count = len(curr - prev)
            exit_count = len(prev - curr)
            turnovers.append(min(new_count, exit_count))
        avg = np.mean(turnovers) if turnovers else 0.0
        out.append({"stock_code": sc, "turnover_avg": round(avg, 2)})
    return pd.DataFrame(out)


def calc_factors(df: pd.DataFrame) -> pd.DataFrame:
    """计算全部因子"""
    ratio_df = calc_top10_ratio(df)
    std_df = calc_top10_ratio_std(ratio_df)
    inst_df = calc_long_term_institution_count(df)
    inst_current_df = calc_institution_count_current(df)
    turnover_df = calc_turnover_avg(df)
    latest = df.groupby("stock_code")["report_date"].max().reset_index()
    latest.columns = ["stock_code", "latest_report_date"]

    result = ratio_df.sort_values(["stock_code", "report_date"]).groupby("stock_code").agg(
        top10_ratio_latest=("top10_ratio", "last"),
        report_count=("report_date", "count"),
    ).reset_index()
    result = result.merge(std_df, on="stock_code", how="left")
    result = result.merge(inst_df, on="stock_code", how="left")
    result = result.merge(inst_current_df, on="stock_code", how="left")
    result = result.merge(turnover_df, on="stock_code", how="left")
    result = result.merge(latest, on="stock_code", how="left")

    result["top10_ratio_std"] = result["top10_ratio_std"].fillna(np.nan)
    result["long_term_institution_count"] = result["long_term_institution_count"].fillna(0)
    result["institution_count_current"] = result["institution_count_current"].fillna(0)
    result["turnover_avg"] = result["turnover_avg"].fillna(np.nan)
    result["data_sufficient"] = result["report_count"] >= CONFIG["min_reports"]
    return result


def filter_stocks(
    factors_df: pd.DataFrame,
    market_cap_df: Optional[pd.DataFrame] = None,
    use_relaxed: bool = True,
) -> pd.DataFrame:
    """
    按规则筛选。当 use_relaxed=True 且数据不足时，使用放宽条件。
    """
    cfg = CONFIG
    f = factors_df.copy()

    # 严格模式：需满足 min_reports
    strict_mask = f["data_sufficient"]
    f_strict = f[strict_mask]
    f_strict = f_strict[f_strict["top10_ratio_std"] < cfg["top10_ratio_std_max"]]
    f_strict = f_strict[f_strict["long_term_institution_count"] >= cfg["long_term_institution_min"]]
    turn_ok = f_strict["turnover_avg"].isna() | (f_strict["turnover_avg"] <= cfg["turnover_avg_max"])
    f_strict = f_strict[turn_ok]
    if market_cap_df is not None and not market_cap_df.empty:
        f_strict = f_strict.merge(market_cap_df, on="stock_code", how="inner")
        f_strict = f_strict[f_strict["market_cap_yi"] >= cfg["market_cap_min_yi"]]

    if not f_strict.empty:
        f_strict = f_strict.assign(filter_mode="strict")
        return f_strict

    # 放宽模式
    if not use_relaxed:
        return pd.DataFrame()

    f_relaxed = f[
        (f["top10_ratio_latest"] >= cfg["relaxed_top10_ratio_min"])
        & (f["institution_count_current"] >= cfg["relaxed_institution_count_min"])
    ]
    f_relaxed = f_relaxed.assign(filter_mode="relaxed")
    return f_relaxed.sort_values("top10_ratio_latest", ascending=False)


def run_strategy(
    df: Optional[pd.DataFrame] = None,
    years_back: Optional[int] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    执行策略，返回 (factors_df, candidates_df)。
    df 为 None 时从 DuckDB 加载。
    """
    if df is None:
        df = load_data_from_duckdb()
    if years_back is not None:
        cfg_years = CONFIG.get("years_back", 5)
        CONFIG["years_back"] = years_back
    try:
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=CONFIG["years_back"])
        df = df[df["report_date"] >= cutoff].copy()
        factors = calc_factors(df)
        candidates = filter_stocks(factors, use_relaxed=True)
        return factors, candidates
    finally:
        if years_back is not None:
            CONFIG["years_back"] = years_back
