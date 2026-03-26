#!/usr/bin/env python3
"""
更新数据库配置文件 - 将market.duckdb和quant.duckdb引用更新为quant_system.duckdb
"""

import os
import re
from pathlib import Path

def update_file_content(filepath):
    """更新单个文件的内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 替换market.duckdb
        content = re.sub(r'\bmarket\.duckdb\b', 'quant_system.duckdb', content)

        # 替换quant.duckdb
        content = re.sub(r'\bquant\.duckdb\b', 'quant_system.duckdb', content)

        # 替换路径中的引用
        content = re.sub(r'data/market\.duckdb', 'data/quant_system.duckdb', content)
        content = re.sub(r'data/quant\.duckdb', 'data/quant_system.duckdb', content)

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False

    except Exception as e:
        print(f"  错误更新 {filepath}: {e}")
        return False

def main():
    """主函数"""
    print("=== 更新数据库配置文件 ===")
    print("将market.duckdb和quant.duckdb引用更新为quant_system.duckdb")
    print()

    # 搜索所有Python文件
    python_files = []
    for root, dirs, files in os.walk('.'):
        # 跳过一些目录
        if any(skip in root for skip in ['.git', '__pycache__', 'venv', '.venv', 'node_modules']):
            continue

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    # 搜索包含数据库引用的文件
    files_to_update = []
    for filepath in python_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'quant_system.duckdb' in content or 'quant_system.duckdb' in content:
                files_to_update.append(filepath)
        except:
            pass

    print(f"发现 {len(files_to_update)} 个文件包含数据库引用")
    print()

    # 更新文件
    updated_count = 0
    for filepath in files_to_update:
        print(f"更新 {filepath}...", end="")
        if update_file_content(filepath):
            print(" ✅")
            updated_count += 1
        else:
            print(" ⚠️ 无需更新")

    print()
    print(f"📊 更新完成: {updated_count} 个文件已更新")

    # 检查环境文件
    print()
    print("=== 检查环境配置文件 ===")

    env_files = ['.env', '.env.example']
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"检查 {env_file}...", end="")
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'quant_system.duckdb' in content or 'quant_system.duckdb' in content:
                print(" ⚠️ 包含旧数据库引用，建议更新")
            else:
                print(" ✅ 正常")
        else:
            print(f"{env_file} 不存在")

    print()
    print("✅ 配置文件更新完成!")
    print("注意: 请测试更新后的功能是否正常")

if __name__ == "__main__":
    main()