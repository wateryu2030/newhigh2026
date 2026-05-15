"""
DuckDB 批量写任务互斥：对「与库文件同目录的 *.writer.lock」使用 flock(2)。

- Unix/macOS：fcntl.flock
- Windows：无 fcntl 时跳过锁并打印警告（仅开发机）

环境变量 NEWHIGH_SKIP_DUCKDB_FLOCK=1/true 时跳过加锁（应急）。
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


class DuckDbFlockBusy(Exception):
    """非阻塞模式下锁已被占用。"""


class DuckDbFlockTimeout(Exception):
    """阻塞等待超时。"""


def _skip_lock() -> bool:
    return os.environ.get("NEWHIGH_SKIP_DUCKDB_FLOCK", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def writer_lock_path(db_path: str) -> Path:
    p = Path(db_path).expanduser().resolve()
    return p.parent / f"{p.name}.writer.lock"


def resolve_db_path(explicit: Optional[str] = None) -> str:
    if explicit and explicit.strip():
        return str(Path(explicit).expanduser().resolve())
    root = Path(__file__).resolve().parent.parent
    for sub in ("data-pipeline/src",):
        d = root / sub
        if d.is_dir() and str(d) not in sys.path:
            sys.path.insert(0, str(d))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from data_pipeline.storage.duckdb_manager import get_db_path

    return get_db_path()


@contextmanager
def duckdb_write_lock(
    db_path: Optional[str] = None,
    *,
    blocking: bool = True,
    timeout_sec: float = 7200,
    poll_sec: float = 3.0,
) -> Generator[str, None, None]:
    """
    独占写锁；退出上下文后释放。

    :param db_path: 默认用 get_db_path()
    :param blocking: False 时若锁被占用立即抛 DuckDbFlockBusy
    :param timeout_sec: blocking=True 时最长等待秒数（0 表示无限等待）
    """
    if _skip_lock():
        path = resolve_db_path(db_path)
        print("[duckdb-lock] NEWHIGH_SKIP_DUCKDB_FLOCK=1，跳过 flock", file=sys.stderr, flush=True)
        yield path
        return

    try:
        import fcntl
    except ImportError:
        path = resolve_db_path(db_path)
        print(
            "[duckdb-lock] 当前平台无 fcntl，跳过 flock（不建议在生产依赖）",
            file=sys.stderr,
            flush=True,
        )
        yield path
        return

    path = resolve_db_path(db_path)
    lock_fp = writer_lock_path(path)
    lock_fp.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(str(lock_fp), os.O_CREAT | os.O_RDWR, 0o644)
    start = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not blocking:
                    raise DuckDbFlockBusy(
                        f"另一进程正持有 DuckDB 写锁: {lock_fp}（数据库: {path}）"
                    ) from None
                elapsed = time.monotonic() - start
                if timeout_sec > 0 and elapsed >= timeout_sec:
                    raise DuckDbFlockTimeout(
                        f"等待写锁超时 {timeout_sec}s: {lock_fp}"
                    ) from None
                print(
                    f"[duckdb-lock] 等待写锁 {lock_fp.name}（已等待 {int(elapsed)}s）…",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(poll_sec)
        print(f"[duckdb-lock] 已获取写锁 {lock_fp}", file=sys.stderr, flush=True)
        yield path
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(fd)
        except Exception:
            pass
        print(f"[duckdb-lock] 已释放写锁 {lock_fp}", file=sys.stderr, flush=True)
