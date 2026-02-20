#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单移动平均策略示例
使用 AKShare 数据源
"""
from rqalpha.apis import *


def init(context):
    """初始化"""
    logger.info("策略初始化")
    # 设置股票代码（平安银行）
    context.s1 = "000001.XSHE"
    update_universe(context.s1)
    
    # 策略参数
    context.SHORT_MA = 5   # 短期均线周期
    context.LONG_MA = 20   # 长期均线周期
    context.fired = False


def before_trading(context):
    """盘前处理"""
    pass


def handle_bar(context, bar_dict):
    """处理 bar 数据"""
    if context.s1 not in bar_dict:
        return
    # 获取历史收盘价
    prices = history_bars(context.s1, context.LONG_MA + 1, '1d', 'close')
    if prices is None or len(prices) < context.LONG_MA:
        return
    # 计算移动平均
    short_ma = float(prices[-context.SHORT_MA:].mean())
    long_ma = float(prices[-context.LONG_MA:].mean())
    current_price = float(bar_dict[context.s1].close)
    if current_price <= 0 or short_ma != short_ma or long_ma != long_ma or current_price != current_price:
        return
    # 获取当前持仓
    position = get_position(context.s1)
    cur_position = position.quantity if position else 0
    logger.info(f"价格: {current_price:.2f}, 短期均线: {short_ma:.2f}, 长期均线: {long_ma:.2f}, 持仓: {cur_position}")
    # 金叉：短期均线上穿长期均线，买入
    if short_ma > long_ma and cur_position == 0:
        cash = context.portfolio.cash
        if not cash or cash <= 0:
            return
        shares = int(cash / current_price / 100) * 100
        if shares > 0:
            order_shares(context.s1, shares)
            logger.info(f"买入信号: 买入 {shares} 股")
    
    # 死叉：短期均线下穿长期均线，卖出
    elif short_ma < long_ma and cur_position > 0:
        order_target_value(context.s1, 0)
        logger.info("卖出信号: 清仓")


def after_trading(context):
    """盘后处理"""
    pass
