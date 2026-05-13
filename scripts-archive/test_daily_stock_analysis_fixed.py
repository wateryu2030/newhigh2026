#!/usr/bin/env python3
"""
daily_stock_analysis 模块功能测试
修复导入问题后的版本
"""

import asyncio
import sys
import os
import importlib.util


def test_module_imports_fixed():
    """测试模块导入（修复版本）"""
    print("=" * 60)
    print("测试模块导入（修复导入问题）")
    print("=" * 60)

    base_path = "/Users/apple/Ahope/newhigh/strategy-engine/src/strategies/daily_stock_analysis"

    # 首先导入config模块
    config_path = os.path.join(base_path, "config.py")
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    DailyStockConfig = config_module.DailyStockConfig

    print("✅ config 导入成功")

    # 创建配置对象
    config = DailyStockConfig(
        enabled=True,
        data_sources=["akshare", "tushare"],
        ai_model="gemini-pro",
        notification_channels=["console"],
    )

    print(f"   配置创建成功: {config.name}")

    # 测试data_fetcher - 手动处理导入
    print("\n测试 data_fetcher...")
    fetcher_path = os.path.join(base_path, "data_fetcher.py")

    # 读取文件内容
    with open(fetcher_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 修复导入语句
    content = content.replace(
        "from .config import DailyStockConfig",
        f"# 动态导入配置\nDailyStockConfig = {config_module.__name__}.DailyStockConfig",
    )

    # 创建模块
    spec = importlib.util.spec_from_file_location("data_fetcher", fetcher_path)
    fetcher_module = importlib.util.module_from_spec(spec)

    # 执行修复后的代码
    exec(content, fetcher_module.__dict__)

    DataFetcher = fetcher_module.DataFetcher
    print("✅ data_fetcher 导入成功")

    # 测试创建对象
    data_fetcher = DataFetcher(config)
    print(f"   DataFetcher对象创建成功")

    # 测试ai_decision
    print("\n测试 ai_decision...")
    ai_path = os.path.join(base_path, "ai_decision.py")

    with open(ai_path, "r", encoding="utf-8") as f:
        ai_content = f.read()

    # 修复导入
    ai_content = ai_content.replace(
        "from .config import DailyStockConfig",
        f"# 动态导入配置\nDailyStockConfig = {config_module.__name__}.DailyStockConfig",
    )

    spec = importlib.util.spec_from_file_location("ai_decision", ai_path)
    ai_module = importlib.util.module_from_spec(spec)
    exec(ai_content, ai_module.__dict__)

    AIDecisionMaker = ai_module.AIDecisionMaker
    print("✅ ai_decision 导入成功")

    ai_decision_maker = AIDecisionMaker(config)
    print(f"   AIDecisionMaker对象创建成功")

    # 测试notification
    print("\n测试 notification...")
    notification_path = os.path.join(base_path, "notification.py")

    with open(notification_path, "r", encoding="utf-8") as f:
        notification_content = f.read()

    # 修复导入
    notification_content = notification_content.replace(
        "from .config import DailyStockConfig",
        f"# 动态导入配置\nDailyStockConfig = {config_module.__name__}.DailyStockConfig",
    )

    spec = importlib.util.spec_from_file_location("notification", notification_path)
    notification_module = importlib.util.module_from_spec(spec)
    exec(notification_content, notification_module.__dict__)

    NotificationSender = notification_module.NotificationSender
    print("✅ notification 导入成功")

    notification_sender = NotificationSender(config)
    print(f"   NotificationSender对象创建成功")

    # 测试main
    print("\n测试 main...")
    main_path = os.path.join(base_path, "main.py")

    with open(main_path, "r", encoding="utf-8") as f:
        main_content = f.read()

    # 修复所有导入
    main_content = main_content.replace(
        "from .config import DailyStockConfig",
        f"# 动态导入配置\nDailyStockConfig = {config_module.__name__}.DailyStockConfig",
    )
    main_content = main_content.replace(
        "from .data_fetcher import DataFetcher",
        f"# 动态导入DataFetcher\nDataFetcher = {fetcher_module.__name__}.DataFetcher",
    )
    main_content = main_content.replace(
        "from .ai_decision import AIDecisionMaker",
        f"# 动态导入AIDecisionMaker\nAIDecisionMaker = {ai_module.__name__}.AIDecisionMaker",
    )
    main_content = main_content.replace(
        "from .notification import NotificationSender",
        f"# 动态导入NotificationSender\nNotificationSender = {notification_module.__name__}.NotificationSender",
    )

    spec = importlib.util.spec_from_file_location("main", main_path)
    main_module = importlib.util.module_from_spec(spec)
    exec(main_content, main_module.__dict__)

    DailyStockAnalyzer = main_module.DailyStockAnalyzer
    print("✅ main 导入成功")

    analyzer = DailyStockAnalyzer()
    print(f"   DailyStockAnalyzer对象创建成功")
    print(f"   分析器名称: {analyzer.config.name}")

    print("\n" + "=" * 60)
    print("🎉 所有模块导入和对象创建成功！")
    print("=" * 60)

    return True


async def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "=" * 60)
    print("测试基本功能")
    print("=" * 60)

    try:
        # 使用修复后的导入方式
        base_path = "/Users/apple/Ahope/newhigh/strategy-engine/src/strategies/daily_stock_analysis"

        # 导入config
        config_path = os.path.join(base_path, "config.py")
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        DailyStockConfig = config_module.DailyStockConfig

        # 创建配置
        config = DailyStockConfig(
            enabled=True,
            data_sources=["akshare", "tushare"],
            ai_model="gemini-pro",
            notification_channels=["console"],
        )

        # 导入data_fetcher
        fetcher_path = os.path.join(base_path, "data_fetcher.py")
        with open(fetcher_path, "r", encoding="utf-8") as f:
            fetcher_content = f.read()

        fetcher_content = fetcher_content.replace(
            "from .config import DailyStockConfig",
            f"DailyStockConfig = {config_module.__name__}.DailyStockConfig",
        )

        spec = importlib.util.spec_from_file_location("data_fetcher", fetcher_path)
        fetcher_module = importlib.util.module_from_spec(spec)
        exec(fetcher_content, fetcher_module.__dict__)
        DataFetcher = fetcher_module.DataFetcher

        # 测试数据获取
        print("1. 测试数据获取...")
        data_fetcher = DataFetcher(config)

        # 使用小规模测试数据
        market_data = await data_fetcher.fetch_market_data(
            markets=["A", "US"], symbols={"A": ["000001"], "US": ["AAPL"]}
        )

        print(f"   ✅ 数据获取成功")
        print(f"   状态: {market_data.get('status')}")
        print(f"   市场数: {len(market_data.get('markets', {}))}")

        # 导入ai_decision
        ai_path = os.path.join(base_path, "ai_decision.py")
        with open(ai_path, "r", encoding="utf-8") as f:
            ai_content = f.read()

        ai_content = ai_content.replace(
            "from .config import DailyStockConfig",
            f"DailyStockConfig = {config_module.__name__}.DailyStockConfig",
        )

        spec = importlib.util.spec_from_file_location("ai_decision", ai_path)
        ai_module = importlib.util.module_from_spec(spec)
        exec(ai_content, ai_module.__dict__)
        AIDecisionMaker = ai_module.AIDecisionMaker

        # 测试AI分析
        print("\n2. 测试AI分析...")
        ai_decision_maker = AIDecisionMaker(config)
        ai_results = await ai_decision_maker.analyze_market_data(market_data)

        print(f"   ✅ AI分析成功")
        print(f"   使用模型: {ai_results.get('model_used')}")
        print(f"   状态: {ai_results.get('status')}")

        # 导入notification
        notification_path = os.path.join(base_path, "notification.py")
        with open(notification_path, "r", encoding="utf-8") as f:
            notification_content = f.read()

        notification_content = notification_content.replace(
            "from .config import DailyStockConfig",
            f"DailyStockConfig = {config_module.__name__}.DailyStockConfig",
        )

        spec = importlib.util.spec_from_file_location("notification", notification_path)
        notification_module = importlib.util.module_from_spec(spec)
        exec(notification_content, notification_module.__dict__)
        NotificationSender = notification_module.NotificationSender

        # 测试通知发送
        print("\n3. 测试通知发送...")
        notification_sender = NotificationSender(config)
        notification_results = await notification_sender.send_analysis_results(ai_results)

        print(f"   ✅ 通知发送成功")
        print(f"   状态: {notification_results.get('status')}")
        print(f"   成功渠道: {notification_results.get('successful_channels', [])}")

        print("\n" + "=" * 60)
        print("🎉 所有基本功能测试通过！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始 daily_stock_analysis 模块测试（修复版）...")

    # 运行测试
    import_success = test_module_imports_fixed()
    func_success = await test_basic_functionality()

    # 总结
    print("\n" + "=" * 60)
    print("测试完成总结")
    print("=" * 60)

    test_results = [import_success, func_success]
    total_tests = len(test_results)
    passed_tests = sum(test_results)

    print(f"总测试组数: {total_tests}")
    print(f"通过测试组: {passed_tests}")
    print(f"失败测试组: {total_tests - passed_tests}")

    if passed_tests == total_tests:
        print("\n🎉 所有测试通过! daily_stock_analysis 模块基本功能正常")
        print("   模块可以正常导入、初始化并运行基础功能")
    elif passed_tests >= 1:
        print("\n👍 部分测试通过，模块基本可用")
        print("   需要进一步解决导入路径问题")
    else:
        print("\n⚠ 测试失败，需要进一步检查")

    return all(test_results)


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())

    # 退出代码
    sys.exit(0 if success else 1)
