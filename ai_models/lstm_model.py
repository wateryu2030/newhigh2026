# -*- coding: utf-8 -*-
"""
LSTM 模型：输入过去 T 天特征序列，输出未来 1 日收益率。
机构常用序列预测模型，可与因子引擎联合使用。
"""
import torch
import torch.nn as nn
from typing import Optional


class LSTMModel(nn.Module):
    """
    输入: (batch, seq_len, input_size)，如 (batch, 30, 10)
    输出: (batch, 1)，未来 1 日收益率
    """

    def __init__(self, input_size: int, hidden: int = 64, num_layers: int = 1):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size,
            hidden,
            num_layers=num_layers,
            batch_first=True,
        )
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        out = self.fc(out)
        return out
