# -*- coding: utf-8 -*-
"""
TDengine 行情接入（可选）：预留接口，当前项目以 DuckDB 为主。
"""
from __future__ import annotations
from typing import Optional

import pandas as pd


def get_bars(
    symbol: str,
    start_date: str,
    end_date: str,
    table: str = "price_daily",
) -> Optional[pd.DataFrame]:
    """
    从 TDengine 读取日线。未配置时返回 None，由上层回退到 DuckDB。
    """
    return None
