#!/usr/bin/env python3
"""
快速AI集成测试
测试完整的AI决策流程
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_full_ai_pipeline():
    """测试完整的AI决策流程"""
    print("=" * 60)
    print("测试完整AI决策流程")
    print("=" * 60)
    
    try:
        # 导入必要的模块
        import sys
        sys.path.insert(0, str(project_root / "strategy-engine"))
        
        from src.strategies.daily_stock_analysis.ai_decision import AIDecisionMaker
        from src.strategies.daily_stock_analysis.config import DailyStockConfig
        
        # 创建配置
        config = DailyStockConfig(
            ai_model="gemini-pro",
            ai_temperature=0.7,
            ai_max_tokens=2000
        )
        
        print("✅ 配置创建成功")
        
        # 创建AI决策器
        ai_maker = AIDecisionMaker(config)
        print("✅ AI决策器创建成功")
        
        # 模拟股票数据
        mock_data = {
            "symbol": "000001",
            "name": "平安银行",
            "current_price": 15.80,
            "change_percent": 1.25,
            "volume": 125000000,
            "market_cap": 300000000000,
            "pe_ratio": 8.5,
            "pb_ratio": 0.9,
            "dividend_yield": 3.2,
            "industry": "银行",
            "technical_indicators": {
                "rsi": 45.2,
                "macd": 0.15,
                "bollinger_bands": {"upper": 16.5, "middle": 15.2, "lower": 13.9}
            }
        }
        
        print(f"\n📊 模拟股票数据:")
        print(f"  股票: {mock_data['name']} ({mock_data['symbol']})")
        print(f"  价格: ¥{mock_data['current_price']} ({mock_data['change_percent']}%)")
        print(f"  估值: PE={mock_data['pe_ratio']}, PB={mock_data['pb_ratio']}")
        print(f"  股息率: {mock_data['dividend_yield']}%")
        
        # 调用AI分析
        print("\n🤖 调用AI分析...")
        ai_response = await ai_maker.analyze_stock(mock_data)
        
        print(f"\n✅ AI分析完成!")
        print(f"响应长度: {len(ai_response)} 字符")
        print(f"\n📝 AI分析结果:")
        print("-" * 40)
        print(ai_response[:500] + "..." if len(ai_response) > 500 else ai_response)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 快速AI集成测试")
    print(f"时间: 2026-03-13 18:20")
    print(f"项目: {project_root.name}")
    print()
    
    # 检查环境变量
    print("🔍 检查环境配置...")
    api_keys = {
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY"),
    }
    
    for key, value in api_keys.items():
        if value:
            print(f"  ✅ {key}: 已设置 ({value[:10]}...)")
        else:
            print(f"  ⚠ {key}: 未设置")
    
    # 运行测试
    print("\n" + "=" * 60)
    print("开始测试")
    print("=" * 60)
    
    # 运行异步测试
    success = asyncio.run(test_full_ai_pipeline())
    
    # 结果汇总
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    if success:
        print("🎉 测试成功！AI决策流程正常工作。")
        print("\n下一步:")
        print("1. 运行实际股票分析: python run_daily_analysis.py")
        print("2. 测试更多股票: 修改测试脚本中的股票数据")
        print("3. 集成到调度系统: 配置每日自动分析")
    else:
        print("⚠ 测试失败，需要检查:")
        print("1. 确保所有依赖已安装")
        print("2. 检查API Key是否正确")
        print("3. 查看错误日志获取详细信息")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)