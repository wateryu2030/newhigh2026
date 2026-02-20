# -*- coding: utf-8 -*-
"""
投资组合引擎：多策略信号融合与组合收益曲线。
综合多个策略的 BUY/SELL/HOLD 得到组合信号，并计算组合净值。
"""
import os
import sys
from typing import List, Dict, Any, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


class PortfolioEngine:
    """
    多策略组合引擎：对同一 DataFrame 运行多个策略，融合信号并输出组合结果。
    """

    def __init__(self, strategies: List[Any], weights: Optional[List[float]] = None):
        """
        :param strategies: 策略实例列表（需实现 generate_signals(df)）
        :param weights: 各策略权重，长度需与 strategies 一致；None 表示等权
        """
        self.strategies = strategies
        n = len(strategies)
        if weights is None or len(weights) != n:
            self.weights = [1.0 / n] * n if n else []
        else:
            s = sum(weights)
            self.weights = [w / s for w in weights] if s else [1.0 / n] * n

    def combine_signal(self, signals: List[str]) -> str:
        """
        融合多策略信号：多数 BUY -> BUY，多数 SELL -> SELL，否则 HOLD。
        :param signals: ["BUY"|"SELL"|"HOLD", ...]
        """
        if not signals:
            return "HOLD"
        buy = sum(1 for s in signals if (s or "").upper() == "BUY")
        sell = sum(1 for s in signals if (s or "").upper() == "SELL")
        if buy > sell:
            return "BUY"
        if sell > buy:
            return "SELL"
        return "HOLD"

    def run(
        self,
        df: Any,
    ) -> Dict[str, Any]:
        """
        在整段行情上运行多策略，按日融合信号并计算组合净值。
        :param df: 行情 DataFrame，需含 date, open, high, low, close
        :return: { "signals": [{ date, signal, weights_per_strategy }], "equity": [{ date, value }], "stats": {} }
        """
        if df is None or len(df) < 2:
            return {"signals": [], "equity": [], "stats": {}}

        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]

        dates = df["date"].astype(str).str[:10].tolist()
        closes = df["close"].tolist()
        # 各策略在每日的持仓建议：1=多 -1=空 0=空仓，由最近一次信号决定
        positions = []  # list of list: positions[i] = [strategy0_pos, strategy1_pos, ...]
        for _ in dates:
            positions.append([0] * len(self.strategies))

        for si, strategy in enumerate(self.strategies):
            try:
                sig_list = strategy.generate_signals(df)
            except Exception:
                continue
            # 用信号更新该策略的持仓序列
            sig_by_date = {str(s["date"])[:10]: s.get("type", "HOLD") for s in sig_list}
            pos = 0
            for i, d in enumerate(dates):
                s = (sig_by_date.get(d) or "HOLD").upper()
                if s == "BUY":
                    pos = 1
                elif s == "SELL":
                    pos = -1
                positions[i][si] = pos

        # 组合信号：按权重加权平均仓位，>0.5 视为多，<-0.5 视为空
        combined_signals = []
        equity = 1.0
        equity_curve = []
        for i, d in enumerate(dates):
            w_pos = sum(self.weights[j] * (1 if positions[i][j] == 1 else (-1 if positions[i][j] == -1 else 0)) for j in range(len(self.strategies)))
            if w_pos > 0.3:
                comb = "BUY"
            elif w_pos < -0.3:
                comb = "SELL"
            else:
                comb = "HOLD"
            combined_signals.append({"date": d, "signal": comb, "weights_per_strategy": positions[i][:]})
            # 简单净值：组合仓位 * 日收益率
            if i > 0 and closes[i - 1] and closes[i - 1] != 0:
                ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                pos_comb = 1 if comb == "BUY" else (-1 if comb == "SELL" else 0)
                equity *= 1 + pos_comb * ret
            equity_curve.append({"date": d, "value": round(equity, 6)})

        # 简单统计
        final = equity_curve[-1]["value"] if equity_curve else 1.0
        total_return = final - 1.0
        peak = 1.0
        max_dd = 0.0
        for p in equity_curve:
            v = p["value"]
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak
                if dd > max_dd:
                    max_dd = dd

        return {
            "signals": combined_signals,
            "equity": equity_curve,
            "stats": {
                "total_return": total_return,
                "max_drawdown": max_dd,
                "final_equity": final,
            },
        }

    def run_portfolio(
        self,
        strategies: List[Any],
        df: Any,
        weights: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        类方法式入口：用给定 strategies/weights 构建引擎并 run。
        """
        engine = PortfolioEngine(strategies, weights)
        return engine.run(df)
