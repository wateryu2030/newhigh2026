"""RL trader: PPO/SAC training with Stable-Baselines3 (stub + optional SB3)."""

from typing import Any, Dict, Optional

# Optional: from stable_baselines3 import PPO, SAC; from sb3_contrib import RecurrentPPO
# Env: observation = features, action = position or trade signal, reward = PnL or Sharpe.


def create_rl_env(
    df_prices: Any,
    reward_type: str = "returns",
    **kwargs: Any,
) -> Any:
    """
    Create gym-style env for RL (stub). In production use gym.Env with price/feature df.
    reward_type: returns | sharpe | sortino.
    """
    return None  # Stub: return custom env wrapping df_prices


def train_ppo(
    env: Any,
    total_timesteps: int = 100_000,
    policy_kwargs: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    """Train PPO agent (stub). Requires stable_baselines3."""
    try:
        from stable_baselines3 import PPO

        model = PPO(
            "MlpPolicy",
            env,
            policy_kwargs=policy_kwargs or {},
            **kwargs,
        )
        model.learn(total_timesteps=total_timesteps)
        return model
    except ImportError:
        return None


def train_sac(
    env: Any,
    total_timesteps: int = 100_000,
    **kwargs: Any,
) -> Any:
    """Train SAC agent (stub). Requires stable_baselines3."""
    try:
        from stable_baselines3 import SAC

        model = SAC("MlpPolicy", env, **kwargs)
        model.learn(total_timesteps=total_timesteps)
        return model
    except ImportError:
        return None


def predict_signal(model: Any, obs: Any) -> int:
    """Predict action (e.g. -1, 0, 1 for SELL, HOLD, BUY) from trained model. Stub returns 0."""
    if model is None:
        return 0
    try:
        action, _ = model.predict(obs, deterministic=True)
        return int(action)
    except Exception:  # pylint: disable=broad-exception-caught  # RL model prediction fallback, safe to return 0 (HOLD)
        return 0
