"""
应用配置
"""
import json
from typing import Any, List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # 应用配置
    APP_NAME: str = "红山量化交易平台"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "hongshan_quant"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    AUTO_INIT_DB: bool = True

    # CORS：支持逗号分隔或 JSON 数组字符串（便于 Docker env）
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://localhost:9080",
        "http://127.0.0.1:9080",
        "http://localhost:5174",
    ]

    # 飞书配置
    FEISHU_BOT_WEBHOOK: str = ""
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""

    # 交易配置
    DEFAULT_INITIAL_CAPITAL: float = 500000
    COMMISSION_RATE: float = 0.0003  # 万分之三
    STAMP_TAX_RATE: float = 0.001  # 千分之一

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Union[List[str], Any]:
        if v is None:
            return v
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except json.JSONDecodeError:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return v


settings = Settings()
