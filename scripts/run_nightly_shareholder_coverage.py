#!/usr/bin/env python3
"""
晚间股东数据巡检：生成 JSON 报告并写入缺失股票列表，可选按列表补采。

由 start_schedulers 每日 22:15 左右调用，也可手动：
  python scripts/run_nightly_shareholder_coverage.py

产出：
  - reports/shareholder_coverage_YYYYMMDD.json
  - reports/shareholder_coverage_latest.json
  - reports/missing_stocks.txt（无缺失时可能为空或仅换行）

环境变量：
  NIGHTLY_SHAREHOLDER_BACKFILL=1  — 在存在缺失时后台调用
      run_shareholder_collect.py --shareholders-only --stocks-file reports/missing_stocks.txt
  NIGHTLY_SHAREHOLDER_COLLECT_DELAY — 补采每股间隔秒，默认 0.6
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
MISSING_FILE = REPORTS / "missing_stocks.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [nightly_shareholder] %(levelname)s %(message)s",
)
LOG = logging.getLogger(__name__)


def _load_coverage_module():
    p = ROOT / "scripts" / "check_top10_shareholders_coverage.py"
    spec = importlib.util.spec_from_file_location("shareholder_cov", p)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 check_top10_shareholders_coverage")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "lib"))

    REPORTS.mkdir(parents=True, exist_ok=True)

    mod = _load_coverage_module()
    rep = mod.check_coverage(
        sample_missing=0,
        max_missing_file=50_000,
        write_missing_path=MISSING_FILE,
    )

    day = datetime.now().strftime("%Y%m%d")
    payload = json.dumps(rep, ensure_ascii=False, indent=2)
    (REPORTS / f"shareholder_coverage_{day}.json").write_text(payload, encoding="utf-8")
    (REPORTS / "shareholder_coverage_latest.json").write_text(payload, encoding="utf-8")

    missing_n = int(rep.get("missing_stocks_count") or 0)
    cov = rep.get("coverage_rate_pct")
    LOG.info(
        "巡检完成 ok=%s coverage=%s%% missing_stocks=%s 报告已写入 reports/",
        rep.get("ok"),
        cov,
        missing_n,
    )

    backfill = os.environ.get("NIGHTLY_SHAREHOLDER_BACKFILL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if backfill and rep.get("ok") and missing_n > 0 and MISSING_FILE.is_file():
        lines = [
            ln.strip().split(",")[0].strip()
            for ln in MISSING_FILE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if lines:
            delay = os.environ.get("NIGHTLY_SHAREHOLDER_COLLECT_DELAY", "0.6").strip() or "0.6"
            py = ROOT / ".venv" / "bin" / "python"
            exe = str(py) if py.is_file() else sys.executable
            LOG.info("NIGHTLY_SHAREHOLDER_BACKFILL: 启动补采 %d 只股票", len(lines))
            log_path = ROOT / "logs" / "shareholder_collect.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as flog:
                flog.write(f"\n--- nightly backfill {datetime.now().isoformat()} ---\n")
                proc = subprocess.Popen(
                    [
                        exe,
                        str(ROOT / "scripts" / "run_shareholder_collect.py"),
                        "--shareholders-only",
                        "--stocks-file",
                        str(MISSING_FILE.resolve()),
                        "--delay",
                        delay,
                    ],
                    cwd=str(ROOT),
                    env={**os.environ, "PYTHONPATH": str(ROOT)},
                    stdout=flog,
                    stderr=subprocess.STDOUT,
                )
            LOG.info("补采子进程已启动 PID=%s → logs/shareholder_collect.log", proc.pid)

    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
