"""在无 Cursor / LaunchAgent 场景加载仓库根 `.env`（TUSHARE_TOKEN、DuckDB 路径等）。"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_present(repo_root: Path | None = None) -> None:
    root = repo_root or Path(__file__).resolve().parent.parent
    env_file = root / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
    except ImportError:
        pass


def _strip_token_val(raw: object) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def hydrate_tushare_token_from_dotenv(repo_root: Path | None = None) -> None:
    """
    LaunchAgent / 定时任务进程常无交互 shell，仅有空的 TUSHARE_TOKEN。
    若环境变量仍为空，从 `.env` 原文读取并写入 os.environ（与 run_tushare_incremental 对齐）。
    """
    if (os.environ.get("TUSHARE_TOKEN") or "").strip():
        return
    root = repo_root or Path(__file__).resolve().parent.parent
    path = root / ".env"
    if not path.is_file():
        return
    try:
        from dotenv import dotenv_values
    except ImportError:
        return
    try:
        vals = dotenv_values(path) or {}
        for key in ("TUSHARE_TOKEN", "TUSHARE_API_KEY", "TS_TOKEN"):
            tok = _strip_token_val(vals.get(key))
            if tok and "你的" not in tok.lower() and len(tok) >= 8:
                os.environ["TUSHARE_TOKEN"] = tok
                return
    except Exception:
        pass
