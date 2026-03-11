#!/usr/bin/env python3
"""
Tushare数据获取演示脚本
演示如何在量化平台中使用Tushare连接器
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_basic_usage():
    """演示基本用法"""
    print("=" * 60)
    print("Tushare数据获取演示")
    print("=" * 60)
    
    # 检查环境变量
    token = os.getenv('TUSHARE_TOKEN')
    if not token:
        print("错误: 未设置TUSHARE_TOKEN环境变量")
        print("请设置: export TUSHARE_TOKEN='你的token'")
        print("获取token: https://tushare.pro")
        return
    
    print(f"✓ 找到TUSHARE_TOKEN环境变量")
    
    try:
        # 导入Tushare连接器
        from data_engine.src.data_engine import connector_tushare as tushare
        
        print("\n1. 测试Tushare连接器...")
        if tushare.test_tushare_connector():
            print("✓ Tushare连接器测试通过")
        else:
            print("✗ Tushare连接器测试失败")
            return
        
        print("\n2. 获取股票基本信息示例...")
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            
            # 获取平安银行基本信息
            df = pro.stock_basic(ts_code='000001.SZ', fields='ts_code,name,industry,list_date,market')
            if not df.empty:
                stock_info = df.iloc[0]
                print(f"  代码: {stock_info['ts_code']}")
                print(f"  名称: {stock_info['name']}")
                print(f"  行业: {stock_info['industry']}")
                print(f"  上市日期: {stock_info['list_date']}")
                print(f"  市场: {stock_info['market']}")
                print("✓ 股票信息获取成功")
        except Exception as e:
            print(f"✗ 获取股票信息失败: {e}")
        
        print("\n3. 获取日线数据示例...")
        try:
            # 计算日期
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            # 使用连接器获取数据
            ohlcv_list = tushare.fetch_ohlcv(
                code='000001',
                start_date=start_date,
                end_date=end_date,
                period='daily'
            )
            
            if ohlcv_list:
                print(f"  获取到 {len(ohlcv_list)} 条日线数据")
                latest = ohlcv_list[0]  # 最新数据在前
                print(f"  最新数据: {latest.timestamp.date()} 收盘价: {latest.close:.2f} 成交量: {latest.volume:,.0f}")
                print("✓ 日线数据获取成功")
            else:
                print("✗ 未获取到日线数据")
        except Exception as e:
            print(f"✗ 获取日线数据失败: {e}")
        
        print("\n4. 批量获取多只股票数据示例...")
        try:
            stocks = ['000001', '000002', '600000']  # 平安银行, 万科A, 浦发银行
            
            for stock in stocks:
                try:
                    ohlcv_list = tushare.fetch_ohlcv(
                        code=stock,
                        start_date='20240101',
                        end_date='20240131',
                        period='daily'
                    )
                    if ohlcv_list:
                        latest = ohlcv_list[0]
                        print(f"  {stock}: 1月最新收盘价 {latest.close:.2f}, 成交量 {latest.volume:,.0f}")
                except Exception as e:
                    print(f"  {stock}: 获取失败 - {e}")
        except Exception as e:
            print(f"✗ 批量获取失败: {e}")
        
        print("\n5. 财务数据示例...")
        try:
            # 获取利润表数据
            df = tushare.fetch_financial_data(
                code='000001',
                report_type='income',
                start_date='20230101',
                end_date='20231231'
            )
            if not df.empty:
                print(f"  获取到 {len(df)} 条利润表数据")
                print(f"  最新报表日期: {df.iloc[0]['end_date']}")
                print("✓ 财务数据获取成功")
        except Exception as e:
            print(f"✗ 获取财务数据失败: {e}")
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        
        print("\n下一步建议:")
        print("1. 在data-engine中集成Tushare连接器")
        print("2. 创建定时任务自动获取数据")
        print("3. 将Tushare数据与其他数据源结合分析")
        print("4. 开发基于Tushare数据的策略")
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装tushare: pip install tushare")
    except Exception as e:
        print(f"演示过程中出错: {e}")


def integration_guide():
    """集成指南"""
    print("\n" + "=" * 60)
    print("Tushare集成指南")
    print("=" * 60)
    
    print("\n1. 环境配置:")
    print("   export TUSHARE_TOKEN='你的token'")
    print("   pip install tushare pandas")
    
    print("\n2. 在项目中导入:")
    print("   from data_engine.src.data_engine import connector_tushare as tushare")
    
    print("\n3. 基本使用:")
    print("   # 获取日线数据")
    print("   data = tushare.fetch_ohlcv('000001', '20240101', '20240131', 'daily')")
    
    print("\n4. 数据管道集成:")
    print("   # 在data_pipeline.py中添加Tushare数据源")
    print("   from data_engine.src.data_engine.connector_tushare import fetch_ohlcv")
    
    print("\n5. 定时任务配置:")
    print("   # 创建定时获取任务")
    print("   # 每天收盘后获取最新数据")
    
    print("\n6. 数据存储:")
    print("   # 使用现有存储系统（ClickHouse/DuckDB）")
    print("   # 或直接使用Tushare缓存")


if __name__ == "__main__":
    demo_basic_usage()
    integration_guide()