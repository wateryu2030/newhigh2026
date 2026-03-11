"""Connect pipeline: wire data_update, feature_generation, ... to engines."""
import logging
from typing import Callable, Optional

from .task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)


def connect_pipeline(
    scheduler: Optional[TaskScheduler] = None,
    data_engine_run_pipeline: Optional[Callable[[], None]] = None,
    feature_engine_build: Optional[Callable[[], None]] = None,
    strategy_engine_run: Optional[Callable[[], None]] = None,
    backtest_engine_run: Optional[Callable[[], None]] = None,
    risk_engine_check: Optional[Callable[[], None]] = None,
    execution_engine_deploy: Optional[Callable[[], None]] = None,
) -> TaskScheduler:
    """
    Wire pipeline steps to callable stubs or real engine functions.
    Each *_run/build/check/deploy is a callable() that runs that step.
    Returns the scheduler with steps registered.
    """
    from .task_scheduler import TaskScheduler, get_default_scheduler
    s = scheduler or get_default_scheduler()

    def data_update() -> None:
        if data_engine_run_pipeline:
            data_engine_run_pipeline()
        else:
            logger.info("data_update (no impl)")

    def feature_generation() -> None:
        if feature_engine_build:
            feature_engine_build()
        else:
            logger.info("feature_generation (no impl)")

    def strategy_generation() -> None:
        if strategy_engine_run:
            strategy_engine_run()
        else:
            logger.info("strategy_generation (no impl)")

    def backtest() -> None:
        if backtest_engine_run:
            backtest_engine_run()
        else:
            logger.info("backtest (no impl)")

    def risk_filter() -> None:
        if risk_engine_check:
            risk_engine_check()
        else:
            logger.info("risk_filter (no impl)")

    def deploy() -> None:
        if execution_engine_deploy:
            execution_engine_deploy()
        else:
            logger.info("deploy (no impl)")

    s.register("data_update", data_update)
    s.register("feature_generation", feature_generation)
    s.register("strategy_generation", strategy_generation)
    s.register("backtest", backtest)
    s.register("risk_filter", risk_filter)
    s.register("deploy", deploy)

    # Evolution stage (OPENCLAW_EVOLUTION): self-improvement loop
    def generate_strategies() -> None:
        try:
            from alpha_factory import generate_population
            pop = generate_population(100)
            logger.info("generate_strategies: %d candidates", len(pop))
        except ImportError:
            logger.info("generate_strategies (alpha_factory not installed)")

    def backtest_strategies() -> None:
        logger.info("backtest_strategies (wire to backtest_engine)")

    def score_alpha() -> None:
        try:
            from alpha_scoring import alpha_score
            logger.info("score_alpha (alpha_scoring ready)")
        except ImportError:
            logger.info("score_alpha (alpha_scoring not installed)")

    def evolve_population() -> None:
        try:
            from strategy_evolution import evolve_population
            logger.info("evolve_population (strategy_evolution ready)")
        except ImportError:
            logger.info("evolve_population (strategy_evolution not installed)")

    def deploy_top_strategies() -> None:
        try:
            from meta_fund_manager import select_strategies
            logger.info("deploy_top_strategies (meta_fund_manager ready)")
        except ImportError:
            logger.info("deploy_top_strategies (meta_fund_manager not installed)")

    s.register("generate_strategies", generate_strategies)
    s.register("backtest_strategies", backtest_strategies)
    s.register("score_alpha", score_alpha)
    s.register("evolve_population", evolve_population)
    s.register("deploy_top_strategies", deploy_top_strategies)
    return s
