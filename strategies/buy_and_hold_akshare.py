#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
买入并持有策略 - 使用 AKShare 数据
"""
from rqalpha.apis import *


def init(context):
    """初始化"""
    logger.info("买入并持有策略初始化")
    context.s1 = "000001.XSHE"  # 平安银行
    update_universe(context.s1)
    context.fired = False


def handle_bar(context, bar_dict):
    """处理 bar"""
    if not context.fired:
        # 买入并持有
        order_percent(context.s1, 1.0)
        context.fired = True
        logger.info(f"买入 {context.s1}，价格: {bar_dict[context.s1].close}")
