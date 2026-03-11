"""Task scheduler: run pipeline steps on a schedule or trigger."""
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Simple in-process scheduler: register tasks and run them in order or by name.
    Pipeline: data_update -> feature_generation -> strategy_generation -> backtest -> risk_filter -> deploy.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Callable[[], None]] = {}
        self._order: List[str] = [
            "data_update",
            "feature_generation",
            "strategy_generation",
            "backtest",
            "risk_filter",
            "deploy",
        ]
        self._evolution_order: List[str] = [
            "generate_strategies",
            "backtest_strategies",
            "score_alpha",
            "evolve_population",
            "deploy_top_strategies",
        ]

    def register(self, name: str, fn: Callable[[], None]) -> None:
        self._tasks[name] = fn

    def run(self, name: str) -> bool:
        if name not in self._tasks:
            logger.warning("Unknown task: %s", name)
            return False
        try:
            self._tasks[name]()
            return True
        except Exception as e:
            logger.exception("Task %s failed: %s", name, e)
            return False

    def run_pipeline(self, from_step: Optional[str] = None, to_step: Optional[str] = None) -> List[str]:
        """
        Run pipeline in order. Optionally from_step/to_step (inclusive).
        Returns list of step names that completed successfully.
        """
        start = 0
        end = len(self._order)
        if from_step:
            try:
                start = self._order.index(from_step)
            except ValueError:
                pass
        if to_step:
            try:
                end = self._order.index(to_step) + 1
            except ValueError:
                pass
        ran = []
        for name in self._order[start:end]:
            if self.run(name):
                ran.append(name)
            else:
                break
        return ran

    def run_all(self) -> List[str]:
        """Run full pipeline in order."""
        return self.run_pipeline()

    def run_evolution_pipeline(self) -> List[str]:
        """Run evolution loop: generate_strategies -> backtest -> score_alpha -> evolve -> deploy."""
        ran = []
        for name in self._evolution_order:
            if name not in self._tasks:
                logger.warning("Evolution step not registered: %s", name)
                continue
            if self.run(name):
                ran.append(name)
            else:
                break
        return ran


def get_default_scheduler() -> TaskScheduler:
    """Return a scheduler with pipeline steps wired as no-ops (caller wires real impl)."""
    s = TaskScheduler()
    for step in s._order:
        s.register(step, (lambda x: lambda: logger.info("run %s (no-op)", x))(step))
    return s
