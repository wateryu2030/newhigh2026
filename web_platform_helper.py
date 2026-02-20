#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web平台辅助工具 - 动态修改策略文件以支持股票代码选择
"""
import os
import re
import shutil
from datetime import datetime


def inject_stock_code_to_strategy(strategy_path, stock_code, output_path=None):
    """
    将股票代码注入到策略文件中
    对于不支持动态股票代码的策略，创建一个临时版本
    """
    if not os.path.exists(strategy_path):
        raise FileNotFoundError(f"策略文件不存在: {strategy_path}")
    
    with open(strategy_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否是 universal_ma_strategy.py（支持环境变量）
    if 'universal_ma_strategy' in strategy_path or 'STOCK_CODE' in content or 'os.environ.get' in content:
        # 已经支持动态股票代码，不需要修改
        return strategy_path
    
    # 对于其他策略，尝试替换硬编码的股票代码
    # 查找常见的股票代码模式（使用全局替换，替换所有匹配）
    patterns = [
        (r'context\.s1\s*=\s*["\'][^"\']+["\']', f'context.s1 = "{stock_code}"'),  # 替换所有 context.s1 = "..."
        (r'STOCK_CODE\s*=\s*["\'][^"\']+["\']', f'STOCK_CODE = "{stock_code}"'),  # 替换所有 STOCK_CODE = "..."
        (r'context\.stock\s*=\s*["\'][^"\']+["\']', f'context.stock = "{stock_code}"'),  # 替换所有 context.stock = "..."
    ]
    
    modified = False
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)  # 全局替换所有匹配
            modified = True
    
    if not modified:
        # 仅当策略使用单股票（context.s1 / context.stock）时才在 init 开头注入
        if 'def init(context):' in content and ('context.s1' in content or 'context.stock' in content):
            # 替换时不要带尾部空格，否则下一行会多出缩进导致 IndentationError
            replacement = f'def init(context):\n    # 动态设置股票代码\n    context.s1 = "{stock_code}"\n'
            content = re.sub(r'def init\(context\):\s*\n', replacement, content, count=1)
            modified = True
    
    # 多股票策略（如行业轮动、动量+均值回归）无需注入单股票代码，直接使用原文件
    if not modified:
        return strategy_path
    
    if not output_path:
        # 创建临时文件
        base_name = os.path.basename(strategy_path)
        name, ext = os.path.splitext(base_name)
        output_path = f"strategies/.tmp_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_path


if __name__ == "__main__":
    # 测试
    test_strategy = "strategies/simple_ma_strategy.py"
    if os.path.exists(test_strategy):
        result = inject_stock_code_to_strategy(test_strategy, "600745.XSHG")
        print(f"生成临时策略文件: {result}")
