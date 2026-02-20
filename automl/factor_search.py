# -*- coding: utf-8 -*-
"""
AutoML 因子搜索：用 Optuna 优化 RandomForest（或其它分类器）超参，最大化 CV 得分。
可接入因子矩阵 X 与未来收益二分类 y，自动寻找「哪些指标最赚钱」。
"""
import numpy as np
from typing import Optional, Callable, Any
import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score


def objective(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 3,
) -> float:
    n_estimators = trial.suggest_int("n_estimators", 50, 200)
    max_depth = trial.suggest_int("max_depth", 2, 10)
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=42,
    )
    score = cross_val_score(model, X, y, cv=cv, n_jobs=-1).mean()
    return score


def run_factor_search(
    X: np.ndarray,
    y: np.ndarray,
    n_trials: int = 50,
    cv: int = 3,
    direction: str = "maximize",
    objective_fn: Optional[Callable[..., float]] = None,
) -> optuna.Study:
    """
    在 (X, y) 上运行 Optuna 优化，默认优化 RandomForest 的 n_estimators、max_depth。
    :param X: 特征矩阵（因子）
    :param y: 二分类标签（如未来收益 >0 为 1）
    :param n_trials: 试验次数
    :param cv: 交叉验证折数
    :param direction: maximize 或 minimize
    :param objective_fn: 自定义 objective(trial, X, y, cv)；None 则用默认
    :return: optuna.Study，可读 best_params / best_value
    """
    if objective_fn is None:
        def obj(trial):
            return objective(trial, X, y, cv=cv)
    else:
        def obj(trial):
            return objective_fn(trial, X, y, cv=cv)
    study = optuna.create_study(direction=direction)
    study.optimize(obj, n_trials=n_trials, show_progress_bar=True)
    print("best_params:", study.best_params)
    print("best_value:", study.best_value)
    return study
