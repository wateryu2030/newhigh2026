"""
Redis 缓存适配器：实时行情、会话等。未安装 redis 时返回 None。
"""
from __future__ import annotations

from typing import Any, Optional

_redis_client: Optional[Any] = None


def get_client() -> Optional[Any]:
    """返回 Redis 客户端；未配置或未安装 redis 时返回 None。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    import os
    url = os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")).strip()
    try:
        import redis
        _redis_client = redis.from_url(url)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None


def get_cache() -> Optional[Any]:
    """返回缓存对象：.get(key), .set(key, value, ttl_seconds)。"""
    c = get_client()
    if c is None:
        return None

    class _Cache:
        def __init__(self, client):
            self._client = client

        def get(self, key: str) -> Optional[str]:
            try:
                v = self._client.get(key)
                return v.decode() if isinstance(v, bytes) else v
            except Exception:
                return None

        def set(self, key: str, value: str, ttl_seconds: int = 300) -> bool:
            try:
                self._client.setex(key, ttl_seconds, value)
                return True
            except Exception:
                return False

    return _Cache(c)
