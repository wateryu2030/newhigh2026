#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单移动平均策略 - 使用 AKShare 数据源
展示如何使用 AKShare → RQAlpha 数据源适配层

策略逻辑：
- 短期均线上穿长期均线时买入
- 短期均线下穿长期均线时卖出
"""
from rqalpha.apis import *
import numpy as np


def init(context):
    """策略初始化"""
    # 从环境变量或配置获取股票代码
    import os
    stock_code = os.environ.get('STOCK_CODE') or getattr(context.config.extra, 'stock_code', None)
    
    if not stock_code:
        # 默认股票：闻泰科技
        stock_code = "600745.XSHG"
    
    context.stock = stock_code
    context.short_ma = 5   # 短期均线周期
    context.long_ma = 20   # 长期均线周期
    
    logger.info("=" * 50)
    logger.info("简单移动平均策略 - AKShare 数据源")
    logger.info(f"标的: {context.stock}")
    logger.info(f"短期均线: {context.short_ma}日")
    logger.info(f"长期均线: {context.long_ma}日")
    logger.info("=" * 50)
    
    # 将股票加入 universe
    update_universe(context.stock)


def handle_bar(context, bar_dict):
    """处理 bar 数据"""
    stock = context.stock
    
    if stock not in bar_dict:
        return
    
    # 获取历史价格数据
    hist = history_bars(stock, context.long_ma, "1d", "close")
    
    if len(hist) < context.long_ma:
        return
    
    # 计算均线
    short_ma_value = np.mean(hist[-context.short_ma:])
    long_ma_value = np.mean(hist[-context.long_ma:])
    
    # 获取当前持仓
    position = get_position(stock)
    
    # 交易逻辑
    if short_ma_value > long_ma_value and position.quantity == 0:
        # 买入信号：短期均线上穿长期均线
        order_target_percent(stock, 1.0)  # 满仓买入
        logger.info(f"{context.now.date()} 买入信号: 短期均线({short_ma_value:.2f}) > 长期均线({long_ma_value:.2f})")
    
    elif short_ma_value < long_ma_value and position.quantity > 0:
        # 卖出信号：短期均线下穿长期均线
        order_target_percent(stock, 0.0)  # 清仓
        logger.info(f"{context.now.date()} 卖出信号: 短期均线({short_ma_value:.2f}) < 长期均线({long_ma_value:.2f})")
