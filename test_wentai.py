#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闻泰科技数据获取测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from akshare.stock_feature.stock_hist_em import stock_zh_a_hist
import pandas as pd

def test_wentai_data():
    """测试获取闻泰科技数据"""
    print("=" * 50)
    print("闻泰科技（600745）数据获取测试")
    print("=" * 50)
    
    try:
        # 获取2024年数据
        df = stock_zh_a_hist(
            symbol="600745",
            period="daily",
            start_date="20240101",
            end_date="20241231",
            adjust="qfq"  # 前复权
        )
        
        if df is None or len(df) == 0:
            print("❌ 未获取到数据")
            return False
        
        print(f"✅ 数据获取成功！")
        print(f"数据条数: {len(df)}")
        print(f"\n最新5条数据:")
        print(df.head())
        print(f"\n数据统计:")
        print(df.describe())
        
        # 保存到CSV
        output_file = "data/wentai_600745_2024.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n✅ 数据已保存到: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_wentai_data()
