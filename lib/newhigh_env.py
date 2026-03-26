"""在无 Cursor / LaunchAgent 场景加载仓库根 `.env`（TUSHARE_TOKEN、DuckDB 路径等）。"""

from __future__ import annotations

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
