#!/usr/bin/env python3
"""
新闻采集入口（写入 quant_system.duckdb 的 news_items，含 url）：

1. 东财个股新闻（akshare，稳定）：默认从前 N 只股票各取若干条，带原文链接。
2. 财新（tushare.internet.caixinnews）：搜索页若改版可能失败，失败时不影响东财结果。

用法（仓库根目录）：

  .venv/bin/python scripts/run_news_collect.py
  NEWS_EM_CODES_LIMIT=120 NEWS_EM_PER_CODE=10 .venv/bin/python scripts/run_news_collect.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data-pipeline" / "src"))

try:
    from lib.newhigh_env import load_dotenv_if_present
except ImportError:
    load_dotenv_if_present = None  # type: ignore[misc, assignment]

if load_dotenv_if_present:
    load_dotenv_if_present(ROOT)


def main() -> int:
    from data_pipeline.collectors.caixin_news import update_caixin_news
    from data_pipeline.collectors.em_stock_news import update_em_stock_news

    n_em = update_em_stock_news(
        codes_limit=int(os.environ.get("NEWS_EM_CODES_LIMIT", "80")),
        per_code_limit=int(os.environ.get("NEWS_EM_PER_CODE", "12")),
    )

    kw = os.environ.get("NEWS_KEYWORDS", "经济")
    days = int(os.environ.get("NEWS_DAYS_BACK", "5"))
    print(f"尝试财新: keywords={kw!r}, days_back={days}")
    n_cx = update_caixin_news(keywords=kw, days_back=days)

    print(f"完成: 东财新写入 {n_em} 条, 财新处理 {n_cx} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
