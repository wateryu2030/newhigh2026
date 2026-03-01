# -*- coding: utf-8 -*-
"""
LLM 客户端：集成 DeepSeek API 进行非结构化文本分析和推理
"""
from __future__ import annotations
import os
import sys
import json
import requests
from typing import Any, Dict, List, Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


class DeepSeekClient:
    """
    DeepSeek API 客户端
    用于主题提取、情感分析、策略推荐等NLP任务
    """
    
    API_BASE = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: int = 60,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model
        self.timeout = timeout
        
        if not self.api_key:
            print("[DeepSeekClient] Warning: API Key未设置，LLM功能将不可用")
    
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """调用DeepSeek API"""
        if not self.api_key:
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            response = requests.post(
                f"{self.API_BASE}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"[DeepSeekClient] API错误: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"[DeepSeekClient] 请求失败: {e}")
            return None
    
    def extract_themes(self, news_texts: List[str]) -> List[Dict[str, Any]]:
        """
        从新闻文本中提取热门主题和行业概念
        
        :param news_texts: 新闻文本列表
        :return: 主题列表，包含名称、热度、相关概念
        """
        if not news_texts:
            return []
        
        # 构造提示词
        news_combined = "\n---\n".join(news_texts[:20])  # 最多取20条
        
        system_prompt = """你是一位专业的财经分析师。请从以下财经新闻中提取热门投资主题和行业概念。
对每个主题给出：
1. 主题名称（简洁的2-6个字）
2. 热度评分（0-100）
3. 相关概念/板块
4. 简要逻辑说明

请以JSON格式返回，格式如下：
{
  "themes": [
    {"name": "低空经济", "heat": 85, "concepts": ["无人机", "通用航空"], "logic": "政策利好不断，产业加速发展"},
    ...
  ]
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下新闻：\n{news_combined}"},
        ]
        
        response = self._call_api(messages, temperature=0.5, max_tokens=2000)
        if not response:
            return []
        
        # 解析JSON响应
        try:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("themes", [])
            return []
        except Exception as e:
            print(f"[DeepSeekClient] 解析主题失败: {e}")
            return []
    
    def analyze_theme_regime(
        self,
        theme_name: str,
        fund_flow: float,
        price_change: float,
        sentiment: float,
    ) -> Dict[str, Any]:
        """
        分析主题所处的生命周期阶段
        
        :param theme_name: 主题名称
        :param fund_flow: 资金流向评分(0-100)
        :param price_change: 涨跌幅(%) 
        :param sentiment: 情绪评分(0-100)
        :return: 包含stage(启动/加速/分歧/衰退)和confidence的字典
        """
        system_prompt = """你是一位资深的市场周期分析师。请根据提供的量化数据，
判断该主题当前所处的生命周期阶段：
- 启动期(early): 资金刚开始流入，涨幅温和，情绪初热
- 加速期(accelerating): 资金大幅流入，涨幅强劲，情绪高涨
- 分歧期(divergence): 资金流入放缓，波动加大，情绪分化
- 衰退期(declining): 资金流出，涨幅回落，情绪冷却

请以JSON格式返回：{"stage": "启动期", "confidence": 0.85, "reason": "说明"}"""
        
        user_prompt = f"""主题: {theme_name}
资金流向评分: {fund_flow}/100
近期涨跌幅: {price_change}%
市场情绪评分: {sentiment}/100

请判断该主题的生命周期阶段。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = self._call_api(messages, temperature=0.3, max_tokens=1000)
        if not response:
            return {"stage": "未知", "confidence": 0.0, "reason": "LLM分析失败"}
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"stage": "未知", "confidence": 0.0, "reason": "无法解析"}
        except:
            return {"stage": "未知", "confidence": 0.0, "reason": "解析错误"}
    
    def select_strategy_for_theme(
        self,
        theme_name: str,
        theme_regime: str,
        tier: str,
    ) -> Dict[str, Any]:
        """
        为主题选择最合适的交易策略
        
        :param theme_name: 主题名称
        :param theme_regime: 生命周期阶段
        :param tier: 梯队(Leaders/Rising/Watch)
        :return: 策略建议
        """
        system_prompt = """你是一位量化策略专家。请根据主题的生命周期和梯队位置，
推荐最适合的交易策略：

可选策略:
1. 趋势突破(Trend Breakout) - 适合加速期的领涨股
2. 回踩反转(Pullback Reversal) - 适合上升期的分歧回调
3. 均值回归(Mean Reversion) - 适合震荡期的低吸
4. 事件动量(Event Momentum) - 适合突发高热度事件
5. 资金跟随(Money Follow) - 适合资金主导但趋势不明
6. 低关注度潜伏(Low Attention) - 适合底部建仓阶段

请以JSON格式返回策略建议。"""
        
        user_prompt = f"""主题: {theme_name}
生命周期: {theme_regime}
梯队位置: {tier}

请推荐交易策略。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = self._call_api(messages, temperature=0.4, max_tokens=1000)
        if not response:
            return {"strategy": "趋势突破", "reason": "默认策略", "confidence": 0.5}
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"strategy": "趋势突破", "reason": "默认策略", "confidence": 0.5}
        except:
            return {"strategy": "趋势突破", "reason": "解析失败", "confidence": 0.5}
    
    def analyze_stock_for_pick(
        self,
        stock_data: Dict[str, Any],
        strategy: str,
    ) -> Dict[str, Any]:
        """
        LLM深度分析个股，生成交易计划
        
        :param stock_data: 包含因子数据的字典
        :param strategy: 策略类型
        :return: 包含逻辑、止损、观察点的分析结果
        """
        system_prompt = """你是一位资深的技术分析研究员。请基于提供的量化数据进行定性分析，
判断该股票是否符合交易策略要求，并给出具体交易计划。

必须给出:
1. 是否通过筛选(pass/fail)
2. 买入逻辑(清晰具体)
3. 止损条件(stop_loss)
4. 次日观察点(observe)
5. 风险等级(low/medium/high)

请以JSON格式返回。"""
        
        user_prompt = f"""策略: {strategy}
股票数据: {json.dumps(stock_data, ensure_ascii=False, indent=2)}

请分析并给出交易计划。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = self._call_api(messages, temperature=0.3, max_tokens=1500)
        if not response:
            return {
                "pass": False,
                "logic": "LLM分析失败",
                "stop_loss": "N/A",
                "observe": "N/A",
                "risk": "high",
            }
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {
                "pass": False,
                "logic": "解析失败",
                "stop_loss": "N/A",
                "observe": "N/A",
                "risk": "high",
            }
        except:
            return {
                "pass": False,
                "logic": "解析错误",
                "stop_loss": "N/A",
                "observe": "N/A",
                "risk": "high",
            }
