"""
Redis 缓存服务
用于性能优化
"""
import os
import redis
import json
import logging
from typing import Any, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 缓存服务"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.default_ttl = 300  # 默认 5 分钟
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, ensure_ascii=False)
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
    
    def get_stock_quote(self, symbol: str) -> Optional[dict]:
        """获取股票行情缓存"""
        return self.get(f"quote:{symbol}")
    
    def set_stock_quote(self, symbol: str, quote: dict, ttl: int = 60) -> bool:
        """设置股票行情缓存 (默认 1 分钟)"""
        return self.set(f"quote:{symbol}", quote, ttl)
    
    def get_stock_history(self, symbol: str, start_date: str, end_date: str) -> Optional[dict]:
        """获取历史行情缓存"""
        key = f"history:{symbol}:{start_date}:{end_date}"
        return self.get(key)
    
    def set_stock_history(self, symbol: str, start_date: str, end_date: str, data: dict, ttl: int = 3600) -> bool:
        """设置历史行情缓存 (默认 1 小时)"""
        key = f"history:{symbol}:{start_date}:{end_date}"
        return self.set(key, data, ttl)
    
    def invalidate_stock_cache(self, symbol: str) -> bool:
        """清除股票相关缓存"""
        try:
            # 清除行情缓存
            self.delete(f"quote:{symbol}")
            
            # 清除历史行情缓存 (使用通配符)
            pattern = f"history:{symbol}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            
            return True
        except Exception as e:
            logger.error(f"Redis invalidate error: {e}")
            return False


# 单例（Docker / 本机可通过 REDIS_HOST、REDIS_PORT 覆盖）
cache = RedisCache(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
)
