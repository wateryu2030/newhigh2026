"""
多环境配置加载：按 APP_ENV 加载 config/dev|staging|prod.yaml，与环境变量合并。
环境变量优先于 yaml。与 core.config 配合使用。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

_CONFIG_DIR = Path(__file__).resolve().parent
_ENV_KEY = "APP_ENV"


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_env_name() -> str:
    """返回当前环境：dev / staging / prod，默认 dev。"""
    return os.environ.get(_ENV_KEY, "dev").strip().lower() or "dev"


def load_env_config(env: str | None = None) -> Dict[str, Any]:
    """
    加载指定环境的 yaml 配置。env 默认从 APP_ENV 读取。
    返回扁平 dict，供覆盖 os.environ 或与 core.config 合并。
    """
    name = (env or get_env_name()).strip().lower() or "dev"
    if name not in ("dev", "staging", "prod"):
        name = "dev"
    path = _CONFIG_DIR / f"{name}.yaml"
    if not path.is_file():
        return {}
    return _load_yaml(path)


# 配置键到环境变量名的映射（pydantic-settings 常用命名）
_KEY_TO_ENV = {
    "api_host": "API_HOST",
    "api_port": "API_PORT",
    "api_reload": "API_RELOAD",
    "celery_broker_url": "CELERY_BROKER_URL",
    "celery_result_backend": "CELERY_RESULT_BACKEND",
    "execution_simulated": "EXECUTION_SIMULATED",
    "execution_real_enabled": "EXECUTION_REAL_ENABLED",
    "log_level": "LOG_LEVEL",
    "log_json": "LOG_JSON",
    "app_env": "APP_ENV",
}


def apply_env_from_config(config: Dict[str, Any]) -> None:
    """
    将 config 中的键值写入 os.environ（仅当该键尚未设置时）。
    键名通过 _KEY_TO_ENV 映射为环境变量名；未映射的键转为大写。
    """
    for k, v in config.items():
        env_key = _KEY_TO_ENV.get(k, str(k).upper())
        if os.environ.get(env_key) is not None and os.environ.get(env_key) != "":
            continue
        if v is None:
            continue
        os.environ.setdefault(env_key, str(v))


def init_app_env() -> Dict[str, Any]:
    """
    根据 APP_ENV 加载对应 yaml 并写入 os.environ（未设置项），返回配置 dict。
    建议在应用入口最早调用（如 gateway/app.py、system_runner）。
    """
    cfg = load_env_config()
    apply_env_from_config(cfg)
    return cfg
