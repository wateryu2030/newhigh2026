#!/usr/bin/env python3
"""
列出可用的Gemini模型
"""

import os
from google.genai import Client

# 设置API Key
api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyA7jsyrYWE3_uT8AirnhxAQVavVC4nYxQQ")

# 创建客户端
client = Client(api_key=api_key)

# 列出模型
print("可用的Gemini模型:")
models = client.models.list()
for model in models:
    print(f"  - {model.name}")
    print(f"    支持的方法: {model.supported_generation_methods}")
    print()