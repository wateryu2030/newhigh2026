#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用移动平均策略 - 支持动态股票代码
通过 context.stock_code 设置股票代码
"""
from rqalpha.apis import *
import numpy as np


# 策略参数（可通过 context 覆盖）
DEFAULT_STOCK_CODE = "600745.XSHG"  # 默认：闻泰科技
SHORT_MA = 5   # 短期均线周期
LONG_MA = 20   # 长期均线周期
STOP_LOSS_RATIO = 0.08  # 止损8%
TAKE_PROFIT_RATIO = 0.20  # 止盈20%


def init(context):
    """初始化"""
    # 从多个来源获取股票代码：环境变量 > context.stock_code > config.extra > 默认值
    import os
    stock_code = os.environ.get('STOCK_CODE', None)
    if not stock_code:
        stock_code = getattr(context, 'stock_code', None)
    if not stock_code:
        stock_code = getattr(context.config.extra, 'stock_code', None) if hasattr(context, 'config') else None
    if not stock_code:
        stock_code = DEFAULT_STOCK_CODE
    
    context.stock = stock_code
    context.SHORT_MA = SHORT_MA
    context.LONG_MA = LONG_MA
    context.STOP_LOSS_RATIO = STOP_LOSS_RATIO
    context.TAKE_PROFIT_RATIO = TAKE_PROFIT_RATIO
    
    logger.info("=" * 50)
    logger.info("通用移动平均策略")
    logger.info(f"标的: {context.stock}")
    logger.info(f"短期均线: {context.SHORT_MA}日, 长期均线: {context.LONG_MA}日")
    logger.info(f"止损: {context.STOP_LOSS_RATIO*100}%, 止盈: {context.TAKE_PROFIT_RATIO*100}%")
    logger.info("=" * 50)
    
    # 设置股票池
    update_universe(context.stock)
    
    # 初始化状态
    context.last_short_ma = None
    context.last_long_ma = None
    context.position_held = False


def before_trading(context):
    """盘前处理"""
    pass


def handle_bar(context, bar_dict):
    """处理bar数据"""
    if context.stock not in bar_dict:
        logger.warn(f"无法获取 {context.stock} 的行情数据")
        return
    
    try:
        # 获取历史收盘价
        prices = history_bars(context.stock, context.LONG_MA + 1, '1d', 'close')
        
        if len(prices) < context.LONG_MA:
            logger.debug(f"历史数据不足，需要 {context.LONG_MA} 日，当前 {len(prices)} 日")
            return
        
        # 计算移动平均
        short_ma = np.mean(prices[-context.SHORT_MA:])
        long_ma = np.mean(prices[-context.LONG_MA:])
        
        current_price = bar_dict[context.stock].close
        
        # 获取当前持仓
        position = get_position(context.stock)
        current_quantity = position.quantity if position else 0
        
        # 记录日志（简化版，避免日志过多）
        if current_quantity > 0 or (context.last_short_ma is not None and 
            ((context.last_short_ma <= context.last_long_ma and short_ma > long_ma) or
             (context.last_short_ma >= context.last_long_ma and short_ma < long_ma))):
            logger.info(f"日期: {context.now.strftime('%Y-%m-%d')}, 价格: {current_price:.2f}, "
                       f"短期MA: {short_ma:.2f}, 长期MA: {long_ma:.2f}, 持仓: {current_quantity}")
        
        # 检查止损止盈
        if current_quantity > 0:
            cost_price = position.avg_price
            if cost_price > 0:
                profit_ratio = (current_price - cost_price) / cost_price
                
                # 止损
                if profit_ratio <= -context.STOP_LOSS_RATIO:
                    order_target_percent(context.stock, 0)
                    logger.info(f"触发止损卖出: 亏损 {profit_ratio*100:.2f}%")
                    context.position_held = False
                    return
                
                # 止盈
                if profit_ratio >= context.TAKE_PROFIT_RATIO:
                    order_target_percent(context.stock, 0)
                    logger.info(f"触发止盈卖出: 盈利 {profit_ratio*100:.2f}%")
                    context.position_held = False
                    return
        
        # 判断买卖信号
        if context.last_short_ma is not None and context.last_long_ma is not None:
            # 金叉：短期均线上穿长期均线
            if context.last_short_ma <= context.last_long_ma and short_ma > long_ma:
                if current_quantity == 0:
                    # 买入
                    order_target_percent(context.stock, 1.0)  # 满仓
                    logger.info("=" * 30)
                    logger.info("买入信号: 金叉")
                    logger.info(f"买入价格: {current_price:.2f}")
                    logger.info("=" * 30)
                    context.position_held = True
            
            # 死叉：短期均线下穿长期均线
            elif context.last_short_ma >= context.last_long_ma and short_ma < long_ma:
                if current_quantity > 0:
                    # 卖出
                    order_target_percent(context.stock, 0)
                    logger.info("=" * 30)
                    logger.info("卖出信号: 死叉")
                    logger.info(f"卖出价格: {current_price:.2f}")
                    logger.info("=" * 30)
                    context.position_held = False
        
        # 更新均线值
        context.last_short_ma = short_ma
        context.last_long_ma = long_ma
        
    except Exception as e:
        logger.error(f"处理bar数据时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())


def after_trading(context):
    """盘后处理"""
    pass
