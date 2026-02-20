# -*- coding: utf-8 -*-
"""
LSTM 训练脚本：用历史序列 (seq_len, features) 预测下一日收益率。
可接入 factor_engine 产出特征 + 自建 y，或使用示例假数据。
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

import torch
from torch.utils.data import DataLoader, TensorDataset
from typing import Optional
from ai_models.lstm_model import LSTMModel


def train(
    input_size: int = 10,
    seq_len: int = 30,
    hidden: int = 64,
    epochs: int = 10,
    batch_size: int = 16,
    lr: float = 0.001,
    save_path: Optional[str] = None,
    X: Optional[torch.Tensor] = None,
    y: Optional[torch.Tensor] = None,
):
    """
    :param input_size: 特征维度
    :param seq_len: 序列长度（过去多少天）
    :param hidden: LSTM 隐藏层大小
    :param save_path: 模型保存路径；None 则默认 ai_models/lstm.pth
    """
    save_path = save_path or os.path.join(os.path.dirname(__file__), "lstm.pth")
    if X is None or y is None:
        # 假数据示例
        n_samples = 100
        X = torch.randn(n_samples, seq_len, input_size)
        y = torch.randn(n_samples, 1)
    loader = DataLoader(
        TensorDataset(X, y),
        batch_size=batch_size,
        shuffle=True,
    )
    model = LSTMModel(input_size=input_size, hidden=hidden)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            pred = model(xb)
            loss = loss_fn(pred, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        n_batches = len(loader)
        avg = total_loss / n_batches if n_batches else 0
        print(f"epoch {epoch} loss {avg:.6f}")

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Model saved: {save_path}")
    return model


if __name__ == "__main__":
    train()
