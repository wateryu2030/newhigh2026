"""
可选 Redis 热缓存：失败不抛出、不阻塞 DuckDB 主路径。
环境变量：REDIS_CACHE_URL（未设置则所有 API 为 no-op）。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

_log = logging.getLogger(__name__)
_URL = os.environ.get("REDIS_CACHE_URL", "").strip()
_TTL = int(os.environ.get("REDIS_CACHE_TTL_SEC", "300"))


def cache_get_json(key: str) -> Optional[Any]:
    if not _URL:
        return None
    try:
        import redis

        r = redis.from_url(_URL, decode_responses=True)
        raw = r.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception as e:
        _log.warning("redis_cache get %s failed: %s", key, e)
        return None


def cache_set_json(key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
    if not _URL:
        return
    try:
        import redis

        r = redis.from_url(_URL, decode_responses=True)
        r.setex(key, ttl_sec or _TTL, json.dumps(value, ensure_ascii=False, default=str))
    except Exception as e:
        _log.warning("redis_cache set %s failed: %s", key, e)


def pipeline_cache_key(source_id: str, suffix: str = "snapshot") -> str:
    return f"newhigh:pipeline:{source_id}:{suffix}"
