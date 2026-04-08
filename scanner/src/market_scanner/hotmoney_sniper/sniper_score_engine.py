"""
游资狙击评分：题材 30% + 资金异动 30% + 量能结构 20% + 涨停行为 20% → Sniper Score。
输出 sniper_candidates（score > 0.7）。
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime


class SniperScoreEngine:
    def __init__(self, conn=None):
        self._conn = conn
        self._theme_weight = 0.3
        self._fund_weight = 0.3
        self._volume_weight = 0.2
        self._limit_weight = 0.2

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        from lib.database import get_connection, ensure_core_tables

        c = get_connection(read_only=False)
        if c:
            ensure_core_tables(c)
        return c

    def calculate_score(
        self,
        theme_score: float,
        fund_score: float,
        volume_score: float,
        limit_score: float,
    ) -> float:
        return (
            theme_score * self._theme_weight
            + fund_score * self._fund_weight
            + volume_score * self._volume_weight
            + limit_score * self._limit_weight
        )

    def run(
        self,
        min_score: float = 0.7,
        top_n: int = 50,
    ) -> pd.DataFrame:
        """
        汇总 theme/fund/volume/limitup 信号，对每只涨停标的打分，筛选 score >= min_score。
        返回 DataFrame: code, theme, sniper_score, confidence.
        """
        from .theme_detector import ThemeDetector
        from .fund_spike_detector import FundSpikeDetector
        from .volume_pattern_detector import VolumePatternDetector
        from .limitup_behavior_detector import LimitUpBehaviorDetector

        conn = self._get_conn()
        if not conn:
            return pd.DataFrame(columns=["code", "theme", "sniper_score", "confidence"])
        themes = ThemeDetector(conn).detect_hot_themes()
        spikes = FundSpikeDetector(conn).detect_spikes(volume_ratio_min=2.0)
        pattern = VolumePatternDetector(conn).detect_pattern(ratio_min=1.8)
        limit_df = LimitUpBehaviorDetector(conn).detect_limit_behavior()

        if limit_df is None or limit_df.empty:
            return pd.DataFrame(columns=["code", "theme", "sniper_score", "confidence"])

        # 取最近交易日（用于 spike/pattern 过滤）
        try:
            latest_date = conn.execute("SELECT MAX(date) FROM a_stock_daily").fetchone()[0]
        except Exception:
            latest_date = None

        # 板块排名 → theme_score 0~1（rank 1 最好）
        sector_rank = {}
        if themes is not None and not themes.empty:
            for _, r in themes.iterrows():
                sector_rank[str(r["sector"])] = 1.0 / (1 + int(r.get("rank", 99)))

        # 涨停标的列表
        codes = limit_df["code"].astype(str).unique().tolist()
        # 涨停所在板块（从 basic 取）
        code_sector = {}
        try:
            for c in codes:
                row = conn.execute(
                    "SELECT sector FROM a_stock_basic WHERE code = ?", [c]
                ).fetchone()
                code_sector[c] = str(row[0]) if row and row[0] else "未分类"
        except Exception:
            for c in codes:
                code_sector[c] = "未分类"

        spike_set = set()
        if latest_date and spikes is not None and not spikes.empty:
            recent = spikes[spikes["date"].astype(str) == str(latest_date)]
            spike_set = set(recent["code"].astype(str).tolist())

        pattern_set = set()
        if latest_date and pattern is not None and not pattern.empty:
            recent = pattern[pattern["date"].astype(str) == str(latest_date)]
            pattern_set = set(recent["code"].astype(str).tolist())

        results = []
        for _, row in limit_df.iterrows():
            code = str(row.get("code", ""))
            if not code:
                continue
            theme = code_sector.get(code, "未分类")
            theme_score = min(1.0, sector_rank.get(theme, 0.3) * 3)  # 0~1
            fund_score = 0.9 if code in spike_set else 0.3
            volume_score = 0.9 if code in pattern_set else 0.3
            # 连板数 1->0.5, 2->0.7, 3+->0.95
            lt = int(row.get("limit_up_times", 1) or 1)
            limit_score = min(0.95, 0.4 + lt * 0.2)

            score = self.calculate_score(theme_score, fund_score, volume_score, limit_score)
            confidence = min(0.99, score)
            results.append(
                {"code": code, "theme": theme, "sniper_score": score, "confidence": confidence}
            )

        df = pd.DataFrame(results)
        if df.empty:
            return pd.DataFrame(columns=["code", "theme", "sniper_score", "confidence"])
        df = (
            df[df["sniper_score"] >= min_score]
            .sort_values("sniper_score", ascending=False)
            .head(top_n)
        )
        return df.reset_index(drop=True)


def run_sniper(min_score: float = 0.7, top_n: int = 50) -> int:
    """运行狙击引擎并写入 sniper_candidates 表，返回写入条数。"""
    engine = SniperScoreEngine()
    df = engine.run(min_score=min_score, top_n=top_n)
    if df is None or df.empty:
        return 0
    conn = engine._get_conn()
    if not conn:
        return 0
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables

        ensure_tables(conn)
    except Exception:
        pass
    conn.execute("DELETE FROM sniper_candidates")
    conn.register("tmp", df)
    conn.execute("""
        INSERT INTO sniper_candidates (code, theme, sniper_score, confidence)
        SELECT code, theme, sniper_score, confidence FROM tmp
    """)
    n = len(df)
    return n
