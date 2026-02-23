# -*- coding: utf-8 -*-
"""
形态识别引擎：统一调用趋势/反转/量价形态，输出综合形态信号与类型。
"""
from __future__ import annotations
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

from . import trend_patterns as tp
from . import reversal_patterns as rp
from . import volume_patterns as vp


class PatternEngine:
    """
    技术形态识别引擎。
    输出：每根 K 线对应的形态标签列表 + 综合强度。
    """

    def __init__(
        self,
        trend_window: int = 20,
        reversal_lookback: int = 10,
        volume_ma_window: int = 5,
    ):
        self.trend_window = trend_window
        self.reversal_lookback = reversal_lookback
        self.volume_ma_window = volume_ma_window

    def run(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        在 OHLCV DataFrame 上运行所有形态检测，返回带 pattern 列的 DataFrame。
        新增列：pattern_trend, pattern_reversal, pattern_volume, pattern_score, pattern_tags
        """
        if df is None or len(df) < 20:
            return df
        out = df.copy()
        # 趋势类
        bull, bull_strength = tp.detect_multi_ma_bull(out, 5, 20, 60)
        breakout = tp.detect_breakout_platform(out, self.trend_window)
        new_high = tp.detect_new_high_breakout(out, 60)
        out["_trend_bull"] = bull.astype(int)
        out["_trend_breakout"] = breakout.astype(int)
        out["_trend_newhigh"] = new_high.astype(int)
        # 反转类
        v_rev = rp.detect_v_reversal(out, self.reversal_lookback)
        oversold = rp.detect_oversold_bounce(out, 14, 30)
        out["_rev_v"] = v_rev.astype(int)
        out["_rev_oversold"] = oversold.astype(int)
        # 量价类
        vol_break = vp.detect_volume_breakout(out, self.trend_window, self.volume_ma_window)
        vol_pull = vp.detect_volume_pullback(out, 5, 20)
        out["_vol_break"] = vol_break.astype(int)
        out["_vol_pull"] = vol_pull.astype(int)

        # 综合得分：形态触发数量与强度
        trend_score = out["_trend_bull"] + out["_trend_breakout"] + out["_trend_newhigh"]
        rev_score = out["_rev_v"] + out["_rev_oversold"]
        vol_score = out["_vol_break"] + out["_vol_pull"]
        out["pattern_trend"] = trend_score
        out["pattern_reversal"] = rev_score
        out["pattern_volume"] = vol_score
        out["pattern_score"] = (trend_score + rev_score + vol_score).clip(0, 10)

        # 标签（最后一根用于展示）
        def _tags(row: pd.Series) -> str:
            tags = []
            if row.get("_trend_bull", 0) == 1:
                tags.append("多头排列")
            if row.get("_trend_breakout", 0) == 1:
                tags.append("突破平台")
            if row.get("_trend_newhigh", 0) == 1:
                tags.append("新高突破")
            if row.get("_rev_v", 0) == 1:
                tags.append("V反")
            if row.get("_rev_oversold", 0) == 1:
                tags.append("超跌反弹")
            if row.get("_vol_break", 0) == 1:
                tags.append("放量突破")
            if row.get("_vol_pull", 0) == 1:
                tags.append("缩量回踩")
            return ",".join(tags) if tags else ""

        out["pattern_tags"] = out.apply(_tags, axis=1)
        return out

    def get_latest_patterns(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        取最新一根 K 线的形态结果，供扫描器/API 使用。
        """
        run_df = self.run(df)
        if run_df is None or len(run_df) == 0:
            return {"score": 0, "tags": [], "trend": 0, "reversal": 0, "volume": 0}
        last = run_df.iloc[-1]
        tags_str = last.get("pattern_tags", "") or ""
        def _int(v, default=0):
            try:
                x = int(v)
                return x if x == x else default  # NaN check
            except (TypeError, ValueError):
                return default

        return {
            "score": _int(last.get("pattern_score"), 0),
            "tags": [t.strip() for t in tags_str.split(",") if t.strip()],
            "trend": _int(last.get("pattern_trend"), 0),
            "reversal": _int(last.get("pattern_reversal"), 0),
            "volume": _int(last.get("pattern_volume"), 0),
        }
