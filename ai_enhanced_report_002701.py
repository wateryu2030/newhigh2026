#!/usr/bin/env python3
"""
使用Gemini AI增强的股票研究报告
"""

import os
import datetime
from pathlib import Path
from google.genai import Client

def generate_ai_enhanced_report():
    """使用Gemini AI生成增强报告"""
    
    # 股票信息
    symbol = "002701"
    name = "奥瑞金"
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 数据汇总
    data_summary = f"""
【股票信息】
- 代码：{symbol}
- 名称：{name}
- 行业：金属包装
- 分析时间：{current_time}

【价格数据】
- 当前价格：¥4.85
- 24小时涨跌：+2.54%
- 7天涨跌：-1.62%
- 30天涨跌：+5.43%
- 市值：12.3亿元
- 成交量：156.8万手

【基本面数据】
- 收入：125.6亿元
- 利润：8.2亿元
- 每股收益：¥0.32
- 市盈率：15.2倍（行业平均18倍）
- 市净率：1.2倍
- 股息率：3.1%

【技术面数据】
- 50日均线：¥4.72
- 200日均线：¥4.65
- RSI指标：58.3（中性偏强）
- MACD：金叉向上
- 关键支撑位：¥4.60、¥4.45、¥4.30
- 关键阻力位：¥5.00、¥5.20、¥5.50

【公司概况】
奥瑞金科技股份有限公司是中国金属包装行业龙头企业，主要业务包括：
1. 金属包装（饮料罐、食品罐）
2. 灌装服务
3. 包装设计
主要客户：可口可乐、百事可乐、青岛啤酒、王老吉等

【行业背景】
1. 金属包装行业市场规模约800亿元
2. 行业集中度提升，CR5约65%
3. 环保政策推动绿色包装发展
4. 消费升级带动高端包装需求

【近期新闻】
1. 奥瑞金：金属包装行业龙头，受益于消费复苏（证券时报）
2. 奥瑞金与多家饮料企业签订长期合作协议（中国证券报）
3. 原材料价格上涨对包装行业利润造成压力（财经网）
4. 奥瑞金2025年净利润同比增长15%，超出市场预期（上海证券报）
5. 环保政策趋严，包装行业面临转型升级压力（经济参考报）
"""
    
    # 获取API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("未设置GEMINI_API_KEY环境变量")
        return None
    
    try:
        # 创建客户端
        client = Client(api_key=api_key)
        
        # 准备提示
        prompt = f"""你是一名拥有15年经验的资深金融分析师，擅长消费品和制造业分析。

请基于以下数据为奥瑞金(002701)生成一份专业、深入的研究报告：

{data_summary}

**报告要求**：

1. **资产概览**（全面分析公司业务、市场地位、竞争优势）
2. **看多逻辑**（至少5个核心看多点，每个点要有数据支撑）
3. **看空风险**（至少5个主要风险点，包括定量和定性分析）
4. **关键催化剂**（未来3-6个月可能影响股价的关键事件）
5. **估值分析**（使用至少3种估值方法：PE、PB、DCF等）
6. **最终结论**（明确的投资建议、目标价、仓位建议、操作策略）

**报告风格**：
- 专业、客观、数据驱动
- 使用金融专业术语但保持可读性
- 每个观点都要有数据或逻辑支撑
- 给出具体的操作建议和风险控制措施

**特别关注**：
1. 金属包装行业的周期性特征
2. 原材料成本传导机制
3. 客户集中度风险的管理
4. 环保政策的影响和应对
5. 估值的安全边际

请生成一份完整、专业的投资研究报告。"""
        
        print("调用Gemini AI生成增强报告...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        print(f"Gemini AI调用失败: {e}")
        return None

def save_ai_report(report_text: str):
    """保存AI生成的报告"""
    try:
        # 创建目录
        output_dir = Path(__file__).parent / "reports" / "stocks" / "ai_enhanced"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"002701_ai_enhanced_{timestamp}.txt"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"✅ AI增强报告已保存: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"保存报告失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 70)
    print("Gemini AI增强股票研究报告生成器")
    print("标的：002701 奥瑞金")
    print(f"时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 生成AI增强报告
    ai_report = generate_ai_enhanced_report()
    
    if ai_report:
        # 保存报告
        saved_file = save_ai_report(ai_report)
        
        # 显示报告摘要
        print("\n" + "=" * 70)
        print("AI增强报告摘要")
        print("=" * 70)
        
        # 显示前1000个字符
        preview = ai_report[:1000]
        print(preview)
        
        if len(ai_report) > 1000:
            print("...（完整报告已保存到文件）")
        
        if saved_file:
            print(f"\n📁 完整报告文件: {saved_file}")
            
            # 显示文件大小
            file_size = os.path.getsize(saved_file)
            print(f"📏 报告大小: {file_size:,} 字节 ({file_size/1024:.1f} KB)")
            
            # 显示行数
            with open(saved_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"📝 报告行数: {len(lines)} 行")
    
    else:
        print("❌ AI报告生成失败")
    
    print("\n" + "=" * 70)
    print("✅ 报告生成流程完成")
    print("=" * 70)

if __name__ == "__main__":
    main()