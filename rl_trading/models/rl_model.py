# -*- coding: utf-8 -*-
"""
RL 模型封装：PPO 训练、保存、加载；支持决策解释（reason）。
"""
from __future__ import annotations
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv
    SB3_AVAILABLE = True
except ImportError:
    PPO = None
    BaseCallback = object
    DummyVecEnv = None
    SB3_AVAILABLE = False


class RLModelWrapper:
    """PPO 模型包装：训练、保存、加载、预测（含置信度与原因）。"""

    def __init__(
        self,
        env=None,
        policy: str = "MlpPolicy",
        total_timesteps: int = 50_000,
        learning_rate: float = 3e-4,
        model_path: Optional[str] = None,
    ):
        if not SB3_AVAILABLE:
            raise ImportError("请安装 stable-baselines3: pip install stable-baselines3")
        self.policy = policy
        self.total_timesteps = total_timesteps
        self.learning_rate = learning_rate
        self.model_path = model_path
        self.model = None
        if model_path and os.path.exists(model_path):
            self.model = PPO.load(model_path)
            logger.info("已加载 RL 模型: %s", model_path)

    def train(
        self,
        env,
        total_timesteps: Optional[int] = None,
        save_path: Optional[str] = None,
        callback: Optional[BaseCallback] = None,
    ) -> Dict[str, Any]:
        """训练 PPO；可传入 DummyVecEnv(env)。"""
        if self.model is None:
            self.model = PPO(
                self.policy,
                env,
                learning_rate=self.learning_rate,
                verbose=0,
            )
        steps = total_timesteps or self.total_timesteps
        self.model.learn(total_timesteps=steps, callback=callback)
        if save_path:
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            self.model.save(save_path)
            logger.info("模型已保存: %s", save_path)
        return {"total_timesteps": steps, "save_path": save_path}

    def predict(
        self,
        obs: np.ndarray,
        deterministic: bool = True,
    ) -> Tuple[int, Optional[np.ndarray]]:
        """返回 (action, state) 或 (0, None) 若未加载模型。"""
        if self.model is None:
            return 0, None
        action, _ = self.model.predict(obs, deterministic=deterministic)
        return int(action), None

    def predict_with_confidence(
        self,
        obs: np.ndarray,
    ) -> Tuple[int, float, List[str]]:
        """
        预测动作并给出置信度与原因列表（用于 UI「AI 为什么买」）。
        返回: (action, confidence, reasons)
        """
        if self.model is None:
            return 0, 0.0, ["模型未加载"]
        action, _ = self.model.predict(obs, deterministic=True)
        action = int(action)
        # 用 policy 评估得到 logits，转成概率作为置信度
        try:
            dist = self.model.policy.get_distribution(self.model.policy.obs_to_tensor(obs)[0])
            probs = dist.distribution.probs.detach().cpu().numpy()[0]
            confidence = float(probs[action])
        except Exception:
            confidence = 0.6
        reasons = _state_to_reasons(obs, action)
        return action, confidence, reasons

    def save(self, path: str) -> None:
        if self.model is not None:
            self.model.save(path)

    def load(self, path: str) -> None:
        if PPO is not None and os.path.exists(path):
            self.model = PPO.load(path)
            self.model_path = path


def _state_to_reasons(obs: np.ndarray, action: int) -> List[str]:
    """根据状态向量和动作生成可读原因（用于决策解释）。"""
    reasons = []
    if len(obs) >= 2:
        price_ratio, rsi = float(obs[0]), float(obs[1])
        if price_ratio > 0.05:
            reasons.append("价格在均线上方")
        elif price_ratio < -0.05:
            reasons.append("价格在均线下方")
        if rsi > 0.1:
            reasons.append("RSI 偏强")
        elif rsi < -0.1:
            reasons.append("RSI 偏弱")
    if len(obs) >= 4:
        pos_norm = float(obs[3])
        if pos_norm > 0.3 and action == 2:
            reasons.append("减仓锁定收益")
        elif pos_norm < -0.3 and action == 1:
            reasons.append("加仓机会")
    if action == 0:
        reasons.append("观望")
    elif action == 1:
        reasons.append("趋势/信号偏多")
    elif action == 2:
        reasons.append("趋势/信号偏空")
    return reasons if reasons else ["根据当前状态综合判断"]
