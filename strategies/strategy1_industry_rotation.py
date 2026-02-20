#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略1：高科技+消费行业轮动策略（基本面+资金流双驱动）

策略逻辑：
- 筛选高科技（半导体/AI/算力）和消费（食品饮料/美妆/家电）核心行业
- 基于行业景气度（财务）+ 资金流（北向/主力资金）做月度轮动
- 选景气度高+资金净流入的行业，持仓龙头标的
"""
from rqalpha.apis import *
import pandas as pd
import numpy as np
import os
from strategies.utils import normalize_score


# 策略参数
TECH_INDUSTRIES = ["半导体", "计算机应用", "电力设备"]
CONSUME_INDUSTRIES = ["食品饮料", "美容护理", "白色家电"]
TARGET_INDUSTRIES = TECH_INDUSTRIES + CONSUME_INDUSTRIES
REBALANCE_INTERVAL = 30  # 月度调仓（30个交易日）
STOP_LOSS_RATIO = 0.08  # 8%止损
TOP_N_INDUSTRIES = 2  # 选前2个行业
TOP_N_STOCKS_PER_INDUSTRY = 3  # 每个行业选前3只股票


def init(context):
    """初始化"""
    logger.info("策略1：行业轮动策略初始化")
    
    # 加载行业-股票映射表
    data_dir = "data"
    industry_map_path = os.path.join(data_dir, "industry_stock_map.csv")
    industry_score_path = os.path.join(data_dir, "industry_score.csv")
    
    if os.path.exists(industry_map_path):
        df = pd.read_csv(industry_map_path, encoding="utf-8-sig")
        # 支持两种格式：① 股票代码（每行一行业，逗号分隔） ② 代码+行业名称（每行一股票）
        if "股票代码" in df.columns:
            context.industry_stock_map = dict(zip(
                df["行业名称"],
                df["股票代码"].str.split(",")
            ))
        elif "代码" in df.columns and "行业名称" in df.columns:
            context.industry_stock_map = df.groupby("行业名称")["代码"].apply(list).to_dict()
        else:
            logger.warn("行业映射表缺少「股票代码」或「代码」列，使用默认股票池")
            context.industry_stock_map = {
                "半导体": ["000001.XSHE", "000002.XSHE"],
                "食品饮料": ["600519.XSHG", "000858.XSHE"],
            }
    else:
        logger.warn("未找到行业股票映射表，使用默认股票池")
        context.industry_stock_map = {}
        # 默认股票池（示例）
        context.industry_stock_map["半导体"] = ["000001.XSHE", "000002.XSHE"]
        context.industry_stock_map["食品饮料"] = ["600519.XSHG", "000858.XSHE"]
    
    # 将映射表内所有股票加入订阅池，否则 bar_dict 中无数据会导致「未找到目标股票」
    all_pool = []
    for stocks in context.industry_stock_map.values():
        all_pool.extend(stocks)
    all_pool = list(dict.fromkeys(all_pool))
    if all_pool:
        update_universe(all_pool)
        logger.info(f"已加入 {len(all_pool)} 只股票到 universe: {all_pool}")
    
    if os.path.exists(industry_score_path):
        context.industry_score = pd.read_csv(industry_score_path, encoding="utf-8-sig", index_col=0)
    else:
        logger.warn("未找到行业得分表，使用默认得分")
        context.industry_score = pd.DataFrame({
            "综合得分": [50] * len(TARGET_INDUSTRIES)
        }, index=TARGET_INDUSTRIES)
    
    context.rebalance_count = 0
    context.target_stocks = []


def before_trading(context):
    """盘前处理"""
    pass


def handle_bar(context, bar_dict):
    """处理bar数据"""
    context.rebalance_count += 1
    
    # 月度调仓
    if context.rebalance_count % REBALANCE_INTERVAL == 0:
        rebalance(context, bar_dict)
    
    # 止损检查
    check_stop_loss(context, bar_dict)


def rebalance(context, bar_dict):
    """调仓逻辑"""
    logger.info("执行月度调仓")
    
    # 1. 筛选综合得分前N的行业
    if len(context.industry_score) == 0:
        logger.warn("行业得分表为空，跳过调仓")
        return
    
    top_industries = context.industry_score.sort_values(
        "综合得分", ascending=False
    ).head(TOP_N_INDUSTRIES).index.tolist()
    
    logger.info(f"选中行业: {top_industries}")
    
    # 2. 每个行业选市值前N的龙头
    target_stocks = []
    for industry in top_industries:
        if industry not in context.industry_stock_map:
            continue
        
        stocks = context.industry_stock_map[industry]
        # 过滤掉不存在的股票
        valid_stocks = [s for s in stocks if s in bar_dict]
        
        if len(valid_stocks) == 0:
            continue
        
        # 按市值排序（简化：使用当前价格*成交量作为代理）
        stock_scores = {}
        for stock in valid_stocks:
            try:
                price = bar_dict[stock].close
                volume = bar_dict[stock].volume
                stock_scores[stock] = price * volume  # 简化的市值代理
            except:
                continue
        
        # 选前N只
        top_stocks = sorted(stock_scores.items(), key=lambda x: x[1], reverse=True)[:TOP_N_STOCKS_PER_INDUSTRY]
        target_stocks.extend([stock for stock, _ in top_stocks])
    
    if len(target_stocks) == 0:
        logger.warn("未找到目标股票，跳过调仓")
        return
    
    logger.info(f"目标股票: {target_stocks}")
    context.target_stocks = target_stocks
    
    # 3. 平仓非目标股票（使用 get_positions API）
    for pos in get_positions():
        stock = pos.order_book_id
        if stock not in target_stocks:
            order_target_percent(stock, 0)
            logger.info(f"平仓: {stock}")
    
    # 4. 等权配置目标股票（仅对有当日行情的标的下单，避免 No market data 刷屏）
    tradable = [s for s in target_stocks if s in bar_dict]
    try:
        tradable = [s for s in tradable if bar_dict[s].close and float(bar_dict[s].close) > 0]
    except Exception:
        pass
    if len(tradable) < len(target_stocks):
        skipped = set(target_stocks) - set(tradable)
        logger.warn(f"以下标的无有效行情，跳过下单: {skipped}")
    if not tradable:
        logger.warn("无任何可交易目标股票，跳过调仓")
        return
    weight = 1.0 / len(tradable)
    for stock in tradable:
        order_target_percent(stock, weight)
        logger.info(f"配置 {stock}: {weight*100:.2f}%")


def check_stop_loss(context, bar_dict):
    """止损检查（使用 get_positions API）"""
    for position in get_positions():
        if position.quantity == 0:
            continue
        stock = position.order_book_id
        # 持仓成本价
        cost_price = position.avg_price
        if cost_price == 0:
            continue
        
        # 当前价格
        try:
            current_price = bar_dict[stock].close
        except:
            continue
        
        # 亏损比例
        loss_ratio = (cost_price - current_price) / cost_price
        
        if loss_ratio >= STOP_LOSS_RATIO:
            order_target_percent(stock, 0)
            logger.info(f"止损卖出 {stock}: 亏损 {loss_ratio*100:.2f}%")


def after_trading(context):
    """盘后处理"""
    pass
