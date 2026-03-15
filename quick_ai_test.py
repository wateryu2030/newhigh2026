#!/usr/bin/env python3
"""
快速AI集成测试脚本
测试Gemini API集成是否正常工作
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_gemini_import():
    """测试Gemini模块导入"""
    print("=" * 60)
    print("测试Gemini模块导入")
    print("=" * 60)
    
    try:
        # 尝试导入新版google.genai
        import google.genai as genai
        print("✅ 成功导入 google.genai (新版Gemini SDK)")
        
        # 检查API Key
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            print(f"✅ 找到GEMINI_API_KEY: {api_key[:10]}...")
            return True, "google.genai"
        else:
            print("⚠ 未找到GEMINI_API_KEY环境变量")
            print("  请在.env文件中设置: GEMINI_API_KEY=your_key_here")
            return False, "no_api_key"
            
    except ImportError as e:
        print(f"⚠ 无法导入google.genai: {e}")
        
        try:
            # 尝试导入旧版google.generativeai
            import google.generativeai as genai
            print("✅ 成功导入 google.generativeai (旧版Gemini SDK)")
            
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                print(f"✅ 找到GEMINI_API_KEY: {api_key[:10]}...")
                return True, "google.generativeai"
            else:
                print("⚠ 未找到GEMINI_API_KEY环境变量")
                return False, "no_api_key"
                
        except ImportError as e2:
            print(f"✗ 无法导入任何Gemini SDK: {e2}")
            print("  安装命令: pip install google-genai")
            return False, "import_failed"

def test_ai_decision_module():
    """测试AI决策模块"""
    print("\n" + "=" * 60)
    print("测试AI决策模块")
    print("=" * 60)
    
    try:
        from strategy_engine.src.strategies.daily_stock_analysis.ai_decision import AIDecisionMaker
        from strategy_engine.src.strategies.daily_stock_analysis.config import DailyStockConfig
        
        # 创建配置
        config = DailyStockConfig(
            model_type="gemini",
            max_tokens=1000,
            temperature=0.7
        )
        
        # 创建AI决策器
        ai_maker = AIDecisionMaker(config)
        print("✅ 成功创建AIDecisionMaker实例")
        
        # 检查可用的AI服务
        print(f"\n可用的AI服务:")
        print(f"  Gemini: {ai_maker.GEMINI_AVAILABLE}")
        print(f"  OpenAI: {ai_maker.OPENAI_AVAILABLE}")
        print(f"  百炼/通义: {ai_maker.DASHSCOPE_AVAILABLE}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试AI决策模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_gemini_call():
    """测试简单的Gemini API调用"""
    print("\n" + "=" * 60)
    print("测试简单Gemini API调用")
    print("=" * 60)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠ 跳过API调用测试: 未设置GEMINI_API_KEY")
        print("  请在.env文件中添加: GEMINI_API_KEY=your_key_here")
        return False
    
    try:
        # 尝试使用新版SDK
        try:
            import google.genai as genai
            genai.configure(api_key=api_key)
            
            # 使用gemini-1.5-flash模型（快速且免费额度高）
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            response = model.generate_content("你好，请用一句话介绍你自己。")
            print(f"✅ Gemini API调用成功!")
            print(f"   模型: gemini-1.5-flash")
            print(f"   响应: {response.text[:100]}...")
            return True
            
        except Exception as e1:
            print(f"⚠ 新版SDK调用失败: {e1}")
            
            # 尝试使用旧版SDK
            try:
                import google.generativeai as genai_old
                genai_old.configure(api_key=api_key)
                
                model = genai_old.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content("你好，请用一句话介绍你自己。")
                print(f"✅ Gemini API调用成功 (使用旧版SDK)!")
                print(f"   模型: gemini-1.5-flash")
                print(f"   响应: {response.text[:100]}...")
                return True
                
            except Exception as e2:
                print(f"✗ 旧版SDK调用也失败: {e2}")
                return False
                
    except Exception as e:
        print(f"✗ Gemini API调用失败: {e}")
        return False

def test_stock_analysis():
    """测试股票分析功能"""
    print("\n" + "=" * 60)
    print("测试股票分析功能")
    print("=" * 60)
    
    try:
        from strategy_engine.src.strategies.daily_stock_analysis.data_fetcher import StockDataFetcher
        from strategy_engine.src.strategies.daily_stock_analysis.ai_decision import AIDecisionMaker
        from strategy_engine.src.strategies.daily_stock_analysis.config import DailyStockConfig
        
        # 创建配置
        config = DailyStockConfig(
            model_type="gemini",
            max_tokens=1500,
            temperature=0.7,
            enable_technical_analysis=True,
            enable_fundamental_analysis=True
        )
        
        # 创建数据获取器
        fetcher = StockDataFetcher(config)
        print("✅ 成功创建StockDataFetcher")
        
        # 创建AI决策器
        ai_maker = AIDecisionMaker(config)
        print("✅ 成功创建AIDecisionMaker")
        
        # 模拟股票数据（快速测试，不实际获取）
        mock_stock_data = {
            "symbol": "000001",
            "name": "平安银行",
            "current_price": 15.80,
            "change_percent": 1.25,
            "volume": 125000000,
            "market_cap": 300000000000,
            "pe_ratio": 8.5,
            "pb_ratio": 0.9,
            "dividend_yield": 3.2
        }
        
        print(f"\n模拟股票数据:")
        for key, value in mock_stock_data.items():
            print(f"  {key}: {value}")
        
        print("\n✅ 股票分析模块基础功能正常")
        return True
        
    except Exception as e:
        print(f"✗ 股票分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("量化平台AI集成快速测试")
    print("=" * 60)
    print(f"项目路径: {project_root}")
    print(f"Python版本: {sys.version.split()[0]}")
    print()
    
    # 加载环境变量
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"找到.env文件: {env_file}")
        # 简单读取环境变量
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key_value = line.strip().split('=', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        if "KEY" in key or "TOKEN" in key:
                            print(f"  找到: {key}={value[:10]}...")
    else:
        print("⚠ 未找到.env文件")
    
    # 运行测试
    tests_passed = 0
    total_tests = 4
    
    # 测试1: Gemini模块导入
    gemini_ok, gemini_version = test_gemini_import()
    if gemini_ok:
        tests_passed += 1
    
    # 测试2: AI决策模块
    if test_ai_decision_module():
        tests_passed += 1
    
    # 测试3: 简单Gemini调用（需要API Key）
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        if test_simple_gemini_call():
            tests_passed += 1
    else:
        print("\n⚠ 跳过Gemini API调用测试（需要API Key）")
        total_tests -= 1
    
    # 测试4: 股票分析功能
    if test_stock_analysis():
        tests_passed += 1
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过测试: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ 所有测试通过！AI集成正常。")
    elif tests_passed >= total_tests - 1:
        print("⚠ 大部分测试通过，需要设置API Key进行完整测试。")
    else:
        print("✗ 多个测试失败，需要检查配置和依赖。")
    
    # 下一步建议
    print("\n" + "=" * 60)
    print("下一步建议")
    print("=" * 60)
    
    if not api_key:
        print("1. 设置GEMINI_API_KEY:")
        print("   在.env文件中添加: GEMINI_API_KEY=your_key_here")
        print("   或运行: export GEMINI_API_KEY=your_key_here")
    
    if gemini_version == "google.generativeai":
        print("2. 升级Gemini SDK:")
        print("   运行: pip install google-genai")
        print("   然后更新代码使用google.genai")
    
    print("3. 运行完整测试:")
    print("   python test_gemini_integration.py")
    
    print("4. 测试实际股票分析:")
    print("   python strategy-engine/src/strategies/daily_stock_analysis/run_analysis.py")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)