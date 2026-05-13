#!/usr/bin/env python3
"""
超快速Gemini测试
直接测试API是否工作
"""

import os
from google.genai import Client

# 设置API Key
api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyA7jsyrYWE3_uT8AirnhxAQVavVC4nYxQQ")
print(f"使用API Key: {api_key[:15]}...")

# 创建客户端
client = Client(api_key=api_key)

# 使用gemini-2.5-flash模型
model = "gemini-2.5-flash"

# 简单测试
print("测试Gemini API...")
response = client.models.generate_content(
    model=model,
    contents="用一句话回答：今天的天气怎么样？"
)
print(f"响应: {response.text}")

# 股票分析测试
print("\n测试股票分析...")
stock_prompt = """请分析平安银行(000001)股票：
1. 当前股价15.80元
2. 市盈率8.5倍
3. 市净率0.9倍
4. 股息率3.2%

请给出简短的投资建议（不超过3句话）。"""

stock_response = client.models.generate_content(
    model=model,
    contents=stock_prompt
)
print(f"股票分析: {stock_response.text}")

print("\n✅ Gemini API测试成功！")