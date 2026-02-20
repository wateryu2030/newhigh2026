#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略4：高科技/消费ETF网格交易（稳健型）

策略逻辑：
- 针对高流动性的ETF做网格交易
- 高科技ETF：网格间距5%，利用高波动赚差价
- 消费ETF：网格间距3%，波动小但收益稳定
"""
from rqalpha.apis import *
import pandas as pd
import numpy as np
from strategies.utils import calculate_ma


# 策略参数
TECH_ETF = "512480.XSHG"  # 半导体ETF（示例，需确认实际代码）
CONSUME_ETF = "516130.XSHG"  # 消费龙头ETF（示例，需确认实际代码）
TECH_GRID_SPACING = 0.05  # 高科技网格间距5%
CONSUME_GRID_SPACING = 0.03  # 消费网格间距3%
GRID_POSITION_SIZE = 0.10  # 单格仓位10%
MA_WINDOW = 20  # 基准价使用20日均线
TECH_UPPER_LIMIT = 0.15  # 高科技上限+15%（清仓）
TECH_LOWER_LIMIT = -0.15  # 高科技下限-15%（满仓）
CONSUME_UPPER_LIMIT = 0.10  # 消费上限+10%
CONSUME_LOWER_LIMIT = -0.10  # 消费下限-10%
MAX_ETF_POSITION = 0.50  # 单ETF最大仓位50%
TREND_THRESHOLD = 0.20  # 趋势性行情阈值20%


def init(context):
    """初始化"""
    logger.info("策略4：ETF网格交易策略初始化")
    
    # ETF配置
    context.etf_config = {
        TECH_ETF: {
            "grid_spacing": TECH_GRID_SPACING,
            "upper_limit": TECH_UPPER_LIMIT,
            "lower_limit": TECH_LOWER_LIMIT,
            "base_price": None,  # 基准价（20日均线）
            "grid_levels": {},  # 网格层级持仓
            "trend_mode": False,  # 是否处于趋势模式
        },
        CONSUME_ETF: {
            "grid_spacing": CONSUME_GRID_SPACING,
            "upper_limit": CONSUME_UPPER_LIMIT,
            "lower_limit": CONSUME_LOWER_LIMIT,
            "base_price": None,
            "grid_levels": {},
            "trend_mode": False,
        }
    }
    
    context.rebalance_count = 0


def before_trading(context):
    """盘前处理"""
    pass


def handle_bar(context, bar_dict):
    """处理bar数据"""
    context.rebalance_count += 1
    
    # 每日更新基准价和检查网格
    for etf in [TECH_ETF, CONSUME_ETF]:
        if etf not in bar_dict:
            continue
        
        update_base_price(context, etf, bar_dict)
        check_trend_mode(context, etf, bar_dict)
        
        if not context.etf_config[etf]["trend_mode"]:
            execute_grid_trading(context, etf, bar_dict)


def update_base_price(context, etf, bar_dict):
    """更新基准价（20日均线）"""
    try:
        hist = history_bars(etf, MA_WINDOW, "1d", "close")
        if len(hist) >= MA_WINDOW:
            base_price = calculate_ma(hist, MA_WINDOW)
            context.etf_config[etf]["base_price"] = base_price
    except Exception as e:
        logger.debug(f"更新 {etf} 基准价失败: {e}")


def check_trend_mode(context, etf, bar_dict):
    """检查是否进入趋势模式"""
    config = context.etf_config[etf]
    base_price = config["base_price"]
    
    if base_price is None:
        return
    
    try:
        current_price = bar_dict[etf].close
        price_change = (current_price - base_price) / base_price
        
        # 如果涨跌幅超过阈值，进入趋势模式
        if abs(price_change) >= TREND_THRESHOLD:
            if not config["trend_mode"]:
                logger.info(f"{etf} 进入趋势模式: 涨跌幅 {price_change*100:.2f}%")
                config["trend_mode"] = True
        else:
            if config["trend_mode"]:
                logger.info(f"{etf} 退出趋势模式")
                config["trend_mode"] = False
    except:
        pass


def execute_grid_trading(context, etf, bar_dict):
    """执行网格交易"""
    config = context.etf_config[etf]
    base_price = config["base_price"]
    
    if base_price is None:
        return
    
    try:
        current_price = bar_dict[etf].close
        price_change = (current_price - base_price) / base_price
        
        # 检查是否超出上下限
        if price_change >= config["upper_limit"]:
            # 达到上限，清仓
            order_target_percent(etf, 0)
            logger.info(f"{etf} 达到上限，清仓")
            return
        
        if price_change <= config["lower_limit"]:
            # 达到下限，满仓（不超过最大仓位）
            order_target_percent(etf, MAX_ETF_POSITION)
            logger.info(f"{etf} 达到下限，满仓")
            return
        
        # 计算当前价格所在的网格层级
        grid_level = int(price_change / config["grid_spacing"])
        
        # 计算目标仓位（基于网格层级）
        target_position = calculate_grid_position(grid_level, config)
        
        # 获取当前仓位（使用 get_position API）
        pos = get_position(etf)
        total_value = context.portfolio.total_value
        current_weight = (pos.market_value / total_value) if pos and total_value and total_value > 0 else 0
        
        # 如果仓位差异较大，调整仓位
        if abs(target_position - current_weight) > 0.02:  # 2%差异阈值
            order_target_percent(etf, target_position)
            logger.info(f"{etf} 网格调仓: 层级 {grid_level}, 目标仓位 {target_position*100:.2f}%")
    
    except Exception as e:
        logger.error(f"执行 {etf} 网格交易失败: {e}")


def calculate_grid_position(grid_level, config):
    """计算网格目标仓位"""
    # 简化版：基于网格层级线性计算仓位
    # 实际可以根据更复杂的逻辑计算
    
    # 网格层级范围
    max_level = int(config["upper_limit"] / config["grid_spacing"])
    min_level = int(config["lower_limit"] / config["grid_spacing"])
    
    # 归一化层级到0-1
    if max_level == min_level:
        normalized_level = 0.5
    else:
        normalized_level = (grid_level - min_level) / (max_level - min_level)
    
    # 仓位从下限满仓到上限空仓
    target_position = MAX_ETF_POSITION * (1 - normalized_level)
    
    return max(0, min(target_position, MAX_ETF_POSITION))


def after_trading(context):
    """盘后处理"""
    pass
