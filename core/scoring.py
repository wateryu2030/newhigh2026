# -*- coding: utf-8 -*-
"""
AI 策略评分系统：多维度加权综合评分，输出 0-100 分与评级。
"""
from typing import Dict, Any, Tuple, Optional


# 权重：收益率 30%，胜率 20%，最大回撤 20%，夏普 20%，交易次数 10%
WEIGHTS = {
    "return": 0.3,
    "winRate": 0.2,
    "maxDrawdown": 0.2,
    "sharpe": 0.2,
    "tradeCount": 0.1,
}


def _clip_score(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def score_strategy(stats: Dict[str, Any]) -> Tuple[float, str]:
    """
    根据回测统计计算策略综合评分与评级。

    :param stats: 至少含 return, winRate, maxDrawdown, tradeCount；sharpe 可选
    :return: (score 0-100, grade 字符串)
    """
    if not stats:
        return 0.0, "无数据"

    total_return = stats.get("return")
    if total_return is None:
        total_return = stats.get("total_returns", 0) or 0
    if isinstance(total_return, (int, float)) and total_return != total_return:
        total_return = 0

    win_rate = stats.get("winRate")
    if win_rate is None:
        win_rate = 0
    if isinstance(win_rate, (int, float)) and (win_rate != win_rate or win_rate < 0):
        win_rate = 0
    if isinstance(win_rate, float) and 0 <= win_rate <= 1:
        win_rate = win_rate * 100

    max_dd = stats.get("maxDrawdown")
    if max_dd is None:
        max_dd = 0
    if isinstance(max_dd, (int, float)) and (max_dd != max_dd or max_dd < 0):
        max_dd = 0
    if isinstance(max_dd, float) and max_dd > 1:
        max_dd = max_dd * 100

    sharpe = stats.get("sharpe")
    if sharpe is None:
        sharpe = 0
    if isinstance(sharpe, (int, float)) and sharpe != sharpe:
        sharpe = 0

    trades = stats.get("tradeCount") or 0
    if not isinstance(trades, (int, float)) or trades != trades:
        trades = 0
    trades = int(trades) if trades == trades else 0

    # 各子项 0-100 分
    return_score = _clip_score((float(total_return) * 100) if total_return is not None else 0)
    win_score = _clip_score(float(win_rate) if win_rate is not None else 0)
    dd_score = _clip_score(100 - float(max_dd) * 100 if max_dd is not None else 100)
    sharpe_score = _clip_score((float(sharpe) * 25) if sharpe is not None else 0)
    trade_score = _clip_score(min(float(trades) * 5, 100) if trades is not None else 0)

    score = (
        return_score * WEIGHTS["return"]
        + win_score * WEIGHTS["winRate"]
        + dd_score * WEIGHTS["maxDrawdown"]
        + sharpe_score * WEIGHTS["sharpe"]
        + trade_score * WEIGHTS["tradeCount"]
    )
    score = round(_clip_score(score), 2)

    if score >= 85:
        grade = "优秀"
    elif score >= 70:
        grade = "良好"
    elif score >= 55:
        grade = "一般"
    elif score >= 40:
        grade = "较弱"
    else:
        grade = "较差"

    return score, grade
