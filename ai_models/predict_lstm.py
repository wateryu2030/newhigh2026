# -*- coding: utf-8 -*-
"""
LSTM 预测脚本：加载已训练模型，对 (batch, seq_len, input_size) 输入预测未来 1 日收益率。
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

import torch
import numpy as np
from typing import Union, Optional  # noqa: F401
from ai_models.lstm_model import LSTMModel


def load_lstm(
    path: str,
    input_size: int = 10,
    hidden: int = 64,
    device: Optional[torch.device] = None,
) -> LSTMModel:
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMModel(input_size=input_size, hidden=hidden)
    state = torch.load(path, map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model


def predict(
    model: LSTMModel,
    X: Union[torch.Tensor, np.ndarray],
    device: Optional[torch.device] = None,
) -> np.ndarray:
    """
    :param model: 已加载的 LSTMModel
    :param X: (batch, seq_len, input_size)
    :return: (batch,) 未来 1 日收益率预测
    """
    device = device or next(model.parameters()).device
    if isinstance(X, np.ndarray):
        X = torch.from_numpy(X).float()
    X = X.to(device)
    with torch.no_grad():
        out = model(X)
    return out.cpu().numpy().ravel()


def predict_from_df(feature_matrix, seq_len: int = 30, model_path: Optional[str] = None):
    """
    从因子特征矩阵中取最近 seq_len 行构造输入，预测下一日收益。
    feature_matrix 需为数值型 DataFrame，无 date 列或 date 列会被排除。
    """
    import pandas as pd
    df = feature_matrix
    if hasattr(df, "columns"):
        cols = [c for c in df.columns if c != "date" and pd.api.types.is_numeric_dtype(df[c])]
        arr = df[cols].values
    else:
        arr = np.asarray(df)
    if len(arr) < seq_len:
        return None
    # 最后 seq_len 行 -> (1, seq_len, n_features)
    x = arr[-seq_len:].astype(np.float32)
    x = np.expand_dims(x, axis=0)
    path = model_path or os.path.join(os.path.dirname(__file__), "lstm.pth")
    if not os.path.isfile(path):
        return None
    model = load_lstm(path, input_size=x.shape[2])
    return predict(model, x)[0]
