#!/usr/bin/env python3
"""
运行深度分析，并将「行业地位与前景 / 机会发现引擎」段落写入独立 Markdown。

默认输出：personal_assistant/reports/deep_industry_YYYY-MM-DD.md

用法：
  python run_deep_industry.py                    # 内置示例股票池
  python run_deep_industry.py 002701.XSHE        # 指定一只或多只
  python run_deep_industry.py --no-write         # 仅终端分析，不写文件
  python run_deep_industry.py --config           # 使用 config.json 的 fixed_stocks
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from deep_analyzer import analyze_target_stocks  # noqa: E402


def _load_fixed_from_config() -> list[str] | None:
    cfg_path = ROOT / "config.json"
    if not cfg_path.is_file():
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        stocks = cfg.get("fixed_stocks")
        if isinstance(stocks, list) and stocks:
            return [str(x) for x in stocks]
    except (json.JSONDecodeError, OSError):
        pass
    return None


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--no-write" and a != "--config"]
    use_config = "--config" in sys.argv
    write_md = "--no-write" not in sys.argv

    codes: list[str] | None = None
    if use_config:
        codes = _load_fixed_from_config()
        if not codes:
            print("⚠️ config.json 中无 fixed_stocks，改用命令行或默认股票池")
    if args:
        codes = args

    analyze_target_stocks(
        target_stocks=codes,
        write_industry_md=write_md,
    )


if __name__ == "__main__":
    main()
