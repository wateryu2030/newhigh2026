#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 快速运行脚本
在项目根目录激活 venv 后执行: python run_akshare.py
或直接: ./scripts/run.sh
"""
import sys

def main():
    try:
        import akshare as ak
        from akshare._version import __version__ as ak_version
    except ImportError:
        print("请先激活虚拟环境: source venv/bin/activate (Linux/Mac) 或 venv\\Scripts\\activate (Windows)")
        sys.exit(1)

    print(f"AKShare 版本: {ak_version}")
    print("示例：获取 A 股 000001 近期日线（前 5 条）")
    try:
        # 从子模块调用，避免依赖 akshare 根模块全部导出
        from akshare.stock_feature.stock_hist_em import stock_zh_a_hist
        df = stock_zh_a_hist(symbol="000001", period="daily", start_date="20250101", end_date="20250601", adjust="")
        print(df.head())
    except Exception as e:
        print(f"获取数据时出错（可能与网络或接口限制有关）: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
