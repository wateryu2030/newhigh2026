#!/usr/bin/env python3
"""
输出全市场 7 维情绪 JSON（与 ``GET /api/market/sentiment-7d`` 同源逻辑）。

盘中建议先写入东财快照再算分（与 ``a_stock_realtime`` 一致）::

  UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py

环境变量与故障排查见仓库 ``docs/MARKET_SENTIMENT_TUSHARE_RUNBOOK.md`` 及 ``.env.example``（``SENTIMENT_7D_*``）。
本脚本会加载仓库根目录 ``.env``，与 ``run_tushare_incremental.py`` 使用同一 ``QUANT_SYSTEM_DUCKDB_PATH``。
"""
import json
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dp_src = os.path.join(_root, "data-pipeline", "src")
_lib = os.path.join(_root, "lib")
for p in (_lib, _dp_src, _root):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

_env_file = os.path.join(_root, ".env")
if os.path.isfile(_env_file):
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass
try:
    from pathlib import Path

    from newhigh_env import load_dotenv_if_present

    load_dotenv_if_present(Path(_root))
except ImportError:
    pass

if __name__ == "__main__":
    if os.environ.get("UPDATE_REALTIME_FIRST"):
        try:
            from data_pipeline.collectors.realtime_quotes import update_realtime_quotes

            n = update_realtime_quotes()
            print(f"realtime rows inserted: {n}", file=sys.stderr)
        except Exception as ex:
            print(f"realtime update skip: {ex}", file=sys.stderr)
    from data_pipeline.sentiment_7d import get_market_sentiment_7d

    print(json.dumps(get_market_sentiment_7d(), ensure_ascii=False, indent=2))
