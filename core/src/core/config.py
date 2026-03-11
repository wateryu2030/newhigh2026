"""统一配置：从环境变量与 .env 加载，供各模块使用。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    BaseSettings = None  # type: ignore

# 仓库根目录（core 在 core/src/core，向上 4 级）
_THIS_DIR = Path(__file__).resolve().parent
_CORE_SRC = _THIS_DIR.parent
_CORE_ROOT = _CORE_SRC.parent
_NEWHIGH_ROOT = _CORE_ROOT.parent
_DEFAULT_DATA_DIR = _NEWHIGH_ROOT / "data"
_DEFAULT_DB_PATH = _DEFAULT_DATA_DIR / "quant_system.duckdb"


def _str_path(v: Optional[str]) -> Optional[str]:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    return str(v).strip()


if BaseSettings is not None:

    class Settings(BaseSettings):
        """统一配置项；可通过环境变量或 .env 覆盖。"""

        # 数据库
        quant_system_duckdb_path: Optional[str] = None
        newhigh_market_duckdb_path: Optional[str] = None
        newhigh_duckdb_path: Optional[str] = None

        # Gateway / API
        api_host: str = "0.0.0.0"
        api_port: int = 8000
        api_reload: bool = False

        # 前端（NEXT_PUBLIC_ 由 Next 内联）
        next_public_api_target: Optional[str] = None

        # Celery / Redis（可选，阶段 0.1 使用）
        celery_broker_url: Optional[str] = None
        celery_result_backend: Optional[str] = None

        # 模拟盘 / 执行
        execution_simulated: bool = True
        execution_real_enabled: bool = False

        model_config = {
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "extra": "ignore",
        }

        def get_db_path(self) -> str:
            """统一 DuckDB 路径，与 duckdb_manager 逻辑一致。"""
            return (
                _str_path(self.quant_system_duckdb_path)
                or _str_path(self.newhigh_market_duckdb_path)
                or os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
                or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
                or str(_DEFAULT_DB_PATH)
            )

    settings = Settings()
else:
    settings = None  # type: ignore


def get_db_path() -> str:
    """统一入口：优先从 settings，否则从环境变量，最后默认路径。"""
    if settings is not None:
        return settings.get_db_path()
    return (
        os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
        or str(_DEFAULT_DB_PATH)
    )


def get_api_host() -> str:
    if settings is not None:
        return settings.api_host
    return os.environ.get("API_HOST", "0.0.0.0")


def get_api_port() -> int:
    if settings is not None:
        return settings.api_port
    try:
        return int(os.environ.get("API_PORT", "8000"))
    except ValueError:
        return 8000
