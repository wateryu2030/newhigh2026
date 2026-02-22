# -*- coding: utf-8 -*-
"""
策略执行器：安全执行 AI 生成的策略代码，在给定 DataFrame 上运行并返回带 signal/equity 的结果。
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional


def _default_equity_from_signals(df: pd.DataFrame, signal_col: str = "signal") -> pd.Series:
    """根据 signal 列（1/-1/0）计算简单净值曲线（不考虑仓位大小，仅方向）。"""
    s = df[signal_col].fillna(0)
    # 收益：持有则用收盘价变化
    ret = df["close"].pct_change().fillna(0)
    # 仅在有信号时参与：买入持有到卖出
    pos = 0.0
    equity = [1.0]
    for i in range(1, len(df)):
        if s.iloc[i] == 1:
            pos = 1.0
        elif s.iloc[i] == -1:
            pos = 0.0
        equity.append(equity[-1] * (1 + pos * ret.iloc[i]))
    return pd.Series(equity, index=df.index)


class StrategyRunner:
    """执行策略代码字符串，在 df 上运行并返回带 equity 的 DataFrame。"""

    def run(
        self,
        code: str,
        df: pd.DataFrame,
        entry_point: str = "strategy",
    ) -> Dict[str, Any]:
        """
        执行策略代码，返回包含 equity 和 metrics 的结果。
        :param code: 策略 Python 代码字符串，需定义 strategy(df) -> DataFrame
        :param df: 至少含 open, high, low, close, volume 的 K 线
        :param entry_point: 函数名，默认 strategy
        :return: {"df": DataFrame, "equity": Series, "error": Optional[str]}
        """
        if df is None or len(df) < 2:
            return {"df": df, "equity": None, "error": "数据不足"}
        df = df.copy()
        if "date" not in df.columns and df.index.dtype in ("datetime64[ns]", "object", "str"):
            df["date"] = df.index.astype(str).str[:10] if hasattr(df.index, "str") else str(df.index[0])
        local_vars: Dict[str, Any] = {}
        try:
            exec(code, {"pd": pd, "np": np}, local_vars)
        except Exception as e:
            return {"df": df, "equity": None, "error": f"编译/执行异常: {e}"}
        func = local_vars.get(entry_point)
        if func is None:
            return {"df": df, "equity": None, "error": f"未找到函数 {entry_point}"}
        try:
            result = func(df)
        except Exception as e:
            return {"df": df, "equity": None, "error": f"策略运行异常: {e}"}
        if result is None or not isinstance(result, pd.DataFrame):
            return {"df": df, "equity": None, "error": "策略未返回 DataFrame"}
        out = result
        # 统一 equity
        if "equity" in out.columns:
            equity = out["equity"]
        elif "signal" in out.columns:
            equity = _default_equity_from_signals(out, "signal")
        elif "buy" in out.columns and "sell" in out.columns:
            out["signal"] = 0
            out.loc[out["buy"].fillna(False), "signal"] = 1
            out.loc[out["sell"].fillna(False), "signal"] = -1
            equity = _default_equity_from_signals(out, "signal")
        else:
            equity = pd.Series(1.0, index=out.index)
        out = out.copy()
        out["equity"] = equity
        return {"df": out, "equity": equity, "error": None}
