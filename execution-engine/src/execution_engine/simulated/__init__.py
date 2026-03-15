"""模拟盘引擎：消费 trade_signals，维护 sim_positions / sim_orders / sim_account_snapshots。"""

from .engine import (
    step_simulated,
    get_positions,
    get_orders,
    get_account_snapshots,
    DEFAULT_INITIAL_CASH,
    DEFAULT_LOT_SIZE,
)

__all__ = [
    "step_simulated",
    "get_positions",
    "get_orders",
    "get_account_snapshots",
    "DEFAULT_INITIAL_CASH",
    "DEFAULT_LOT_SIZE",
]
