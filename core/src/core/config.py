"""
统一配置中心

所有配置项通过此模块管理，优先使用 pydantic-settings，
否则回退到环境变量。

使用示例:
    from core.config import settings, get_db_path, get_api_port

    db_path = get_db_path()
    api_port = get_api_port()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Dict, Any

# 项目根目录定位 (从 core/src/core 向上 3 层)
_THIS_DIR = Path(__file__).resolve().parent
_CORE_SRC = _THIS_DIR.parent
_CORE_ROOT = _CORE_SRC.parent
_NEWHIGH_ROOT = _CORE_ROOT.parent

_DEFAULT_DATA_DIR = _NEWHIGH_ROOT / "data"
_DEFAULT_DB_PATH = _DEFAULT_DATA_DIR / "quant_system.duckdb"

# === 统一环境变量前缀 ===
ENV_PREFIX = "QUANT_"


def _str_path(v: Optional[str]) -> Optional[str]:
    """清理字符串路径"""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    return str(v).strip()


# === 配置类定义 ===
class _Settings:
    """简化版配置类 (不依赖 pydantic-settings)"""

    def __init__(self):
        # 数据库配置
        self.db_path: Optional[str] = None
        self.db_read_only: bool = False

        # API 配置
        self.api_host: str = "0.0.0.0"
        self.api_port: int = 8000
        self.api_debug: bool = False

        # 前端配置
        self.frontend_url: str = "http://localhost:3000"

        # AI 模型配置
        self.llm_provider: str = "dashscope"
        self.llm_model: str = "qwen3.5-plus"
        self.llm_api_key: Optional[str] = None

        # 数据源配置
        self.akshare_enabled: bool = True
        self.tushare_enabled: bool = False
        self.tushare_token: Optional[str] = None

        # 定时任务配置
        self.news_collection_interval: int = 3600  # 秒
        self.scanner_interval: int = 300  # 秒

        # OpenClaw 配置
        self.openclaw_enabled: bool = True
        self.evolution_population_limit: int = 100

        # 从环境变量加载
        self._load_from_env()

    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        # 数据库
        self.db_path = _str_path(os.environ.get(f"{ENV_PREFIX}DB_PATH"))
        self.db_read_only = os.environ.get(f"{ENV_PREFIX}DB_READ_ONLY", "false").lower() == "true"

        # API
        if api_host := os.environ.get(f"{ENV_PREFIX}API_HOST"):
            self.api_host = api_host
        if api_port := os.environ.get(f"{ENV_PREFIX}API_PORT"):
            try:
                self.api_port = int(api_port)
            except ValueError:
                pass
        self.api_debug = os.environ.get(f"{ENV_PREFIX}API_DEBUG", "false").lower() == "true"

        # AI
        if llm_provider := os.environ.get(f"{ENV_PREFIX}LLM_PROVIDER"):
            self.llm_provider = llm_provider
        if llm_model := os.environ.get(f"{ENV_PREFIX}LLM_MODEL"):
            self.llm_model = llm_model
        self.llm_api_key = _str_path(os.environ.get(f"{ENV_PREFIX}LLM_API_KEY"))

        # 数据源
        self.akshare_enabled = os.environ.get(
            f"{ENV_PREFIX}AKSHARE_ENABLED",
            "true").lower() == "true"
        self.tushare_enabled = os.environ.get(
            f"{ENV_PREFIX}TUSHARE_ENABLED",
            "false").lower() == "true"
        self.tushare_token = _str_path(os.environ.get(f"{ENV_PREFIX}TUSHARE_TOKEN"))

        # 定时任务
        if interval := os.environ.get(f"{ENV_PREFIX}NEWS_INTERVAL"):
            try:
                self.news_collection_interval = int(interval)
            except ValueError:
                pass
        if interval := os.environ.get(f"{ENV_PREFIX}SCANNER_INTERVAL"):
            try:
                self.scanner_interval = int(interval)
            except ValueError:
                pass

        # OpenClaw
        self.openclaw_enabled = os.environ.get(
            f"{ENV_PREFIX}OPENCLAW_ENABLED", "true").lower() == "true"
        if limit := os.environ.get(f"{ENV_PREFIX}EVOLUTION_LIMIT"):
            try:
                self.evolution_population_limit = int(limit)
            except ValueError:
                pass

    def get_db_path(self) -> str:
        """统一数据库路径获取"""
        return (
            self.db_path
            or os.environ.get("QUANT_DB_PATH", "").strip()
            or os.environ.get("NEWHIGH_DB_PATH", "").strip()
            or str(_DEFAULT_DB_PATH)
        )


# 全局配置实例
settings = _Settings()


# === 便捷函数 ===

def get_db_path() -> str:
    """获取数据库路径"""
    return settings.get_db_path()


def get(key: str, default: Any = None) -> Any:
    """获取配置项"""
    return getattr(settings, key, default)


def get_api_host() -> str:
    """获取 API 主机"""
    return settings.api_host


def get_api_port() -> int:
    """获取 API 端口"""
    return settings.api_port


def get_llm_config() -> Dict[str, str]:
    """获取 LLM 配置"""
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "api_key": settings.llm_api_key or "",
    }


def is_module_enabled(module_name: str) -> bool:
    """检查模块是否启用"""
    return getattr(settings, f"{module_name}_enabled", True)


# === 环境变量模板 ===

ENV_TEMPLATE = """
# 量化平台配置文件
# 复制为 .env 并根据需要修改

# === 数据库配置 ===
QUANT_DB_PATH=/Users/apple/Ahope/newhigh/data/quant_system.duckdb
QUANT_DB_READ_ONLY=false

# === API 配置 ===
QUANT_API_HOST=0.0.0.0
QUANT_API_PORT=8000
QUANT_API_DEBUG=false

# === AI 模型配置 ===
QUANT_LLM_PROVIDER=dashscope
QUANT_LLM_MODEL=qwen3.5-plus
QUANT_LLM_API_KEY=sk-xxx

# === 数据源配置 ===
QUANT_AKSHARE_ENABLED=true
QUANT_TUSHARE_ENABLED=false
QUANT_TUSHARE_TOKEN=xxx

# === 定时任务配置 ===
QUANT_NEWS_INTERVAL=3600
QUANT_SCANNER_INTERVAL=300

# === OpenClaw 配置 ===
QUANT_OPENCLAW_ENABLED=true
QUANT_EVOLUTION_LIMIT=100
""".strip()


def print_env_template() -> None:
    """打印环境变量模板"""
    print(ENV_TEMPLATE)
