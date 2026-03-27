"""
股东「筹码结构」辅助指标：在前十大持股基础上，补充集中度 HHI、占比边际变化、综合筹码得分。

与 anti_quant_strategy 因子互补：后者偏「机构长线 + 稳定性」，本模块偏「筹码集中/发散」可读性，
便于投研侧与龙虎榜、量能等并列解读。

公式说明：
- HHI（前十大）：sum((持股占比/100)^2)，数值越高通常表示筹码越向头部股东集中。
- top10_delta_pp：最近两期前十大合计持股占比之差（百分点）；为正表示报告期口径下筹码更集中。
- chip_score：启发式 0–100 分，用于排序而非投资建议。
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def _ratio_col(df: pd.DataFrame) -> str:
    if "shareholding_ratio" in df.columns:
        return "shareholding_ratio"
    if "share_ratio" in df.columns:
        return "share_ratio"
    raise ValueError("need shareholding_ratio or share_ratio")


def calc_hhi_latest(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    每只股票「最近一期报告」的前十大 HHI。
    raw_df：与 anti_quant 一致，含 stock_code, report_date, share_ratio 或 shareholding_ratio
    """
    if raw_df.empty:
        return pd.DataFrame(columns=["stock_code", "hhi_top10"])
    col = _ratio_col(raw_df)
    latest = raw_df.groupby("stock_code")["report_date"].max().reset_index()
    m = raw_df.merge(latest, on=["stock_code", "report_date"])
    rows: list[dict[str, object]] = []
    for sc, sub in m.groupby("stock_code"):
        w = (sub[col].astype(float).fillna(0) / 100.0).clip(lower=0)
        rows.append({"stock_code": sc, "hhi_top10": float((w**2).sum())})
    return pd.DataFrame(rows)


def calc_top10_delta_pp(ratio_df: pd.DataFrame) -> pd.DataFrame:
    """
    基于 calc_top10_ratio 输出的 long 表：每只股票最近两期 top10 合计占比之差（百分点）。
    ratio_df 列：stock_code, report_date, top10_ratio
    """
    if ratio_df.empty:
        return pd.DataFrame(columns=["stock_code", "top10_delta_pp"])
    rows = []
    for sc, g in ratio_df.groupby("stock_code"):
        g = g.sort_values("report_date")
        if len(g) < 2:
            rows.append({"stock_code": sc, "top10_delta_pp": None})
        else:
            d = float(g["top10_ratio"].iloc[-1]) - float(g["top10_ratio"].iloc[-2])
            rows.append({"stock_code": sc, "top10_delta_pp": round(d, 3)})
    return pd.DataFrame(rows)


def chip_score_row(
    top10_ratio: float,
    hhi_top10: float,
    top10_delta_pp: Optional[float],
    institution_count_current: float = 0,
) -> float:
    """
    启发式 0–100：集中度、HHI、环比改善、机构家数（轻度加成）。
    """
    d = top10_delta_pp if top10_delta_pp is not None and not pd.isna(top10_delta_pp) else 0.0
    inst = float(institution_count_current or 0)
    s = (
        min(38.0, max(0.0, float(top10_ratio)) * 0.34)
        + min(36.0, max(0.0, float(hhi_top10)) * 72.0)
        + min(16.0, max(0.0, d) * 1.1)
        + min(10.0, inst * 1.2)
    )
    return round(float(min(100.0, max(0.0, s))), 2)


def enrich_candidates_chip(
    raw_df: pd.DataFrame,
    ratio_df: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    """为候选池追加 hhi_top10、top10_delta_pp、chip_score；非候选不带入。"""
    if candidates.empty:
        return candidates
    hhi = calc_hhi_latest(raw_df)
    dlt = calc_top10_delta_pp(ratio_df)
    cand = candidates.copy()
    cand["stock_code"] = cand["stock_code"].astype(str)
    hhi["stock_code"] = hhi["stock_code"].astype(str)
    dlt["stock_code"] = dlt["stock_code"].astype(str)
    out = cand.merge(hhi, on="stock_code", how="left").merge(dlt, on="stock_code", how="left")
    out["hhi_top10"] = out["hhi_top10"].fillna(np.nan)
    scores = []
    for _, r in out.iterrows():
        scores.append(
            chip_score_row(
                float(r.get("top10_ratio_latest", 0) or 0),
                float(r["hhi_top10"]) if pd.notna(r.get("hhi_top10")) else 0.0,
                float(r["top10_delta_pp"]) if pd.notna(r.get("top10_delta_pp")) else None,
                float(r.get("institution_count_current", 0) or 0),
            )
        )
    out["chip_score"] = scores
    return out


def chip_metrics_for_one(
    raw_df: pd.DataFrame,
    ratio_df: pd.DataFrame,
    stock_code: str,
    top10_ratio_latest: float = 0,
    institution_count_current: float = 0,
) -> dict[str, object]:
    """单标的筹码指标（供 /anti-quant-stock 扩展字段）。"""
    sc = "".join(c for c in str(stock_code) if c.isdigit())[:6].zfill(6)
    c6 = raw_df["stock_code"].astype(str).str.replace(r"\.(SZ|SH|BJ)$", "", regex=True).str.slice(0, 6)
    r0 = raw_df[c6 == sc]
    hhi_df = calc_hhi_latest(r0) if not r0.empty else pd.DataFrame()
    hhi = float(hhi_df["hhi_top10"].iloc[0]) if not hhi_df.empty else None
    rd = ratio_df[ratio_df["stock_code"].astype(str).str.replace(r"\.(SZ|SH|BJ)$", "", regex=True).str.slice(0, 6) == sc]
    dlt_df = calc_top10_delta_pp(rd) if not rd.empty else pd.DataFrame()
    dlt = float(dlt_df["top10_delta_pp"].iloc[0]) if not dlt_df.empty and pd.notna(dlt_df["top10_delta_pp"].iloc[0]) else None
    score = chip_score_row(
        float(top10_ratio_latest),
        hhi if hhi is not None else 0.0,
        dlt,
        float(institution_count_current or 0),
    )
    return {
        "hhi_top10": round(hhi, 4) if hhi is not None else None,
        "top10_delta_pp": dlt,
        "chip_score": score,
    }
