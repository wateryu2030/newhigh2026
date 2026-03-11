"""
Risk Controller — 风险控制系统
集中执行风控规则：回撤/敞口/波动 → 暂停策略、减仓
"""
from typing import Callable, Dict, List, Optional


def check_drawdown_and_decide(
    strategy_id: str,
    current_drawdown: float,
    max_drawdown: float = 0.1,
) -> str:
    """
    回撤检查。返回: "ok" | "suspend" | "reduce"
    """
    if current_drawdown >= max_drawdown:
        return "suspend"
    if current_drawdown >= max_drawdown * 0.8:
        return "reduce"
    return "ok"


def check_exposure_and_decide(
    total_exposure: float,
    max_exposure: float,
) -> str:
    """敞口检查。返回: "ok" | "reduce" """
    if total_exposure > max_exposure:
        return "reduce"
    return "ok"


def check_volatility_and_decide(
    current_vol: float,
    max_vol: float = 0.5,
) -> str:
    """波动检查。返回: "ok" | "reduce" | "suspend" """
    if current_vol >= max_vol:
        return "suspend"
    if current_vol >= max_vol * 0.8:
        return "reduce"
    return "ok"


def apply_risk_rules(
    strategy_id: str,
    *,
    drawdown: Optional[float] = None,
    max_drawdown: float = 0.1,
    exposure: Optional[float] = None,
    max_exposure: Optional[float] = None,
    volatility: Optional[float] = None,
    max_volatility: float = 0.5,
) -> List[str]:
    """
    综合风控：返回应执行的动作列表，如 ["suspend"], ["reduce"], []。
    """
    actions = []
    if drawdown is not None:
        a = check_drawdown_and_decide(strategy_id, drawdown, max_drawdown)
        if a != "ok":
            actions.append(a)
    if exposure is not None and max_exposure is not None:
        if check_exposure_and_decide(exposure, max_exposure) == "reduce":
            actions.append("reduce")
    if volatility is not None:
        a = check_volatility_and_decide(volatility, max_volatility)
        if a != "ok":
            actions.append(a)
    return actions
