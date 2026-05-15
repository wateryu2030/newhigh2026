#!/usr/bin/env python3
"""打印 data_pipeline 解析出的 DuckDB 绝对路径（与 Gateway 同源）。在仓库根执行。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline" / "src"))
if str(ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(ROOT / "lib"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass
try:
    from newhigh_env import load_dotenv_if_present

    load_dotenv_if_present(ROOT)
except ImportError:
    pass

from data_pipeline.storage.duckdb_manager import get_db_path  # noqa: E402

p = get_db_path()
print("get_db_path():", p)
print("文件存在:", os.path.isfile(p))
print("环境变量 QUANT_SYSTEM_DUCKDB_PATH:", os.environ.get("QUANT_SYSTEM_DUCKDB_PATH") or "(未设置，使用默认)")
