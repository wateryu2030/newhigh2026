#!/usr/bin/env python3
"""
依次执行数据质量检查，写入 DuckDB data_quality_reports、reports/latest_quality.json，
可选 Webhook 告警与 AUTO_BACKFILL 触发补采。

环境变量:
  DATA_QUALITY_WEBHOOK_URL  — POST JSON 告警
  COVERAGE_ALERT_THRESHOLD  — 股东覆盖率阈值，默认 90（低于则告警）
  AUTO_BACKFILL=1           — 覆盖率低于阈值时调用 trigger_backfill.py
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "data-pipeline" / "src"))

try:
    from newhigh_env import load_dotenv_if_present

    load_dotenv_if_present(ROOT)
except ImportError:
    pass

LOG = logging.getLogger(__name__)


def _load_shareholder_check_module():
    p = ROOT / "scripts" / "check_top10_shareholders_coverage.py"
    spec = importlib.util.spec_from_file_location("shareholder_cov", p)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 check_top10_shareholders_coverage")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _webhook_post(url: str, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        _ = resp.read(256)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    threshold = float(os.environ.get("COVERAGE_ALERT_THRESHOLD", "90"))
    webhook = os.environ.get("DATA_QUALITY_WEBHOOK_URL", "").strip()
    auto_backfill = os.environ.get("AUTO_BACKFILL", "").strip().lower() in ("1", "true", "yes")

    report: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [],
    }

    # 1) 股东覆盖 + 写缺失列表
    missing_path = ROOT / "reports" / "missing_stocks.txt"
    mod = _load_shareholder_check_module()
    sh = mod.check_coverage(
        sample_missing=0,
        max_missing_file=50_000,
        write_missing_path=missing_path,
    )
    report["checks"].append({"name": "shareholder_top10", "result": sh})

    cov = sh.get("coverage_rate_pct")
    if isinstance(cov, (int, float)) and cov < threshold:
        msg = f"股东覆盖率 {cov}% 低于阈值 {threshold}%"
        LOG.warning("ALERT: %s", msg)
        if webhook:
            try:
                _webhook_post(webhook, {"text": msg, "report": report})
            except urllib.error.URLError as e:
                LOG.error("Webhook 失败: %s", e)

    if auto_backfill and sh.get("ok") and sh.get("missing_stocks_count", 0) > 0:
        if missing_path.is_file():
            py = ROOT / ".venv" / "bin" / "python"
            exe = str(py) if py.is_file() else sys.executable
            LOG.info("AUTO_BACKFILL: 启动 trigger_backfill.py")
            subprocess.run(
                [exe, str(ROOT / "scripts" / "trigger_backfill.py"), "--file", str(missing_path)],
                cwd=str(ROOT),
                env={**os.environ, "PYTHONPATH": str(ROOT)},
            )

    # 2) 持久化
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    latest_json = reports_dir / "latest_quality.json"
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            LOG.error("DuckDB 文件不存在: %s", get_db_path())
            return 1
        conn = get_conn(read_only=False)
        nid = 0
        try:
            ensure_tables(conn)
            r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM data_quality_reports").fetchone()
            nid = int(r[0]) if r else 1
            conn.execute(
                "INSERT INTO data_quality_reports (id, report_json) VALUES (?, ?)",
                [nid, json.dumps(report, ensure_ascii=False)],
            )
        finally:
            conn.close()
        if nid:
            LOG.info("已写入 data_quality_reports id=%s", nid)
    except Exception:
        LOG.exception("写入 data_quality_reports 失败")

    return 0 if sh.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
