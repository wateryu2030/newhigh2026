#!/usr/bin/env python3
"""
修复财报采集器 - 适配 AkShare 数据格式
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "data" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "core" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "lib"))

import akshare as ak
import pandas as pd
from datetime import datetime


def test_income_statement():
    """测试利润表数据格式"""
    print("=" * 60)
    print("测试利润表数据格式")
    print("=" * 60)

    symbol = "SH600519"
    df = ak.stock_financial_abstract(symbol=symbol)

    print(f"\n数据形状：{df.shape}")
    print(f"前 5 列：{df.columns[:5].tolist()}")
    print(f"\n前 3 行数据:")
    print(df.head(3))

    # 分析数据结构
    print(f"\n数据结构分析:")
    print(f"  - 第 1 列：{df.columns[0]} (可能是指标名称)")
    print(f"  - 第 2 列：{df.columns[1]} (可能是选项)")
    print(f"  - 后续列：日期格式 (20250930, 20250630, etc.)")

    # 转换数据
    print(f"\n转换示例:")
    # 取"营业总收入"行
    if '营业总收入' in df['指标'].values:
        revenue_row = df[df['指标'] == '营业总收入'].iloc[0]
        print(f"  营业总收入 (最新): {revenue_row['20250930'] if '20250930' in df.columns else 'N/A'}")

    return df


def test_balance_sheet():
    """测试资产负债表数据格式"""
    print("\n" + "=" * 60)
    print("测试资产负债表数据格式")
    print("=" * 60)

    symbol = "SH600519"
    df = ak.stock_balance_sheet_by_report_em(symbol=symbol)

    print(f"\n数据形状：{df.shape}")
    print(f"前 20 列：{df.columns[:20].tolist()}")

    # 查找关键列
    key_columns = ['资产总计', '负债合计', '股东权益合计']
    for col in key_columns:
        if col in df.columns:
            print(f"  ✅ {col}: 第 1 行值 = {df.iloc[0].get(col, 'N/A')}")
        else:
            # 查找相似列名
            similar = [c for c in df.columns if col[:2] in c]
            if similar:
                print(f"  ⚠️ 未找到'{col}',相似列：{similar[:3]}")
            else:
                print(f"  ❌ 未找到'{col}'")

    return df


def test_cashflow():
    """测试现金流表数据格式"""
    print("\n" + "=" * 60)
    print("测试现金流表数据格式")
    print("=" * 60)

    symbol = "SH600519"
    df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)

    print(f"\n数据形状：{df.shape}")
    print(f"前 20 列：{df.columns[:20].tolist()}")

    # 查找关键列
    key_columns = ['经营活动产生的现金流量净额', '投资活动产生的现金流量净额', '筹资活动产生的现金流量净额']
    for col in key_columns:
        if col in df.columns:
            print(f"  ✅ {col}: 第 1 行值 = {df.iloc[0].get(col, 'N/A')}")
        else:
            # 查找相似列名
            similar = [c for c in df.columns if '现金流' in c or '现金' in c]
            if similar:
                print(f"  ⚠️ 未找到完整匹配，相似列：{similar[:5]}")
            else:
                print(f"  ❌ 未找到'{col}'")

    return df


def test_shareholders():
    """测试股东数据格式"""
    print("\n" + "=" * 60)
    print("测试 10 大流通股东数据格式")
    print("=" * 60)

    symbol = "SH600519"
    df = ak.stock_circulate_stock_holder(symbol=symbol)

    print(f"\n数据形状：{df.shape}")
    print(f"所有列：{df.columns.tolist()}")
    print(f"\n前 5 行数据:")
    print(df.head(5))

    return df


def create_column_mapping():
    """创建列名映射表"""
    print("\n" + "=" * 60)
    print("建议的列名映射")
    print("=" * 60)

    mapping = {
        'income': {
            '营业总收入': 'total_revenue',
            '营业利润': 'operating_profit',
            '净利润': 'net_profit',
            '基本每股收益': 'eps',
        },
        'balance': {
            '资产总计': 'total_assets',
            '负债合计': 'total_liabilities',
            '股东权益合计': 'shareholders_equity',
        },
        'cashflow': {
            '经营活动产生的现金流量净额': 'operating_cash_flow',
            '投资活动产生的现金流量净额': 'investing_cash_flow',
            '筹资活动产生的现金流量净额': 'financing_cash_flow',
        },
        'shareholders': {
            '截止日期': 'report_date',
            '编号': 'rank',
            '股东名称': 'shareholder_name',
            '持股数量': 'share_count',
            '占流通股比例': 'share_ratio',
            '股本性质': 'shareholder_type',
        }
    }

    for table, cols in mapping.items():
        print(f"\n{table}:")
        for cn, en in cols.items():
            print(f"  {cn} → {en}")

    return mapping


if __name__ == "__main__":
    print("财报采集器数据格式分析")
    print(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试各表数据格式
    test_income_statement()
    test_balance_sheet()
    test_cashflow()
    test_shareholders()

    # 创建映射表
    create_column_mapping()

    print("\n" + "=" * 60)
    print("✅ 数据分析完成!")
    print("=" * 60)
