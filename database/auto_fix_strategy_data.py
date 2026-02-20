#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动补齐策略所需数据文件
检查策略需要的数据文件，如果缺失则自动生成
"""
import os
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ensure_data_files(strategy_file, stock_code=None):
    """
    确保策略所需的数据文件存在，如果缺失则自动生成
    
    Args:
        strategy_file: 策略文件路径
        stock_code: 用户选择的股票代码（可选，用于确保股票在股票池中）
    
    Returns:
        list: 缺失的文件列表（已补齐则返回空列表）
    """
    missing_files = []
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    strategy_name = os.path.basename(strategy_file)
    
    # 策略1：行业轮动
    if "strategy1_industry_rotation" in strategy_name:
        files_needed = {
            "industry_stock_map.csv": create_industry_stock_map,
            "industry_score.csv": create_industry_score,
        }
        for filename, creator in files_needed.items():
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath) or os.path.getsize(filepath) < 50:
                print(f"生成缺失文件: {filename}")
                creator(filepath)
                missing_files.append(filename)
        # 用户选择的股票加入行业映射，确保回测能选中该股票
        if stock_code:
            industry_map_path = os.path.join(data_dir, "industry_stock_map.csv")
            add_stock_to_industry_map(industry_map_path, stock_code)
    
    # 策略2：动量+均值回归
    elif "strategy2_momentum_meanreversion" in strategy_name:
        files_needed = {
            "tech_leader_stocks.csv": create_tech_leader_stocks,
            "consume_leader_stocks.csv": create_consume_leader_stocks,
        }
        for filename, creator in files_needed.items():
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath) or os.path.getsize(filepath) < 50:
                print(f"生成缺失文件: {filename}")
                creator(filepath)
                missing_files.append(filename)
        
        # 如果用户选择了股票，确保它在对应的股票池中
        if stock_code:
            symbol = stock_code.split(".")[0] if "." in stock_code else stock_code
            # 判断是高科技还是消费（简化：6开头通常是上交所，0/3开头通常是深交所，这里简化处理）
            if symbol.startswith("6") or symbol.startswith("0"):
                # 检查是否在高科技或消费股票池中
                tech_file = os.path.join(data_dir, "tech_leader_stocks.csv")
                consume_file = os.path.join(data_dir, "consume_leader_stocks.csv")
                add_stock_to_pool(tech_file, stock_code, "高科技")
                add_stock_to_pool(consume_file, stock_code, "消费")
    
    # 策略3：财报超预期（与策略2共用股票池，并确保用户股票在池中）
    elif "strategy3_earnings_surprise" in strategy_name:
        files_needed = {
            "tech_leader_stocks.csv": create_tech_leader_stocks,
            "consume_leader_stocks.csv": create_consume_leader_stocks,
            "earnings_events.csv": create_earnings_events,
        }
        for filename, creator in files_needed.items():
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath) or os.path.getsize(filepath) < 50:
                print(f"生成缺失文件: {filename}")
                creator(filepath)
                missing_files.append(filename)
        if stock_code:
            add_stock_to_pool(os.path.join(data_dir, "tech_leader_stocks.csv"), stock_code, "高科技")
            add_stock_to_pool(os.path.join(data_dir, "consume_leader_stocks.csv"), stock_code, "消费")
    
    # 策略4：ETF网格
    elif "strategy4_etf_grid" in strategy_name:
        files_needed = {
            "etf_list.csv": create_etf_list,
        }
        for filename, creator in files_needed.items():
            filepath = os.path.join(data_dir, filename)
            if not os.path.exists(filepath) or os.path.getsize(filepath) < 50:
                print(f"生成缺失文件: {filename}")
                creator(filepath)
                missing_files.append(filename)
    
    return missing_files


def create_industry_stock_map(filepath):
    """创建行业-股票映射表"""
    data = {
        "代码": [
            "600745.XSHG",  # 闻泰科技
            "000001.XSHE",  # 平安银行
            "600519.XSHG",  # 贵州茅台
            "000858.XSHE",  # 五粮液
        ],
        "行业名称": [
            "半导体",
            "半导体",
            "食品饮料",
            "食品饮料",
        ]
    }
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"✅ 已创建: {filepath}")


def create_industry_score(filepath):
    """创建行业评分表"""
    data = {
        "行业名称": ["半导体", "食品饮料"],
        "景气度得分": [60, 55],
        "资金流得分": [55, 60],
        "综合得分": [58, 57],
    }
    df = pd.DataFrame(data)
    df.set_index("行业名称", inplace=True)
    df.to_csv(filepath, encoding="utf-8-sig")
    print(f"✅ 已创建: {filepath}")


def create_tech_leader_stocks(filepath):
    """创建高科技龙头股票池"""
    # 包含数据库中已有的股票，以及常见的高科技股票
    data = {
        "代码": [
            "600745.XSHG",  # 闻泰科技
            "002701.XSHE",  # 奥瑞金
            "000001.XSHE",  # 平安银行（示例）
        ],
        "名称": [
            "闻泰科技",
            "奥瑞金",
            "平安银行",
        ]
    }
    # 如果文件已存在，读取并合并，避免覆盖用户数据
    if os.path.exists(filepath):
        try:
            existing_df = pd.read_csv(filepath, encoding="utf-8-sig")
            existing_codes = set(existing_df["代码"].tolist() if "代码" in existing_df.columns else [])
            new_codes = set(data["代码"])
            if not new_codes.issubset(existing_codes):
                # 合并新旧数据
                combined_codes = list(existing_codes | new_codes)
                combined_names = []
                for code in combined_codes:
                    if code in existing_df["代码"].values:
                        name = existing_df[existing_df["代码"] == code]["名称"].iloc[0]
                    else:
                        name = data["名称"][data["代码"].index(code)]
                    combined_names.append(name)
                data = {"代码": combined_codes, "名称": combined_names}
        except Exception:
            pass  # 如果读取失败，使用新数据
    
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"✅ 已创建/更新: {filepath}")


def create_consume_leader_stocks(filepath):
    """创建消费龙头股票池"""
    data = {
        "代码": [
            "600519.XSHG",  # 贵州茅台
            "000858.XSHE",  # 五粮液
            "002304.XSHE",  # 洋河股份（示例）
        ],
        "名称": [
            "贵州茅台",
            "五粮液",
            "洋河股份",
        ]
    }
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"✅ 已创建: {filepath}")


def create_earnings_events(filepath):
    """创建财报事件表（简化版）"""
    data = {
        "股票代码": ["600745.XSHG"],
        "事件日期": ["2024-01-01"],
        "事件类型": ["营收超预期"],
    }
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"✅ 已创建: {filepath}")


def create_etf_list(filepath):
    """创建ETF列表"""
    data = {
        "代码": [
            "515050.XSHG",  # 5G ETF（示例）
            "159928.XSHE",  # 消费ETF（示例）
        ],
        "名称": [
            "5G ETF",
            "消费ETF",
        ]
    }
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"✅ 已创建: {filepath}")


def add_stock_to_industry_map(filepath, stock_code):
    """将股票加入行业-股票映射表（代码+行业名称格式），便于策略1能选中该股票"""
    if not os.path.exists(filepath):
        return
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        if "代码" not in df.columns or "行业名称" not in df.columns:
            return
        if stock_code in df["代码"].values:
            return
        # 取第一个已有行业，或默认「半导体」
        industry = df["行业名称"].iloc[0] if len(df) > 0 else "半导体"
        new_row = pd.DataFrame({"代码": [stock_code], "行业名称": [industry]})
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"✅ 已将 {stock_code} 加入行业映射表（{industry}）")
    except Exception as e:
        print(f"⚠️  添加股票到行业映射表失败: {e}")


def add_stock_to_pool(filepath, stock_code, pool_name):
    """将股票添加到股票池（如果不存在）"""
    if not os.path.exists(filepath):
        return
    
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        if "代码" not in df.columns:
            return
        
        if stock_code not in df["代码"].values:
            # 从数据库获取股票名称
            try:
                from database.db_schema import StockDatabase
                db = StockDatabase()
                stocks = db.get_stocks()
                stock_name = None
                for ob, sym, name in stocks:
                    if ob == stock_code:
                        stock_name = name or sym
                        break
                if not stock_name:
                    stock_name = stock_code.split(".")[0]
            except Exception:
                stock_name = stock_code.split(".")[0]
            
            # 添加到股票池
            new_row = pd.DataFrame({"代码": [stock_code], "名称": [stock_name]})
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            print(f"✅ 已将 {stock_code} 添加到{pool_name}股票池")
    except Exception as e:
        print(f"⚠️  添加股票到{pool_name}股票池失败: {e}")


if __name__ == "__main__":
    # 测试：补齐所有策略的数据文件
    strategies = [
        "strategies/strategy1_industry_rotation.py",
        "strategies/strategy2_momentum_meanreversion.py",
        "strategies/strategy3_earnings_surprise.py",
        "strategies/strategy4_etf_grid.py",
    ]
    for strategy in strategies:
        if os.path.exists(strategy):
            print(f"\n检查 {strategy}:")
            missing = ensure_data_files(strategy)
            if not missing:
                print("  所有数据文件已存在")
