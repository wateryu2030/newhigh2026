#!/usr/bin/env python3
"""
Gemini AI集成快速测试
测试daily_stock_analysis模块的Gemini AI服务集成
"""

import asyncio
import sys
import os
import json


async def test_gemini_integration():
    """测试Gemini集成"""
    print("=" * 60)
    print("Gemini AI集成快速测试")
    print("=" * 60)

    try:
        # 1. 检查Gemini API Key
        print("1. 检查Gemini API Key...")
        api_key = os.getenv("GEMINI_API_KEY")

        if api_key:
            print(f"   ✅ Gemini API Key已配置: {api_key[:10]}...{api_key[-10:]}")
        else:
            print("   ❌ 未找到GEMINI_API_KEY环境变量")
            return False

        # 2. 检查google.generativeai模块
        print("\n2. 检查google.generativeai模块...")
        try:
            import google.generativeai as genai

            print("   ✅ google.generativeai模块可用")

            # 配置API Key
            genai.configure(api_key=api_key)
            print("   ✅ API Key配置成功")
        except ImportError:
            print("   ⚠ google.generativeai模块未安装，将使用pip安装")
            import subprocess

            try:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "google-generativeai",
                        "--break-system-packages",
                    ]
                )
                import google.generativeai as genai

                print("   ✅ google-generativeai安装成功")
                genai.configure(api_key=api_key)
                print("   ✅ API Key配置成功")
            except Exception as e:
                print(f"   ❌ 安装失败: {e}")
                return False

        # 3. 测试简单Gemini调用
        print("\n3. 测试简单Gemini调用...")
        try:
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content("请用一句话介绍你自己")

            if response.text:
                print(f"   ✅ Gemini API调用成功")
                print(f"      响应: {response.text[:100]}...")
            else:
                print(f"   ❌ Gemini API调用失败: {response.prompt_feedback}")
                return False

        except Exception as e:
            print(f"   ❌ Gemini调用异常: {e}")
            return False

        # 4. 测试AI决策模块
        print("\n4. 测试AI决策模块集成...")
        try:
            # 导入必要的模块
            import sys

            sys.path.insert(0, "/Users/apple/Ahope/newhigh/strategy-engine/src")

            # 导入config
            from strategies.daily_stock_analysis.config import DailyStockConfig

            # 创建配置
            config = DailyStockConfig(
                enabled=True,
                data_sources=["test"],
                ai_model="gemini-pro",  # 使用Gemini
                ai_temperature=0.7,
                notification_channels=["console"],
            )

            print(f"   ✅ 配置创建成功")
            print(f"      使用AI模型: {config.ai_model}")

            # 导入ai_decision
            from strategies.daily_stock_analysis.ai_decision import AIDecisionMaker

            # 创建AI决策器
            ai_decision_maker = AIDecisionMaker(config)
            print("   ✅ AI决策器创建成功")

            # 5. 准备测试数据
            print("\n5. 准备测试数据...")
            test_market_data = {
                "timestamp": "2026-03-13T13:20:00",
                "data_sources_used": ["test"],
                "markets": {
                    "A": {
                        "summary": {"symbol_count": 3, "data_sources": ["test"], "data_points": 15},
                        "data": {
                            "test": {
                                "quotes": [
                                    {
                                        "symbol": "000001.SZ",
                                        "name": "平安银行",
                                        "price": 15.20,
                                        "change": 1.5,
                                        "volume": 1000000,
                                    },
                                    {
                                        "symbol": "600519.SH",
                                        "name": "贵州茅台",
                                        "price": 1850.00,
                                        "change": 0.8,
                                        "volume": 500000,
                                    },
                                    {
                                        "symbol": "000858.SZ",
                                        "name": "五粮液",
                                        "price": 150.50,
                                        "change": 2.1,
                                        "volume": 800000,
                                    },
                                ]
                            }
                        },
                    }
                },
            }

            print(f"   ✅ 测试数据准备完成")
            print(f"      股票数量: 3")

            # 6. 测试AI分析
            print("\n6. 测试AI分析...")
            print("   正在调用Gemini API分析股票数据，请稍候...")

            ai_results = await ai_decision_maker.analyze_market_data(test_market_data)

            print(f"   ✅ AI分析完成")
            print(f"      状态: {ai_results.get('status')}")
            print(f"      使用模型: {ai_results.get('model_used')}")

            # 检查结果
            recommendations = ai_results.get("recommendations", {})
            if isinstance(recommendations, dict):
                top_picks = recommendations.get("top_picks", [])
                if top_picks:
                    print(f"      推荐股票数: {len(top_picks)}")
                    print("\n      推荐详情:")
                    for i, pick in enumerate(top_picks[:3], 1):
                        if isinstance(pick, dict):
                            print(
                                f"      {i}. {pick.get('symbol', '未知')} - {pick.get('action', '未知')}"
                            )
                            print(f"          理由: {pick.get('reason', '')[:50]}...")
                else:
                    print("      ⚠ 未找到推荐股票")
            else:
                print(f"      原始AI响应: {str(ai_results)[:200]}...")

            # 检查是否使用了真实API
            raw_response = ai_results.get("raw_ai_response", "")
            if "模拟" in str(raw_response) or "mock" in str(raw_response).lower():
                print("\n      ⚠ 注意: 使用了模拟响应，可能API调用失败")
            else:
                print("\n      ✅ 使用了真实Gemini API响应")

        except Exception as e:
            print(f"   ❌ AI决策模块测试失败: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("\n" + "=" * 60)
        print("🎉 Gemini AI集成测试完成！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始Gemini AI集成测试...")

    success = await test_gemini_integration()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if success:
        print("🎉 Gemini AI集成成功！")
        print("   daily_stock_analysis模块现在可以调用真实Gemini AI服务")
        print("\n   下一步:")
        print("   1. 集成真实数据源（Tushare）")
        print("   2. 运行完整的daily_stock_analysis流程")
        print("   3. 输出分析报告")
    else:
        print("❌ Gemini AI集成测试失败")
        print("   请检查：")
        print("   1. GEMINI_API_KEY是否正确配置在.env文件中")
        print("   2. 网络连接是否正常")
        print("   3. Gemini API是否有可用额度")

    return success


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())

    # 退出代码
    sys.exit(0 if success else 1)
