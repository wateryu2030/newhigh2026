"""cn_trading_calendar：周末结束日回退。"""

from datetime import datetime

from data_pipeline.data_sources.cn_trading_calendar import (
    cn_ashare_increment_end_yyyymmdd,
    incremental_range_empty,
)


def test_weekend_maps_to_friday():
    # 2026-04-12 周日
    assert cn_ashare_increment_end_yyyymmdd(datetime(2026, 4, 12, 12, 0)) == "20260410"
    # 2026-04-11 周六
    assert cn_ashare_increment_end_yyyymmdd(datetime(2026, 4, 11, 12, 0)) == "20260410"
    # 2026-04-10 周五
    assert cn_ashare_increment_end_yyyymmdd(datetime(2026, 4, 10, 12, 0)) == "20260410"


def test_incremental_range_empty():
    assert incremental_range_empty("20260410", "20260410")
    assert not incremental_range_empty("20260401", "20260410")
