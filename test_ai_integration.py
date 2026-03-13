#!/usr/bin/env python3
"""
AI集成快速测试
测试daily_stock_analysis模块的AI服务集成
"""

import asyncio
import sys
import os
import importlib.util

async def test_ai_integration():
    """测试AI集成"""
    print("=" * 60)
    print("AI集成快速测试")
    print("=" * 60)
    
    try:
        # 1. 检查环境变量
        print("1. 检查API Key配置...")
        api_key = os.getenv("BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        
        if api_key:
            print(f"   ✅ API Key已配置: {api_key[:10]}...{api_key[-10:]}")
            
            # 检查dashscope模块
            try:
                import dashscope
                print("   ✅ dashscope模块可用")
                
                # 测试API Key
                dashscope.api_key = api_key
                print("   ✅ API Key设置成功")
            except ImportError:
                print("   ⚠ dashscope模块未安装，将使用pip安装")
                import subprocess
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "dashscope"])
                    import dashscope
                    print("   ✅ dashscope安装成功")
                    dashscope.api_key = api_key
                    print("   ✅ API Key设置成功")
                except Exception as e:
                    print(f"   ❌ dashscope安装失败: {e}")
                    return False
        else:
            print("   ❌ 未找到API Key环境变量")
            print("     请检查.env文件中的BAILIAN_API_KEY或DASHSCOPE_API_KEY")
            return False
        
        # 2. 测试AI决策模块导入
        print("\n2. 测试AI决策模块导入...")
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
            data_sources=["tushare"],
            ai_model="qwen-max",  # 使用百炼/通义
            ai_temperature=0.7,
            notification_channels=["console"]
        )
        
        print(f"   ✅ 配置创建成功: {config.name}")
        print(f"     使用AI模型: {config.ai_model}")
        
        # 导入ai_decision
        ai_path = os.path.join(base_path, "ai_decision.py")
        with open(ai_path, 'r', encoding='utf-8') as f:
            ai_content = f.read()
        
        # 修复导入
        ai_content = ai_content.replace("from .config import DailyStockConfig",
                                       f"DailyStockConfig = {config_module.__name__}.DailyStockConfig")
        
        spec = importlib.util.spec_from_file_location("ai_decision", ai_path)
        ai_module = importlib.util.module_from_spec(spec)
        exec(ai_content, ai_module.__dict__)
        AIDecisionMaker = ai_module.AIDecisionMaker
        
        print("   ✅ AI决策模块导入成功")
        
        # 3. 创建AI决策器
        print("\n3. 创建AI决策器...")
        ai_decision_maker = AIDecisionMaker(config)
        print("   ✅ AI决策器创建成功")
        
        # 4. 测试模拟数据
        print("\n4. 准备测试数据...")
        test_market_data = {
            "timestamp": "2026-03-13T12:50:00",
            "data_sources_used": ["test"],
            "markets": {
                "A": {
                    "summary": {
                        "symbol_count": 3,
                        "data_sources": ["test"],
                        "data_points": 15
                    },
                    "data": {
                        "test": {
                            "quotes": [
                                {"symbol": "000001.SZ", "name": "平安银行", "price": 15.20, "change": 1.5, "volume": 1000000},
                                {"symbol": "600519.SH", "name": "贵州茅台", "price": 1850.00, "change": 0.8, "volume": 500000},
                                {"symbol": "000858.SZ", "name": "五粮液", "price": 150.50, "change": 2.1, "volume": 800000}
                            ]
                        }
                    }
                }
            }
        }
        
        print(f"   ✅ 测试数据准备完成")
        print(f"     股票数量: 3")
        
        # 5. 测试AI分析
        print("\n5. 测试AI分析...")
        print("   正在调用通义千问API，请稍候...")
        
        try:
            ai_results = await ai_decision_maker.analyze_market_data(test_market_data)
            
            print(f"   ✅ AI分析完成")
            print(f"     状态: {ai_results.get('status')}")
            print(f"     使用模型: {ai_results.get('model_used')}")
            
            # 检查结果
            recommendations = ai_results.get('recommendations', {})
            if isinstance(recommendations, dict):
                top_picks = recommendations.get('top_picks', [])
                if top_picks:
                    print(f"     推荐股票数: {len(top_picks)}")
                    print("\n     推荐详情:")
                    for i, pick in enumerate(top_picks[:3], 1):
                        if isinstance(pick, dict):
                            print(f"     {i}. {pick.get('symbol', '未知')} - {pick.get('action', '未知')}")
                            print(f"         理由: {pick.get('reason', '')[:50]}...")
                else:
                    print("     ⚠ 未找到推荐股票")
            else:
                print(f"     原始AI响应: {str(ai_results)[:200]}...")
            
            # 检查是否使用了真实API
            raw_response = ai_results.get('raw_ai_response', '')
            if "模拟" in str(raw_response) or "mock" in str(raw_response).lower():
                print("\n     ⚠ 注意: 使用了模拟响应，可能API调用失败")
                print("        可能原因: API Key无效、网络问题、或API限制")
            else:
                print("\n     ✅ 使用了真实AI API响应")
            
        except Exception as e:
            print(f"   ❌ AI分析失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 60)
        print("🎉 AI集成测试完成！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_ai_call():
    """简单AI调用测试"""
    print("\n" + "=" * 60)
    print("简单AI调用测试")
    print("=" * 60)
    
    try:
        # 直接测试dashscope调用
        import dashscope
        
        api_key = os.getenv("BAILIAN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            print("❌ 未找到API Key")
            return False
        
        dashscope.api_key = api_key
        
        print("调用通义千问API测试...")
        response = dashscope.Generation.call(
            model="qwen-turbo",
            prompt="请用一句话介绍你自己",
            max_tokens=50
        )
        
        if response.status_code == 200:
            print(f"✅ API调用成功")
            print(f"   响应: {response.output.text}")
            return True
        else:
            print(f"❌ API调用失败: {response.code} - {response.message}")
            return False
            
    except Exception as e:
        print(f"❌ 简单测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("开始AI集成测试...")
    
    # 先测试简单调用
    simple_success = await test_simple_ai_call()
    
    if simple_success:
        print("\n✅ 基础API调用测试通过，继续完整测试...")
        full_success = await test_ai_integration()
    else:
        print("\n⚠ 基础API调用测试失败，跳过完整测试")
        full_success = False
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if simple_success and full_success:
        print("🎉 所有测试通过！AI集成成功")
        print("   daily_stock_analysis模块可以调用真实AI服务")
    elif simple_success:
        print("👍 基础API调用成功，但完整测试有问题")
        print("   需要进一步调试AI决策模块")
    else:
        print("❌ API调用测试失败")
        print("   请检查：")
        print("   1. API Key是否正确配置在.env文件中")
        print("   2. 网络连接是否正常")
        print("   3. API Key是否有余额或权限")
    
    return simple_success

if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    
    # 退出代码
    sys.exit(0 if success else 1)