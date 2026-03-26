#!/usr/bin/env python3
"""
财报采集器快速测试

测试 AkShare API 并映射列名
"""

import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "data" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "core" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "lib"))

import akshare as ak
import pandas as pd


def test_api():
    """测试 AkShare API"""
    symbol = "SH600519"  # 贵州茅台

    print("=" * 60)
    print(f"测试 AkShare API ({symbol})")
    print("=" * 60)

    # 1. 利润表
    print("\n1. 利润表 (stock_financial_abstract)...")
    try:
        income = ak.stock_financial_abstract(symbol=symbol)
        print(f"   ✅ 成功，{len(income)} 行，{len(income.columns)} 列")
        print(f"   列名：{income.columns.tolist()[:15]}")
        if not income.empty:
            print(f"   最新数据：营业总收入={income.iloc[0].get('营业总收入', 'N/A')}")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    # 2. 资产负债表
    print("\n2. 资产负债表 (stock_balance_sheet_by_report_em)...")
    try:
        balance = ak.stock_balance_sheet_by_report_em(symbol=symbol)
        print(f"   ✅ 成功，{len(balance)} 行，{len(balance.columns)} 列")
        if not balance.empty:
            print(f"   资产总计={balance.iloc[0].get('资产总计', 'N/A')}")
            print(f"   负债合计={balance.iloc[0].get('负债合计', 'N/A')}")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    # 3. 现金流表
    print("\n3. 现金流表 (stock_cash_flow_sheet_by_report_em)...")
    try:
        cashflow = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        print(f"   ✅ 成功，{len(cashflow)} 行，{len(cashflow.columns)} 列")
        if not cashflow.empty:
            print(f"   经营现金流={cashflow.iloc[0].get('经营活动产生的现金流量净额', 'N/A')}")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    # 4. 10 大流通股东
    print("\n4. 10 大流通股东 (stock_circulate_stock_holder)...")
    try:
        holders = ak.stock_circulate_stock_holder(symbol=symbol)
        print(f"   ✅ 成功，{len(holders)} 行")
        print(f"   列名：{holders.columns.tolist()}")
        if not holders.empty:
            print(f"   前 3 大股东:")
            for i, row in holders.head(3).iterrows():
                print(f"      {row.get('编号', i+1)}. {row.get('股东名称', 'N/A')} - {row.get('持股数量', 'N/A')}股")
    except Exception as e:
        print(f"   ❌ 失败：{e}")

    print("\n" + "=" * 60)


def test_collector():
    """测试采集器"""
    from data.collectors.financial_report import FinancialReportCollector

    print("\n" + "=" * 60)
    print("测试 FinancialReportCollector")
    print("=" * 60)

    collector = FinancialReportCollector()

    # 测试贵州茅台
    print("\n采集 600519 (贵州茅台)...")
    result = collector.collect_single_stock("600519")
    print(f"结果：{result}")

    # 验证数据库
    from lib.database import get_connection
    conn = get_connection(read_only=False)

    print("\n数据库验证:")
    df = conn.execute("SELECT COUNT(*) FROM financial_report").fetchone()
    print(f"  财报记录总数：{df[0]}")

    df = conn.execute("SELECT COUNT(*) FROM top_10_shareholders").fetchone()
    print(f"  股东记录总数：{df[0]}")

    if df[0] > 0:
        print("\n  前 3 条股东记录:")
        df = conn.execute("""
            SELECT stock_code, rank, shareholder_name, share_count
            FROM top_10_shareholders
            ORDER BY stock_code, rank
            LIMIT 3
        """).fetchdf()
        print(df.to_string())

    conn.close()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true", help="只测试 API")
    parser.add_argument("--collector", action="store_true", help="测试采集器")
    args = parser.parse_args()

    if args.api:
        test_api()
    elif args.collector:
        test_collector()
    else:
        test_api()
        test_collector()
