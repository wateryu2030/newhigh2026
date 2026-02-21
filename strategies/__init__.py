# 策略模块：含 RQAlpha 脚本与插件策略
from .base import BaseStrategy
from .ma_cross import MACrossStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from .kdj_strategy import KDJStrategy
from .breakout import BreakoutStrategy

# 插件策略注册表：strategy_id -> StrategyClass
PLUGIN_STRATEGIES = {
    "ma_cross": MACrossStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "kdj": KDJStrategy,
    "breakout": BreakoutStrategy,
}


def get_plugin_strategy(strategy_id: str, **kwargs):
    """根据 id 获取策略实例，可选传入策略参数（用于参数优化）。"""
    cls = PLUGIN_STRATEGIES.get(strategy_id)
    if cls is None:
        return None
    return cls(**kwargs) if kwargs else cls()
