# -*- coding: utf-8 -*-
"""
模型修正闭环：训练 → 预测未来 → 新数据到来 → 评估预测与实际 → 修正/再训练 → 循环。

流程：
1. 用历史数据 3/4 训练模型，后 1/4 作为「未来」不做训练
2. 用训练好的模型对后 1/4 做预测（推测未来）
3. 当新数据进来后，后 1/4 的「实际」已知，对比预测与实际，得到误差指标
4. 根据指标决定是否修正（如重训、调参），并将新数据纳入历史，进入下一轮
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from .dataset_builder import build_dataset, get_feature_columns
from .feature_engineering import build_features_multi
from .model_manager import ModelManager
from .model_trainer import ModelTrainer
from .model_predictor import ModelPredictor, DEFAULT_MODEL_PATH as PREDICTOR_MODEL_PATH


# 预测记录存储路径
DEFAULT_PREDICTION_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "prediction_log.csv"
)
DEFAULT_CORRECTION_METRICS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "correction_metrics.json"
)


def split_feature_df_by_time(
    feature_df: pd.DataFrame,
    train_ratio: float = 0.75,
    date_col: str = "date",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    按时间顺序划分：前 train_ratio 用于训练，后 (1-train_ratio) 用于前向验证（模拟未来）。
    严禁打乱顺序，避免未来数据泄露。
    """
    if feature_df is None or len(feature_df) < 20:
        return feature_df, pd.DataFrame()
    out = feature_df.copy()
    if date_col not in out.columns and hasattr(out.index, "str"):
        out[date_col] = out.index.astype(str).str[:10]
    out = out.sort_values(date_col).reset_index(drop=True)
    n = len(out)
    t = int(n * train_ratio)
    train_df = out.iloc[:t]
    forward_df = out.iloc[t:]
    return train_df, forward_df


def train_on_temporal(
    manager: ModelManager,
    market_data: Dict[str, pd.DataFrame],
    train_ratio: float = 0.75,
    label_forward_days: int = 5,
    use_binary: bool = True,
    binary_threshold: float = 0.0,
) -> Dict[str, Any]:
    """
    仅用时间序列前 train_ratio 的数据训练模型，后 1-train_ratio 留作前向验证。
    """
    from .dataset_builder import build_dataset_from_market_data
    feature_df = build_features_multi(market_data, label_forward_days=label_forward_days)
    if feature_df.empty or len(feature_df) < 50:
        return {"ok": False, "reason": "insufficient data", "metrics": {}}

    train_df, forward_df = split_feature_df_by_time(feature_df, train_ratio=train_ratio)
    if len(train_df) < 30:
        return {"ok": False, "reason": "train set too small", "metrics": {}}

    cols = manager.feature_cols or get_feature_columns()
    available = [c for c in cols if c in train_df.columns]
    if not available:
        return {"ok": False, "reason": "no feature columns", "metrics": {}}

    X_train, y_train = build_dataset(
        train_df,
        feature_cols=available,
        use_binary_label=use_binary,
        binary_label_threshold=binary_threshold,
    )
    if X_train.size == 0 or y_train.size == 0:
        return {"ok": False, "reason": "empty train", "metrics": {}}

    from .model_trainer import ModelTrainer, DEFAULT_MODEL_PATH as TRAINER_MODEL_PATH
    trainer = ModelTrainer(
        model_path=manager.model_path or TRAINER_MODEL_PATH,
        feature_cols=available,
        use_binary=use_binary,
        binary_threshold=binary_threshold,
    )
    trainer.train(X_train, y_train, eval_set=None)
    path = trainer.save_model()
    manager._trainer = trainer
    manager._predictor = None

    return {
        "ok": True,
        "model_path": path,
        "n_train": len(train_df),
        "n_forward": len(forward_df),
        "train_date_range": (str(train_df["date"].min()), str(train_df["date"].max())) if "date" in train_df.columns else (None, None),
        "forward_date_range": (str(forward_df["date"].min()), str(forward_df["date"].max())) if "date" in forward_df.columns and len(forward_df) else (None, None),
    }


def predict_forward(
    manager: ModelManager,
    forward_df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
) -> np.ndarray:
    """对前向验证集（forward_df）做预测，返回与 forward_df 行数一致的分数数组。"""
    if forward_df is None or forward_df.empty:
        return np.array([])
    cols = feature_cols or manager.feature_cols or get_feature_columns()
    available = [c for c in cols if c in forward_df.columns]
    if not available:
        return np.array([])
    X = forward_df[available].replace([np.inf, -np.inf], np.nan).fillna(0).values.astype(np.float64)
    pred = ModelPredictor(manager.model_path or PREDICTOR_MODEL_PATH)
    try:
        pred.load_model()
    except FileNotFoundError:
        return np.array([])
    scores = pred.predict_proba(X)
    return np.clip(np.asarray(scores).ravel(), 0.0, 1.0)


def evaluate_forward(forward_df: pd.DataFrame, pred_scores: np.ndarray) -> Dict[str, float]:
    """前向验证：对比预测分数与实际 label（未来收益），计算 IC、Rank IC、Top 组收益等。"""
    if forward_df is None or len(forward_df) < 10 or len(pred_scores) != len(forward_df):
        return {}
    if "label" not in forward_df.columns:
        return {}
    y = forward_df["label"].values.astype(np.float64)
    pred = np.asarray(pred_scores).ravel()[: len(y)]
    ic = float(np.corrcoef(pred, y)[0, 1]) if len(y) > 2 else 0.0
    if np.isnan(ic):
        ic = 0.0
    ic = max(-1.0, min(1.0, ic))
    rank_ic = 0.0
    if len(y) > 2:
        try:
            from scipy.stats import spearmanr
            rank_ic = float(spearmanr(pred, y).correlation)
        except Exception:
            rank_ic = 0.0
    if np.isnan(rank_ic):
        rank_ic = 0.0
    ret_top = 0.0
    if len(pred) >= 10:
        q = np.percentile(pred, 80)
        top = y[pred >= q]
        ret_top = float(np.mean(top)) if len(top) > 0 else 0.0
    return {"ic": ic, "rank_ic": rank_ic, "return_top20pct": ret_top}


def record_predictions(
    as_of_date: str,
    symbol: str,
    score: float,
    actual_ret: Optional[float] = None,
    log_path: Optional[str] = None,
) -> None:
    """追加一条预测记录；actual_ret 在新数据到位后可补填。"""
    path = log_path or DEFAULT_PREDICTION_LOG
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    row = {"as_of_date": as_of_date, "symbol": symbol, "score": score}
    if actual_ret is not None:
        row["actual_ret"] = actual_ret
    df = pd.DataFrame([row])
    if os.path.exists(path):
        try:
            existing = pd.read_csv(path)
            df = pd.concat([existing, df], ignore_index=True)
        except Exception:
            pass
    df.to_csv(path, index=False, encoding="utf-8-sig")


def record_forward_batch(
    forward_df: pd.DataFrame,
    pred_scores: np.ndarray,
    log_path: Optional[str] = None,
) -> None:
    """将前向验证期的预测与实际（label）批量写入 prediction_log。"""
    if forward_df is None or len(forward_df) == 0:
        return
    path = log_path or DEFAULT_PREDICTION_LOG
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if "date" in forward_df.columns:
        dates = forward_df["date"].astype(str).str[:10]
    else:
        dates = pd.Series(forward_df.index.astype(str).str[:10].values, index=forward_df.index)
    symbols = forward_df["symbol"] if "symbol" in forward_df.columns else [""] * len(forward_df)
    labels = forward_df["label"].values if "label" in forward_df.columns else [None] * len(forward_df)
    pred = np.asarray(pred_scores).ravel()[: len(forward_df)]
    rows = []
    for i in range(len(forward_df)):
        rows.append({
            "as_of_date": str(dates.iloc[i])[:10],
            "symbol": str(symbols.iloc[i]),
            "score": float(pred[i]),
            "actual_ret": float(labels[i]) if labels[i] is not None and not np.isnan(labels[i]) else None,
        })
    df = pd.DataFrame(rows)
    if os.path.exists(path):
        try:
            existing = pd.read_csv(path)
            df = pd.concat([existing, df], ignore_index=True)
        except Exception:
            pass
    df.to_csv(path, index=False, encoding="utf-8-sig")


def save_correction_metrics(metrics: Dict[str, Any], path: Optional[str] = None) -> None:
    """保存本轮修正评估指标与时间戳，便于追踪闭环效果。"""
    import json
    path = path or DEFAULT_CORRECTION_METRICS
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    out = {"updated_at": datetime.now().isoformat(), "metrics": metrics}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def run_cycle(
    market_data: Dict[str, pd.DataFrame],
    train_ratio: float = 0.75,
    label_forward_days: int = 5,
    model_path: Optional[str] = None,
    prediction_log_path: Optional[str] = None,
    metrics_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行一轮修正闭环：
    1. 按时间 3/4 训练、1/4 前向
    2. 对前向段预测并评估（预测 vs 实际）
    3. 记录预测与指标，供后续新数据再修正
    """
    if not market_data or len(market_data) < 5:
        return {"ok": False, "error": "market_data 不足", "metrics": {}}

    manager = ModelManager(model_path=model_path)
    # 1. 时序划分训练
    result = train_on_temporal(
        manager,
        market_data,
        train_ratio=train_ratio,
        label_forward_days=label_forward_days,
    )
    if not result.get("ok"):
        return {"ok": False, "error": result.get("reason", "train failed"), "metrics": {}}

    feature_df = build_features_multi(market_data, label_forward_days=label_forward_days)
    train_df, forward_df = split_feature_df_by_time(feature_df, train_ratio=train_ratio)
    if forward_df.empty:
        save_correction_metrics(result, metrics_path)
        return {"ok": True, "n_forward": 0, "metrics": {}, **result}

    # 2. 前向预测
    pred_scores = predict_forward(manager, forward_df)
    if len(pred_scores) != len(forward_df):
        save_correction_metrics(result, metrics_path)
        return {"ok": True, "n_forward": len(forward_df), "predict_failed": True, "metrics": {}, **result}

    # 3. 评估预测 vs 实际
    metrics = evaluate_forward(forward_df, pred_scores)
    record_forward_batch(forward_df, pred_scores, log_path=prediction_log_path)
    save_correction_metrics({**result, **metrics}, metrics_path)

    return {
        "ok": True,
        "n_train": result.get("n_train"),
        "n_forward": result.get("n_forward"),
        "train_date_range": result.get("train_date_range"),
        "forward_date_range": result.get("forward_date_range"),
        "model_path": result.get("model_path"),
        "metrics": metrics,
        **result,
    }


def run_cycle_with_data_loader(
    symbols: Optional[List[str]] = None,
    days: int = 500,
    train_ratio: float = 0.75,
    label_forward_days: int = 5,
    source: str = "database",
) -> Dict[str, Any]:
    """
    从数据源加载 K 线后执行一轮修正闭环；无 symbols 时从全 A 股取样本。
    新数据进来后再次调用本函数即可实现「新数据 → 再训练 → 再预测」的循环。
    """
    from datetime import datetime, timedelta
    from data.data_loader import load_kline
    import sys
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)

    if not symbols:
        try:
            from data.stock_pool import get_a_share_symbols
            symbols = get_a_share_symbols(exclude_delisted=True)
        except Exception:
            symbols = []
        if not symbols:
            try:
                from database.data_fetcher import get_all_a_share_symbols
                symbols = get_all_a_share_symbols()
            except Exception:
                symbols = []
        if not symbols:
            symbols = ["000001", "600519", "000858", "600036", "600745", "300750"]
        if len(symbols) > 500:
            symbols = symbols[:500]

    end = datetime.now().date()
    start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    market_data = {}
    for code in symbols:
        c = code.split(".")[0] if "." in code else code
        df = load_kline(c, start, end_str, source=source)
        if (df is None or len(df) < 60) and source == "database":
            df = load_kline(c, start, end_str, source="akshare")
        if df is not None and len(df) >= 60:
            key = c + ".XSHG" if c.startswith("6") else c + ".XSHE"
            market_data[key] = df

    return run_cycle(
        market_data,
        train_ratio=train_ratio,
        label_forward_days=label_forward_days,
    )
