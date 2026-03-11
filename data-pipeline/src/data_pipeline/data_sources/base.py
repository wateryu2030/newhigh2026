"""
数据源抽象基类与注册表：支持多数据源插件与增量更新。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

_SOURCE_REGISTRY: Dict[str, "BaseDataSource"] = {}


def register_source(source_id: str, source: "BaseDataSource") -> None:
    """注册数据源，供统一调度与 API 使用。"""
    _SOURCE_REGISTRY[source_id] = source


def get_source(source_id: str) -> Optional["BaseDataSource"]:
    """按 id 获取数据源。"""
    return _SOURCE_REGISTRY.get(source_id)


def list_sources() -> List[str]:
    """返回已注册数据源 id 列表。"""
    return list(_SOURCE_REGISTRY.keys())


class BaseDataSource(ABC):
    """
    数据源抽象：具备增量 key（如日期）、拉取与写入能力。
    子类实现 get_last_key / fetch / write，由 run_incremental 串联。
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """唯一标识，如 ashare_daily_kline。"""
        ...

    @abstractmethod
    def get_last_key(self, conn: Any) -> Optional[str]:
        """
        从库中取当前最大增量 key（如最新日期 YYYYMMDD）。
        无数据时返回 None，表示从最早可拉取开始。
        """
        ...

    @abstractmethod
    def fetch(
        self,
        start_key: Optional[str] = None,
        end_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        从外部 API 拉取数据。start_key/end_key 为增量区间（如日期）。
        返回 DataFrame 或可写入的结构；无数据时返回空 DataFrame。
        """
        ...

    @abstractmethod
    def write(self, conn: Any, data: Any) -> int:
        """将 data 写入 DuckDB，去重/覆盖由实现决定。返回写入行数。"""
        ...

    def default_end_key(self) -> str:
        """默认结束 key（如今天 YYYYMMDD），子类可覆盖。"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d")

    def run_incremental(self, conn: Any, force_full: bool = False, **kwargs: Any) -> int:
        """
        执行增量更新：用 get_last_key 得到起点，fetch 后 write。
        force_full=True 时忽略 last_key，从 start_key=None 拉取。
        """
        last = None if force_full else self.get_last_key(conn)
        end = kwargs.pop("end_key", self.default_end_key())
        data = self.fetch(start_key=last, end_key=end, **kwargs)
        if data is None or (hasattr(data, "empty") and data.empty):
            return 0
        return self.write(conn, data)
