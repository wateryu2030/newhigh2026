# -*- coding: utf-8 -*-
"""
AI 策略生成器：使用 LLM 根据描述生成可执行的 Python 策略代码。
要求：输入 df（含 open/high/low/close/volume），输出带 buy/sell 列或 equity 的 DataFrame。
"""
from __future__ import annotations
import os
from typing import Optional


# 策略代码模板：LLM 只需补全 strategy 函数体逻辑
STRATEGY_TEMPLATE = '''
import pandas as pd
import numpy as np

def strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入 df 列: date, open, high, low, close, volume (或 datetime index)
    输出 DataFrame 需含: signal (1=买 -1=卖 0=持有) 或 buy/sell 列，以及可选 equity 列。
    """
    out = df.copy()
    if "date" not in out.columns and out.index.name is not None:
        out["date"] = out.index.astype(str).str[:10]
    # 以下由 LLM 生成
    {strategy_body}
    return out
'''


class StrategyGenerator:
    """使用 OpenAI 兼容 API 生成策略代码。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_API_BASE", "").rstrip("/")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
            return self._client
        except Exception as e:
            raise RuntimeError(f"OpenAI client 初始化失败: {e}，请设置 OPENAI_API_KEY") from e

    def generate(self, idea: str, indicators: Optional[list[str]] = None) -> str:
        """
        根据策略描述生成策略 Python 代码。
        :param idea: 策略思想描述
        :param indicators: 可选指标列表，如 ["ma5", "ma20", "rsi"]
        :return: 完整可执行的策略代码字符串
        """
        ind_text = ""
        if indicators:
            ind_text = f"请使用以下指标：{', '.join(indicators)}。"
        prompt = f"""你是一个量化策略研究员。请生成一个 Python 函数体（仅函数体，不要 def strategy 和 return 以外的重复代码）。

要求：
1. 使用 pandas/numpy，变量名为 df（DataFrame 已有列 open, high, low, close, volume，可能有 date）。
2. 在 out 上增加 signal 列：1=买入，-1=卖出，0=持有。若用 buy/sell 列也可，但最后需有 signal 或 buy/sell 供回测。
3. 禁止使用未来数据（只能用到当前及之前行）。
4. 代码简洁，不超过 30 行。
{ind_text}

策略思想：
{idea}

只输出函数体代码（给 out 赋值 signal 或 buy/sell 的逻辑），不要解释。"""
        try:
            client = self._get_client()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500,
            )
            body = (resp.choices[0].message.content or "").strip()
            # 去掉可能的 markdown 代码块
            if body.startswith("```"):
                lines = body.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                body = "\n".join(lines)
            return STRATEGY_TEMPLATE.format(strategy_body=body or "out['signal'] = 0")
        except Exception as e:
            raise RuntimeError(f"LLM 生成策略失败: {e}") from e
