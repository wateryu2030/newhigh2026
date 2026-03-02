# -*- coding: utf-8 -*-
"""
席位数据库：知名游资席位与类型，与 core.lhb_engine.YZZ_SEATS 对齐。
"""
from __future__ import annotations
from typing import Dict, Any

# 知名游资席位：名称 -> 类型等属性（可扩展）
YZZ_SEATS: Dict[str, Dict[str, Any]] = {
    "章盟主": {"type": "游资"},
    "赵老哥": {"type": "游资"},
    "方新侠": {"type": "游资"},
    "溧阳路": {"type": "游资"},
    "小鳄鱼": {"type": "游资"},
    "炒股养家": {"type": "游资"},
    "作手新一": {"type": "游资"},
    "宁波解放南": {"type": "游资"},
    "上海溧阳路": {"type": "游资"},
    "深圳益田路": {"type": "游资"},
    "国泰君安南京太平南": {"type": "游资"},
    "华泰证券深圳益田路": {"type": "游资"},
    "中信证券杭州延安路": {"type": "游资"},
}


def is_yz_seat(seat_name: str) -> bool:
    """判断营业部名称是否包含知名游资席位。"""
    for key in YZZ_SEATS:
        if key in (seat_name or ""):
            return True
    return False


def seat_list() -> list:
    """返回席位名称列表，供 lhb_engine 等使用。"""
    return list(YZZ_SEATS.keys())
