#!/usr/bin/env python3
"""探测 Gateway data-overview 中实时/涨停快照是否新鲜。依赖 urllib + stdlib。"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_dp_src = ROOT / "data-pipeline" / "src"
if _dp_src.is_dir():
    p = str(_dp_src)
    if p not in sys.path:
        sys.path.insert(0, p)

from data_pipeline.freshness import (  # noqa: E402
    EXIT_INVALID,
    EXIT_MISSING_REALTIME,
    EXIT_OK,
    EXIT_STALE,
    check_overview_payload,
)


def _default_base_url() -> str:
    return (
        os.environ.get("DATA_FRESHNESS_BASE_URL")
        or os.environ.get("GATEWAY_BASE_URL")
        or "http://127.0.0.1:8000"
    ).rstrip("/")


def _fetch_overview(base_url: str, timeout_sec: float = 30.0) -> tuple[int, dict | None, str]:
    url = f"{base_url}/api/system/data-overview"
    # 部分 CDN/WAF 拦截默认 Python-urllib UA，导致 403；浏览器 UA 便于公网探活（仍只读 JSON）。
    ua = os.environ.get(
        "DATA_FRESHNESS_USER_AGENT",
        "Mozilla/5.0 (compatible; newhigh-data-freshness-probe/1.0)",
    )
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return EXIT_INVALID, None, f"http {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return EXIT_INVALID, None, f"url error: {e.reason!s}"
    except Exception as e:  # noqa: BLE001
        return EXIT_INVALID, None, f"request failed: {e}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return EXIT_INVALID, None, f"invalid json: {e}"
    if not isinstance(data, dict):
        return EXIT_INVALID, None, "json root is not an object"
    return EXIT_OK, data, ""


def main(argv: list[str] | None = None) -> int:
    env_req = os.environ.get("DATA_FRESHNESS_REQUIRE_REALTIME", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    parser = argparse.ArgumentParser(description="Check data-overview freshness via Gateway.")
    parser.add_argument(
        "--base-url",
        default=_default_base_url(),
        help="Gateway base URL (default: env DATA_FRESHNESS_BASE_URL / GATEWAY_BASE_URL or 127.0.0.1:8000)",
    )
    parser.add_argument(
        "--max-age-realtime",
        type=float,
        default=120.0,
        help="Max age in seconds for realtime snapshot (default: 120)",
    )
    parser.add_argument(
        "--max-age-limitup",
        type=float,
        default=360.0,
        help="Max age in seconds for limitup snapshot (default: 360)",
    )
    parser.add_argument(
        "--require-realtime",
        default=env_req,
        action=argparse.BooleanOptionalAction,
        help="Require realtime_snapshot_time (default from DATA_FRESHNESS_REQUIRE_REALTIME)",
    )
    args = parser.parse_args(argv)

    code, payload, err = _fetch_overview(args.base_url)
    if code != EXIT_OK or payload is None:
        print(err, file=sys.stderr)
        return EXIT_INVALID

    inner, msg = check_overview_payload(
        payload,
        max_age_realtime_sec=args.max_age_realtime,
        max_age_limitup_sec=args.max_age_limitup,
        require_realtime=args.require_realtime,
    )
    if inner != EXIT_OK:
        print(msg, file=sys.stderr)
    else:
        print(msg)
    return inner


if __name__ == "__main__":
    raise SystemExit(main())
