# Auto-fixed by Cursor on 2026-04-02: pydantic-settings for quant YAML + env.
"""可选配置加载：config/quant_platform.yaml + 环境变量前缀 NEWHIGH_QUANT_."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QuantPlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEWHIGH_QUANT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    default_commission_per_leg: float = Field(default=0.0002)
    default_slippage_per_leg: float = Field(default=0.001)
    signal_execution_lag_bdays: int = Field(default=1)
    parquet_root: str = Field(default="data/parquet")


def load_settings(yaml_path: Optional[Path] = None) -> QuantPlatformSettings:
    base = QuantPlatformSettings()
    path = yaml_path or Path(__file__).resolve().parent / "quant_platform.yaml"
    if not path.is_file():
        return base
    try:
        import yaml  # type: ignore
    except ImportError:
        return base
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        bt = raw.get("backtest") or {}
        data = raw.get("data") or {}
        return QuantPlatformSettings(
            default_commission_per_leg=float(bt.get("default_commission_per_leg", base.default_commission_per_leg)),
            default_slippage_per_leg=float(bt.get("default_slippage_per_leg", base.default_slippage_per_leg)),
            signal_execution_lag_bdays=int(bt.get("signal_execution_lag_bdays", base.signal_execution_lag_bdays)),
            parquet_root=str(data.get("parquet_root", base.parquet_root)),
        )
    except Exception:
        return base
