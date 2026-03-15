"""板块轮动扫描：占位，后续接行业/板块数据写 sector 类 market_signals。"""

from __future__ import annotations


def run_sector_rotation_scanner() -> int:
    from ._storage import _get_conn, write_signals

    # 暂无 a_sector 表时写入空
    return write_signals([], "sector")
