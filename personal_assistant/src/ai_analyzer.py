#!/usr/bin/env python3
"""
个人量化投资助手 - AI分析引擎
功能：调用DeepSeek AI分析股票，生成投资建议
"""

import os
import sys
import json
from typing import Dict, List, Any
from datetime import datetime

# 添加项目路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ["data-pipeline/src", "core/src", "strategy-engine/src"]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from openai import OpenAI
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False
    OpenAI = None

try:
    from soul_framework import soul_body_for_prompt
except ImportError:
    def soul_body_for_prompt() -> str:  # type: ignore
        return ""


class AIStockAnalyzer:
    """AI股票分析器"""

    def __init__(self, api_key: str = None):
        """
        初始化分析器

        Args:
            api_key: DeepSeek API Key
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.client = None

        if DEEPSEEK_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
                print("✅ DeepSeek AI 初始化成功")
            except Exception as e:
                print(f"⚠️ DeepSeek AI 初始化失败: {e}")
        else:
            if not self.api_key:
                print("⚠️ 未找到 DEEPSEEK_API_KEY，将使用模拟分析")

    def analyze_stock(self, stock_data: Dict) -> Dict:
        """
        分析单只股票

        Args:
            stock_data: 股票数据（包含基本信息、近期价格、技术指标等）

        Returns:
            分析结果字典
        """
        if not self.client:
            return self._mock_analysis(stock_data)

        try:
            # 构建分析提示词
            prompt = self._build_analysis_prompt(stock_data)

            # 调用AI
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )

            # 解析AI响应
            ai_response = response.choices[0].message.content
            analysis_result = self._parse_ai_response(ai_response, stock_data)

            return analysis_result

        except Exception as e:
            print(f"⚠️ AI分析失败: {e}，使用模拟分析")
            return self._mock_analysis(stock_data)

    def _get_system_prompt(self) -> str:
        """获取系统提示词（含 soul.md 机会发现引擎，用于行业地位与前景）。"""
        base = """你是一位专业的股票分析师，拥有10年A股市场经验。
你的任务是分析股票数据，给出清晰、实用的投资建议。

请遵循以下原则：
1. 客观分析，不夸大收益，不隐瞒风险
2. 建议明确：买入/持有/卖出，不要模棱两可
3. 理由充分：基于技术面、资金面、情绪面、基本面、消息面
4. 风险提示：必须指出潜在风险
5. 语言简洁：用通俗易懂的中文，避免专业术语堆砌

你必须勇于对股票所在行业地位和前景做分析，并遵循下面的「机会发现引擎」框架（来自项目永久规则 docs/soul.md）：
"""
        soul = soul_body_for_prompt()
        if soul:
            base += "\n" + soul + "\n\n"
        base += """输出格式：
【评级】买入/持有/卖出（1-5星）
【理由】3-5条核心理由（含行业地位/前景时按机会发现引擎的要点简要说明）
【风险】1-3个主要风险点
【策略】具体操作建议"""
        return base

    def _build_analysis_prompt(self, stock_data: Dict) -> str:
        """构建分析提示词"""
        code = stock_data.get("code", "未知")
        name = stock_data.get("name", "未知")
        industry = stock_data.get("industry", "未知")
        market_cap = stock_data.get("market_cap", 0)
        recent_data = stock_data.get("recent_data", [])
        stock_type = stock_data.get("type", "unknown")

        # 计算技术指标
        if recent_data:
            latest = recent_data[0]
            close = latest[5]  # 收盘价
            volume = latest[4]  # 成交量
            amount = latest[5]  # 成交额

            # 计算5日涨跌幅
            if len(recent_data) >= 2:
                old_close = recent_data[-1][5]
                change_5d = (close - old_close) / old_close * 100
            else:
                change_5d = 0
        else:
            close = 0
            change_5d = 0

        prompt = f"""请分析以下股票：

【股票信息】
代码：{code}
名称：{name}
行业：{industry}
市值：{market_cap:,}元
来源：{'固定关注' if stock_type == 'fixed' else '动态筛选'}

【近期价格数据】（最新5个交易日）
日期        开盘    最高    最低    收盘    成交量
"""

        for row in recent_data[:5]:
            date = str(row[1])[:10] if row[1] else "N/A"
            prompt += f"{date}  {row[2]:.2f}  {row[3]:.2f}  {row[4]:.2f}  {row[5]:.2f}  {row[6]:,}\n"

        prompt += f"""
【技术指标】
5日涨跌幅：{change_5d:.2f}%
最新收盘价：{close:.2f}元

【分析要求】
请从以下维度全面分析（其中行业地位与前景必须按系统提示中的「机会发现引擎」框架分析）：
1. 技术面：趋势、支撑位、压力位、成交量变化
2. 资金面：资金流向、主力动向
3. 情绪面：市场情绪、热度
4. 基本面：行业地位、行业前景、估值水平（低效/不对称/趋势/竞争格局/机会排序）
5. 消息面：近期重要新闻、政策影响
6. 板块轮动：所属板块表现

请给出明确的投资建议和风险提示。"""

        return prompt

    def _parse_ai_response(self, ai_response: str, stock_data: Dict) -> Dict:
        """解析AI响应"""
        # 简单解析，提取关键信息
        result = {
            "code": stock_data.get("code"),
            "name": stock_data.get("name"),
            "rating": "持有",  # 默认
            "stars": 3,
            "reasons": [],
            "risks": [],
            "strategy": "观望",
            "raw_analysis": ai_response
        }

        # 尝试提取评级
        if "买入" in ai_response:
            result["rating"] = "买入"
            if "⭐⭐⭐⭐⭐" in ai_response or "5 星" in ai_response:
                result["stars"] = 5
            elif "⭐⭐⭐⭐" in ai_response or "4 星" in ai_response:
                result["stars"] = 4
            elif "⭐⭐⭐" in ai_response or "3 星" in ai_response:
                result["stars"] = 3
        elif "卖出" in ai_response:
            result["rating"] = "卖出"
            if "⭐⭐⭐⭐⭐" in ai_response or "5 星" in ai_response:
                result["stars"] = 5
            elif "⭐⭐⭐⭐" in ai_response or "4 星" in ai_response:
                result["stars"] = 4
            else:
                result["stars"] = 3

        # 提取理由（简单处理）
        lines = ai_response.split("\n")
        for line in lines:
            if "理由" in line or "因为" in line:
                result["reasons"].append(line.strip())
            if "风险" in line:
                result["risks"].append(line.strip())
            if "策略" in line or "建议" in line:
                result["strategy"] = line.strip()

        return result

    def _mock_analysis(self, stock_data: Dict) -> Dict:
        """模拟分析（当AI不可用时）"""
        code = stock_data.get("code", "未知")
        name = stock_data.get("name", "未知")
        recent_data = stock_data.get("recent_data", [])

        # 基于简单规则的模拟分析
        if recent_data and len(recent_data) >= 2:
            latest_close = recent_data[0][5]
            old_close = recent_data[-1][5]
            change = (latest_close - old_close) / old_close * 100

            if change > 5:
                rating = "买入"
                stars = 4
                strategy = "趋势良好，可考虑介入"
            elif change > 0:
                rating = "持有"
                stars = 3
                strategy = "走势平稳，继续持有"
            else:
                rating = "持有"
                stars = 2
                strategy = "短期调整，注意风险"
        else:
            rating = "持有"
            stars = 3
            strategy = "数据不足，谨慎观望"

        return {
            "code": code,
            "name": name,
            "rating": rating,
            "stars": stars,
            "reasons": [
                "基于近期价格走势分析",
                "技术面表现" + ("良好" if stars >= 3 else "一般"),
                "建议关注成交量变化"
            ],
            "risks": [
                "市场波动风险",
                "行业政策变化"
            ],
            "strategy": strategy,
            "is_mock": True
        }


def test_analyzer():
    """测试分析器"""
    print("=== 测试 AI 分析引擎 ===")

    analyzer = AIStockAnalyzer()

    # 测试数据
    test_stock = {
        "code": "600519.XSHG",
        "name": "贵州茅台",
        "industry": "白酒",
        "market_cap": 2000000000000,
        "type": "fixed",
        "recent_data": [
            ("600519.XSHG", "2026-03-14", 1800, 1820, 1790, 1810, 1000000, 1810000000),
            ("600519.XSHG", "2026-03-13", 1780, 1800, 1770, 1795, 900000, 1611000000),
            ("600519.XSHG", "2026-03-12", 1760, 1785, 1750, 1780, 850000, 1513000000),
        ]
    }

    result = analyzer.analyze_stock(test_stock)

    print(f"\n分析结果:")
    print(f"  股票：{result['name']} ({result['code']})")
    print(f"  评级：{result['rating']} {'⭐' * result['stars']}")
    print(f"  策略：{result['strategy']}")
    print(f"  理由：{len(result['reasons'])} 条")
    print(f"  风险：{len(result['risks'])} 条")

    return result


if __name__ == "__main__":
    test_analyzer()
