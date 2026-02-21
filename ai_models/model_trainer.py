# -*- coding: utf-8 -*-
"""
模型训练：XGBoost 选股模型（不可用时回退 sklearn.GradientBoosting），评估 AUC/IC/收益模拟，保存到 models/xgb_model.pkl。
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_DIR = os.path.join(_ROOT, "models")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "xgb_model.pkl")


def _ensure_libomp_path() -> None:
    """Mac 上若已用 brew install libomp，把 lib 路径加入运行时搜索，便于 XGBoost 加载 libomp.dylib。"""
    if os.name != "posix":
        return
    for prefix in ("/opt/homebrew/opt/libomp/lib", "/usr/local/opt/libomp/lib"):
        if os.path.isdir(prefix) and any(f.startswith("libomp") for f in os.listdir(prefix)):
            current = os.environ.get("DYLD_LIBRARY_PATH", "")
            if prefix not in current:
                os.environ["DYLD_LIBRARY_PATH"] = f"{prefix}:{current}" if current else prefix
            break


def _xgboost_available() -> bool:
    """XGBoost 是否可用（含 libomp 等运行时）。"""
    _ensure_libomp_path()
    try:
        import xgboost as xgb  # noqa: F401
        return True
    except Exception:
        return False


class ModelTrainer:
    """XGBoost 或 sklearn GradientBoosting 二分类选股模型训练与评估。"""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        feature_cols: Optional[List[str]] = None,
        use_binary: bool = True,
        binary_threshold: float = 0.0,
        **xgb_params: Any,
    ) -> None:
        self.model_path = model_path
        self.feature_cols = feature_cols
        self.use_binary = use_binary
        self.binary_threshold = binary_threshold
        self.xgb_params = xgb_params
        self._model: Any = None
        self._backend: str = "sklearn"  # "xgboost" | "sklearn"
        self._metrics: Dict[str, float] = {}

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    ) -> "ModelTrainer":
        """训练模型。优先 XGBoost；若不可用（如 Mac 缺 libomp）则用 sklearn.GradientBoostingClassifier。"""
        if _xgboost_available():
            self._train_xgb(X, y, eval_set)
        else:
            self._train_sklearn(X, y)
        return self

    def _train_xgb(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    ) -> None:
        import xgboost as xgb
        objective = "binary:logistic" if self.use_binary else "reg:squarederror"
        params = {
            "max_depth": 5,
            "eta": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "seed": 42,
            "nthread": 4,
            **self.xgb_params,
        }
        dtrain = xgb.DMatrix(X, label=y, feature_names=self.feature_cols)
        evals = [(dtrain, "train")]
        if eval_set is not None:
            Xe, ye = eval_set
            evals.append((xgb.DMatrix(Xe, label=ye, feature_names=self.feature_cols), "eval"))
        self._model = xgb.train(
            {**params, "objective": objective},
            dtrain,
            num_boost_round=200,
            evals=evals,
            verbose_eval=False,
        )
        self._backend = "xgboost"

    def _train_sklearn(self, X: np.ndarray, y: np.ndarray) -> None:
        try:
            from sklearn.ensemble import GradientBoostingClassifier
        except ImportError:
            raise ImportError("需要 scikit-learn：pip install scikit-learn（或安装 XGBoost+libomp：brew install libomp && pip install xgboost）")
        self._model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )
        self._model.fit(X, y)
        self._backend = "sklearn"

    def _predict_scores(self, X: np.ndarray) -> np.ndarray:
        """统一返回 (n,) 概率/分数 0~1。"""
        if self._backend == "xgboost":
            import xgboost as xgb
            d = xgb.DMatrix(X, feature_names=self.feature_cols)
            pred = self._model.predict(d)
        else:
            pred = self._model.predict_proba(X)[:, 1]
        return np.clip(np.asarray(pred).ravel(), 1e-6, 1 - 1e-6)

    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """
        评估：AUC、IC、简单收益模拟。
        """
        if self._model is None:
            return {}
        try:
            from sklearn.metrics import roc_auc_score
        except ImportError:
            self._metrics = {}
            return self._metrics

        pred = self._predict_scores(X)

        auc = 0.5
        if self.use_binary and len(np.unique(y)) >= 2:
            try:
                auc = float(roc_auc_score(y, pred))
            except ValueError:
                auc = 0.5
        ic = float(np.corrcoef(pred.ravel(), y.ravel())[0, 1]) if len(y) > 2 else 0.0
        if np.isnan(ic):
            ic = 0.0
        ic = max(-1.0, min(1.0, ic))

        ret_sim = 0.0
        if feature_df is not None and len(feature_df) == len(y) and "label" in feature_df.columns:
            df = feature_df.copy()
            df["pred"] = pred
            df["label"] = y
            df = df.dropna(subset=["pred", "label"])
            if len(df) >= 10:
                q = np.percentile(df["pred"], 80)
                top = df[df["pred"] >= q]
                ret_sim = float(top["label"].mean()) if len(top) > 0 else 0.0

        self._metrics = {"auc": auc, "ic": ic, "return_top20pct": ret_sim}
        return self._metrics

    def save_model(self, path: Optional[str] = None) -> str:
        path = path or self.model_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import pickle
        with open(path, "wb") as f:
            pickle.dump({
                "backend": self._backend,
                "model": self._model,
                "feature_cols": self.feature_cols,
                "use_binary": self.use_binary,
                "binary_threshold": self.binary_threshold,
            }, f)
        return path
