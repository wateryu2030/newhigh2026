"""Optuna hyperparameter optimizer for strategies."""
from typing import Any, Callable, Dict, Optional

import optuna


def optimize(
    objective: Callable[[optuna.Trial], float],
    n_trials: int = 50,
    direction: str = "maximize",
    study_name: Optional[str] = None,
    storage: Optional[str] = None,
) -> optuna.Study:
    """
    Run Optuna study. objective(trial) returns metric to maximize/minimize.
    direction: maximize or minimize.
    """
    study = optuna.create_study(
        direction=direction,
        study_name=study_name or "strategy_opt",
        storage=storage,
        load_if_exists=True,
    )
    study.optimize(objective, n_trials=n_trials)
    return study


def suggest_strategy_params(trial: optuna.Trial, strategy_type: str) -> Dict[str, Any]:
    """
    Suggest strategy hyperparameters from trial.
    Use inside objective: params = suggest_strategy_params(trial, "trend_following"); ... run backtest ... return sharpe.
    """
    if strategy_type == "trend_following":
        return {
            "fast_period": trial.suggest_int("fast_period", 5, 30),
            "slow_period": trial.suggest_int("slow_period", 30, 100),
        }
    if strategy_type == "mean_reversion":
        return {
            "rsi_period": trial.suggest_int("rsi_period", 7, 21),
            "oversold": trial.suggest_float("oversold", 20, 40),
            "overbought": trial.suggest_float("overbought", 60, 80),
        }
    if strategy_type == "breakout":
        return {
            "lookback": trial.suggest_int("lookback", 10, 50),
        }
    return {}
