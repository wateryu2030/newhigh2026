"""
执行引擎主 Runner：信号 → 风控检查 → 下单执行。
作为执行层统一入口，供 system_runner 或外部调度调用。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """执行引擎配置。"""

    buy_threshold: float = 0.7
    sell_threshold: float = 0.3
    lot_size: int = 100
    max_buys: int = 10
    max_sells: int = 10
    dry_run: bool = True
    enable_risk_check: bool = True
    initial_cash: float = 1_000_000.0


@dataclass
class ExecutionResult:
    """单次执行结果。"""

    ok: bool
    dry_run: bool
    orders_placed: int = 0
    buys: int = 0
    sells: int = 0
    cash: float = 0.0
    equity: float = 0.0
    total_assets: float = 0.0
    risk_blocked: bool = False
    risk_violations: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


class ExecutionRunner:
    """
    执行引擎运行器。

    典型用法::

        runner = ExecutionRunner(ExecutionConfig(dry_run=False))
        result = runner.step()
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()

    def step(self) -> ExecutionResult:
        """
        执行一轮：读取信号 → 风控评估 → 下单。
        返回 ExecutionResult 统计本步结果。
        """
        cfg = self.config
        result = ExecutionResult(ok=True, dry_run=cfg.dry_run)

        # --- 1. 风控检查 ---
        if cfg.enable_risk_check:
            risk_ok, violations = self._risk_check()
            if not risk_ok:
                result.ok = False
                result.risk_blocked = True
                result.risk_violations = violations
                _log.warning("Risk check blocked execution: %s", violations)
                return result

        # --- 2. 获取买卖信号 ---
        try:
            from execution_engine.signal_executor import get_actionable_signals

            buys, sells = get_actionable_signals(
                buy_threshold=cfg.buy_threshold,
                sell_threshold=cfg.sell_threshold,
                limit=max(cfg.max_buys, cfg.max_sells),
            )
        except Exception as e:
            _log.exception("Failed to get actionable signals")
            result.ok = False
            result.errors.append(f"signal error: {e}")
            return result

        # --- 3. 执行订单 ---
        if cfg.dry_run:
            # dry_run 模式：通过 simulated engine step 推进模拟盘
            try:
                from execution_engine.simulated.engine import step_simulated

                sim_result = step_simulated(
                    buy_threshold=cfg.buy_threshold,
                    sell_threshold=cfg.sell_threshold,
                    initial_cash=cfg.initial_cash,
                    lot_size=cfg.lot_size,
                    max_buys=cfg.max_buys,
                    max_sells=cfg.max_sells,
                    risk_check=False,  # 已在上面做过检查
                )
                result.orders_placed = sim_result.get("orders_created", 0)
                result.cash = sim_result.get("cash", 0)
                result.equity = sim_result.get("equity", 0)
                result.total_assets = sim_result.get("total_assets", 0)
                result.buys = min(len(buys), cfg.max_buys)
                result.sells = min(len(sells), cfg.max_sells)
                _log.info(
                    "Execution step: %d orders, cash=%.2f equity=%.2f total=%.2f",
                    result.orders_placed,
                    result.cash,
                    result.equity,
                    result.total_assets,
                )
            except Exception as e:
                _log.exception("Simulated engine step failed")
                result.ok = False
                result.errors.append(f"simulated engine error: {e}")
        else:
            # 真实下单：通过 signal_executor 逐个执行
            try:
                from execution_engine.signal_executor import execute_buy, execute_sell

                for b in buys[: cfg.max_buys]:
                    r = execute_buy(
                        b["code"],
                        quantity=cfg.lot_size,
                        confidence=b.get("confidence", 0),
                        dry_run=False,
                    )
                    if r["ok"]:
                        result.buys += 1
                        result.orders_placed += 1
                    else:
                        result.errors.append(f"BUY {b['code']} failed: {r.get('message')}")

                for s in sells[: cfg.max_sells]:
                    r = execute_sell(
                        s["code"],
                        quantity=cfg.lot_size,
                        confidence=s.get("confidence", 0),
                        dry_run=False,
                    )
                    if r["ok"]:
                        result.sells += 1
                        result.orders_placed += 1
                    else:
                        result.errors.append(f"SELL {s['code']} failed: {r.get('message')}")

                _log.info(
                    "Live execution: %d buys, %d sells, %d errors",
                    result.buys,
                    result.sells,
                    len(result.errors),
                )
            except Exception as e:
                _log.exception("Live execution failed")
                result.ok = False
                result.errors.append(f"live execution error: {e}")

        return result

    def _risk_check(self) -> tuple[bool, List[Dict[str, Any]]]:
        """执行风控评估，返回 (通过, 违规列表)。"""
        try:
            import sys
            import os

            # 确保 risk_engine 可导入
            _root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
            for _d in ["risk-engine/src", "data-pipeline/src"]:
                _p = os.path.join(_root, _d)
                if os.path.isdir(_p) and _p not in sys.path:
                    sys.path.insert(0, _p)

            from risk_engine.risk_monitor import evaluate_current

            res = evaluate_current()
            if res.get("pass", True):
                return True, []
            return False, res.get("violations", [])
        except Exception:
            _log.exception("Risk check failed, allowing execution (fail-open)")
            return True, []

    def get_status(self) -> Dict[str, Any]:
        """返回当前执行层状态快照。"""
        try:
            from execution_engine.simulated.engine import (
                get_positions,
                get_orders,
                get_account_snapshots,
            )

            positions = get_positions()
            orders = get_orders(limit=20)
            snapshots = get_account_snapshots(limit=1)
            latest = snapshots[0] if snapshots else {}
            return {
                "mode": "dry_run" if self.config.dry_run else "live",
                "positions_count": len(positions),
                "positions": positions[:10],
                "orders_count": len(orders),
                "recent_orders": orders[:5],
                "cash": latest.get("cash", 0),
                "equity": latest.get("equity", 0),
                "total_assets": latest.get("total_assets", 0),
            }
        except Exception:
            _log.exception("Failed to get execution status")
            return {"error": "status unavailable", "mode": "unknown"}


def run_execution_cycle(config: Optional[ExecutionConfig] = None) -> ExecutionResult:
    """快捷函数：一轮执行周期。"""
    runner = ExecutionRunner(config)
    return runner.step()
