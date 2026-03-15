#!/usr/bin/env python3
"""
个人量化投资助手 - 报告生成器
功能：生成美观的投资分析报告（支持微信和邮件格式）
"""

import os
from datetime import datetime
from typing import List, Dict


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.date = datetime.now().strftime("%Y-%m-%d")
    
    def generate_wechat_report(self, analysis_results: List[Dict]) -> str:
        """
        生成微信格式报告
        
        Args:
            analysis_results: AI分析结果列表
            
        Returns:
            微信格式的报告文本
        """
        # 按评级排序
        buy_stocks = [r for r in analysis_results if r.get("rating") == "买入"]
        hold_stocks = [r for r in analysis_results if r.get("rating") == "持有"]
        sell_stocks = [r for r in analysis_results if r.get("rating") == "卖出"]
        
        # 按星级排序
        buy_stocks.sort(key=lambda x: x.get("stars", 0), reverse=True)
        
        report = f"""📊 每日股票分析 - {self.date}

━━━━━━━━━━━━━━━━━━
🔥 重点关注（买入评级）
━━━━━━━━━━━━━━━━━━
"""
        
        if buy_stocks:
            for i, stock in enumerate(buy_stocks[:5], 1):
                stars = "⭐" * stock.get("stars", 3)
                report += f"""
{i}. {stock.get('name')} ({stock.get('code')[:6]})
   评级：{stock.get('rating')} {stars}
   策略：{stock.get('strategy', '暂无')}
   理由：{stock.get('reasons', ['暂无'])[0] if stock.get('reasons') else '暂无'}
   ⚠️ 风险：{stock.get('risks', ['暂无'])[0] if stock.get('risks') else '暂无'}
"""
        else:
            report += "\n暂无买入评级股票\n"
        
        report += f"""
━━━━━━━━━━━━━━━━━━
👁️ 保持关注（持有评级）
━━━━━━━━━━━━━━━━━━
"""
        
        if hold_stocks:
            for i, stock in enumerate(hold_stocks[:5], 1):
                report += f"{i}. {stock.get('name')} ({stock.get('code')[:6]}) - {stock.get('strategy', '观望')}\n"
        else:
            report += "\n暂无\n"
        
        if sell_stocks:
            report += f"""
━━━━━━━━━━━━━━━━━━
⚠️ 注意风险（卖出评级）
━━━━━━━━━━━━━━━━━━
"""
            for i, stock in enumerate(sell_stocks[:3], 1):
                report += f"{i}. {stock.get('name')} ({stock.get('code')[:6]}) - {stock.get('strategy', '谨慎')}\n"
        
        # 总结
        report += f"""
━━━━━━━━━━━━━━━━━━
💡 今日策略建议
━━━━━━━━━━━━━━━━━━
• 重点关注：{len(buy_stocks)} 只
• 保持关注：{len(hold_stocks)} 只
• 注意风险：{len(sell_stocks)} 只

• 总股票数：{len(analysis_results)} 只
• 买入比例：{len(buy_stocks)/len(analysis_results)*100:.1f}%

📌 提醒：投资有风险，决策需谨慎
   本分析仅供参考，不构成投资建议

━━━━━━━━━━━━━━━━━━
生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}
"""
        
        return report
    
    def generate_email_report(self, analysis_results: List[Dict]) -> Dict:
        """
        生成邮件格式报告
        
        Args:
            analysis_results: AI分析结果列表
            
        Returns:
            邮件字典（subject, html_content, text_content）
        """
        # 按评级排序
        buy_stocks = [r for r in analysis_results if r.get("rating") == "买入"]
        hold_stocks = [r for r in analysis_results if r.get("rating") == "持有"]
        sell_stocks = [r for r in analysis_results if r.get("rating") == "卖出"]
        
        buy_stocks.sort(key=lambda x: x.get("stars", 0), reverse=True)
        
        # HTML格式
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #667eea; background: #f8f9fa; }}
        .stock {{ margin: 15px 0; padding: 10px; background: white; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .stock-name {{ font-weight: bold; font-size: 16px; color: #667eea; }}
        .rating {{ display: inline-block; padding: 3px 10px; border-radius: 3px; color: white; }}
        .rating-buy {{ background: #28a745; }}
        .rating-hold {{ background: #ffc107; color: #333; }}
        .rating-sell {{ background: #dc3545; }}
        .stars {{ color: #ffc107; }}
        .risk {{ color: #dc3545; font-size: 14px; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 每日股票分析报告</h1>
        <p>{self.date}</p>
    </div>
    
    <div class="section">
        <h2>🔥 重点关注（买入评级）</h2>
"""
        
        if buy_stocks:
            for stock in buy_stocks[:5]:
                stars = "⭐" * stock.get("stars", 3)
                html_content += f"""
        <div class="stock">
            <div class="stock-name">{stock.get('name')} ({stock.get('code')[:6]})</div>
            <div>
                <span class="rating rating-buy">{stock.get('rating')}</span>
                <span class="stars">{stars}</span>
            </div>
            <p><strong>策略：</strong>{stock.get('strategy', '暂无')}</p>
            <p><strong>理由：</strong>{stock.get('reasons', ['暂无'])[0] if stock.get('reasons') else '暂无'}</p>
            <p class="risk"><strong>⚠️ 风险：</strong>{stock.get('risks', ['暂无'])[0] if stock.get('risks') else '暂无'}</p>
        </div>
"""
        else:
            html_content += "<p>暂无买入评级股票</p>"
        
        html_content += """
    </div>
    
    <div class="section">
        <h2>👁️ 保持关注（持有评级）</h2>
"""
        
        if hold_stocks:
            for stock in hold_stocks[:5]:
                html_content += f"""
        <div class="stock">
            <div class="stock-name">{stock.get('name')} ({stock.get('code')[:6]})</div>
            <p>{stock.get('strategy', '观望')}</p>
        </div>
"""
        else:
            html_content += "<p>暂无</p>"
        
        html_content += f"""
    </div>
    
    <div class="footer">
        <p><strong>统计：</strong>重点关注 {len(buy_stocks)} 只 | 保持关注 {len(hold_stocks)} 只 | 注意风险 {len(sell_stocks)} 只</p>
        <p><strong>提醒：</strong>投资有风险，决策需谨慎。本分析仅供参考，不构成投资建议。</p>
        <p>生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </div>
</body>
</html>
"""
        
        # 纯文本格式（用于微信或邮件备用）
        text_content = self.generate_wechat_report(analysis_results)
        
        return {
            "subject": f"📊 每日股票分析 - {self.date}",
            "html": html_content,
            "text": text_content
        }


def test_report():
    """测试报告生成"""
    print("=== 测试报告生成器 ===")
    
    generator = ReportGenerator()
    
    # 测试数据
    test_results = [
        {
            "code": "600519.XSHG",
            "name": "贵州茅台",
            "rating": "买入",
            "stars": 5,
            "strategy": "趋势良好，可考虑介入",
            "reasons": ["技术面突破", "资金流入明显"],
            "risks": ["大盘波动"]
        },
        {
            "code": "300750.XSHE",
            "name": "宁德时代",
            "rating": "持有",
            "stars": 3,
            "strategy": "趋势稳定，等待突破",
            "reasons": ["行业前景好"],
            "risks": ["行业竞争加剧"]
        }
    ]
    
    # 生成微信报告
    wechat_report = generator.generate_wechat_report(test_results)
    print("\n微信报告预览:")
    print(wechat_report[:500] + "...")
    
    # 生成邮件报告
    email_report = generator.generate_email_report(test_results)
    print(f"\n邮件主题：{email_report['subject']}")
    print(f"HTML长度：{len(email_report['html'])} 字符")
    
    return {
        "wechat": wechat_report,
        "email": email_report
    }


if __name__ == "__main__":
    test_report()
