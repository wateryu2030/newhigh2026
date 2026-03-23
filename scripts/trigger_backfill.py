#!/usr/bin/env python3
"""
根据缺失股票列表触发股东补采（调用 run_shareholder_collect.py）。

用法:
  python scripts/trigger_backfill.py
  python scripts/trigger_backfill.py --file reports/missing_stocks.txt
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "logs" / "shareholder_backfill.lock"
LOG = logging.getLogger(__name__)
_LOCK_FP = None


def acquire_lock() -> bool:
    try:
        import fcntl
    except ImportError:
        return True
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_f = open(LOCK_PATH, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_f.write(str(os.getpid()))
        lock_f.flush()
        global _LOCK_FP  # noqa: PLW0603
        _LOCK_FP = lock_f
        return True
    except BlockingIOError:
        lock_f.close()
        LOG.warning("补数锁已被占用，跳过本次 trigger_backfill")
        return False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="触发股东数据补采")
    parser.add_argument(
        "--file",
        type=str,
        default=str(ROOT / "reports" / "missing_stocks.txt"),
        help="缺失股票代码文件（一行一个）",
    )
    parser.add_argument("--delay", type=float, default=0.6, help="传给 run_shareholder_collect")
    args = parser.parse_args()

    fp = Path(args.file)
    if not fp.is_file():
        LOG.error("缺失列表文件不存在: %s", fp)
        return 1

    lines = [ln.strip().split(",")[0].strip() for ln in fp.read_text(encoding="utf-8").splitlines()]
    codes = [c for c in lines if c and not c.startswith("#")]
    if not codes:
        LOG.info("缺失列表为空，不启动补采")
        return 0

    if not acquire_lock():
        return 2

    py = ROOT / ".venv" / "bin" / "python"
    exe = str(py) if py.is_file() else sys.executable
    cmd = [
        exe,
        str(ROOT / "scripts" / "run_shareholder_collect.py"),
        "--shareholders-only",
        "--stocks-file",
        str(fp.resolve()),
        "--delay",
        str(args.delay),
    ]
    LOG.info("启动补采: %d 只股票", len(codes))
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    LOG.info("补采结束 exit=%s", proc.returncode)
    return int(proc.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
