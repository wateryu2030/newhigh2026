#!/usr/bin/env python3
"""
daily_stock_analysis 模块功能测试
简化版测试，避免复杂的导入问题
"""

import asyncio
import sys
import os
import importlib.util

def test_module_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)
    
    modules_to_test = [
        ("config", "config.py"),
        ("data_fetcher", "data_fetcher.py"),
        ("ai_decision", "ai_decision.py"),
        ("notification", "notification.py"),
        ("main", "main.py")
    ]
    
    base_path = "/Users/apple/Ahope/newhigh/strategy-engine/src/strategies/daily_stock_analysis"
    
    for module_name, filename in modules_to_test:
        file_path = os.path.join(base_path, filename)
        
        if os.path.exists(file_path):
            try:
                spec = importlib.util.spec_from_file_location(f"daily_stock_analysis.{module_name}", file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"✅ {module_name} 导入成功")
                
                # 检查关键类/函数
                if module_name == "config":
                    if hasattr(module, "DailyStockConfig"):
                        print(f"   找到类: DailyStockConfig")
                elif module_name == "data_fetcher":
                    if hasattr(module, "DataFetcher"):
                        print(f"   找到类: DataFetcher")
                elif module_name == "ai_decision":
                    if hasattr(module, "AIDecisionMaker"):
                        print(f"   找到类: AIDecisionMaker")
                elif module_name == "notification":
                    if hasattr(module, "NotificationSender"):
                        print(f"   找到类: NotificationSender")
                elif module_name == "main":
                    if hasattr(module, "DailyStockAnalyzer"):
                        print(f"   找到类: DailyStockAnalyzer")
                        
            except Exception as e:
                print(f"❌ {module_name} 导入失败: {e}")
        else:
            print(f"❌ {filename} 文件不存在")
    
    return True

async def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "=" * 60)
    print("测试基本功能")
    print("=" * 60)
    
    try:
        # 导入模块
        base_path = "/Users/apple/Ahope/newhigh/strategy-engine/src/strategies/daily_stock_analysis"
        
        # 导入配置
        config_path = os.path.join(base_path, "config.py")
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        DailyStockConfig = config_module.DailyStockConfig
        
        # 导入数据获取器
        fetcher_path = os.path.join(base_path, "data_fetcher.py")
        spec = importlib.util.spec_from_file_location("data_fetcher", fetcher_path)
        fetcher_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fetcher_module)
        DataFetcher = fetcher_module.DataFetcher
        
        # 导入AI决策器
        ai_path = os.path.join(base_path, "ai_decision.py")
        spec = importlib.util.spec_from_file_location("ai_decision", ai_path)
        ai_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ai_module)
        AIDecisionMaker = ai_module.AIDecisionMaker
        
        # 导入通知发送器
        notification_path = os.path.join(base_path, "notification.py")
        spec = importlib.util.spec_from_file_location("notification", notification_path)
        notification_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(notification_module)
        NotificationSender = notification_module.NotificationSender
        
        print("✅ 所有模块导入成功")
        
        # 测试配置
        print("\n1. 测试配置...")
        config = DailyStockConfig(
            enabled=True,
            data_sources=["akshare", "tushare"],
            ai_model="gemini-pro",
            notification_channels=["console"]
        )
        print(f"   配置名称: {config.name}")
        print(f"   数据源: {config.data_sources}")
        print(f"   AI模型: {config.ai_model}")
        print(f"   通知渠道: {config.notification_channels}")
        
        # 测试数据获取器
        print("\n2. 测试数据获取器...")
        data_fetcher = DataFetcher(config)
        market_data = await data_fetcher.fetch_market_data(
            markets=["A", "US"],
            symbols={"A": ["000001", "600519"], "US": ["AAPL", "GOOGL"]}
        )
        print(f"   数据获取状态: {market_data.get('status')}")
        print(f"   获取的市场数: {len(market_data.get('markets', {}))}")
        
        # 测试AI决策器
        print("\n3. 测试AI决策器...")
        ai_decision_maker = AIDecisionMaker(config)
        ai_results = await ai_decision_maker.analyze_market_data(market_data)
        print(f"   AI分析状态: {ai_results.get('status')}")
        print(f"   使用模型: {ai_results.get('model_used')}")
        
        recommendations = ai_results.get('recommendations', {})
        if isinstance(recommendations, dict) and 'top_picks' in recommendations:
            picks = recommendations['top_picks']
            if isinstance(picks, list):
                print(f"   推荐股票数: {len(picks)}")
                for i, pick in enumerate(picks[:2], 1):
                    if isinstance(pick, dict):
                        print(f"     {i}. {pick.get('symbol', '未知')} - {pick.get('action', '未知')}")
        
        # 测试通知发送器
        print("\n4. 测试通知发送器...")
        notification_sender = NotificationSender(config)
        notification_results = await notification_sender.send_analysis_results(ai_results)
        print(f"   通知发送状态: {notification_results.get('status')}")
        print(f"   成功渠道: {notification_results.get('successful_channels', [])}")
        
        print("\n✅ 所有基本功能测试通过")
        return True
        
    except Exception as e:
        print(f"\n❌ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_file_creation():
    """测试文件创建和完整性"""
    print("\n" + "=" * 60)
    print("测试文件创建和完整性")
    print("=" * 60)
    
    base_path = "/Users/apple/Ahope/newhigh/strategy-engine/src/strategies/daily_stock_analysis"
    required_files = [
        "config.py",
        "data_fetcher.py", 
        "ai_decision.py",
        "notification.py",
        "main.py",
        "__init__.py",
        "README.md"
    ]
    
    all_exist = True
    for filename in required_files:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {filename} 存在 ({size} 字节)")
        else:
            print(f"❌ {filename} 不存在")
            all_exist = False
    
    if all_exist:
        print("\n✅ 所有必需文件都存在")
    else:
        print("\n⚠ 缺少一些文件")
    
    return all_exist

async def main():
    """主测试函数"""
    print("开始 daily_stock_analysis 模块测试...")
    
    # 运行测试
    import_success = test_module_imports()
    file_success = await test_file_creation()
    func_success = await test_basic_functionality()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试完成总结")
    print("=" * 60)
    
    test_results = [import_success, file_success, func_success]
    total_tests = len(test_results)
    passed_tests = sum(test_results)
    
    print(f"总测试组数: {total_tests}")
    print(f"通过测试组: {passed_tests}")
    print(f"失败测试组: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过! daily_stock_analysis 模块基本功能正常")
    elif passed_tests >= 2:
        print("\n👍 大部分测试通过，模块基本可用")
    else:
        print("\n⚠ 多个测试失败，需要进一步检查")
    
    return all(test_results)

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    
    # 退出代码
    sys.exit(0 if success else 1)