#!/usr/bin/env python3
"""
个人量化投资助手 - 主程序
功能：整合股票筛选、AI 分析、报告生成和推送
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加项目路径
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT, "src")
sys.path.insert(0, SRC_DIR)

from stock_screener import StockScreener
from ai_analyzer import AIStockAnalyzer
from report_generator import ReportGenerator
from pusher import ReportPusher


def main():
    """主函数"""
    print("=" * 60)
    print("📊 个人量化投资助手")
    print("=" * 60)
    print(f"运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 加载配置
    config = load_config()

    # Step 1: 股票筛选
    print("📝 Step 1: 筛选股票...")
    screener = StockScreener(
        db_path=config.get("db_path"),
        fixed_stocks=config.get("fixed_stocks")
    )
    stock_pool = screener.get_stock_pool(
        fixed_count=config.get("fixed_count", 10),
        dynamic_count=config.get("dynamic_count", 10)
    )

    if not stock_pool:
        print("❌ 股票池为空，退出")
        return

    print(f"✅ 筛选完成：{len(stock_pool)} 只股票")
    print()

    # Step 2: AI 分析
    print("🤖 Step 2: AI 分析...")
    analyzer = AIStockAnalyzer(api_key=config.get("deepseek_api_key"))

    analysis_results = []
    for i, stock in enumerate(stock_pool, 1):
        print(f"  [{i}/{len(stock_pool)}] 分析 {stock['name']} ({stock['code'][:6]})...", end="")
        result = analyzer.analyze_stock(stock)
        analysis_results.append(result)
        print(f" {result.get('rating', 'N/A')} {'⭐' * result.get('stars', 0)}")

    print(f"✅ 分析完成：{len(analysis_results)} 只股票")
    print()

    # Step 3: 生成报告
    print("📝 Step 3: 生成报告...")
    generator = ReportGenerator()

    wechat_report = generator.generate_wechat_report(analysis_results)
    email_report = generator.generate_email_report(analysis_results)

    print("✅ 报告生成完成")
    print()

    # Step 4: 推送报告
    print("📤 Step 4: 推送报告...")
    pusher = ReportPusher()

    push_results = pusher.push_report(
        wechat_content=wechat_report,
        email_subject=email_report["subject"],
        email_html=email_report["html"],
        email_text=email_report["text"]
    )
    print()

    # Step 5: 保存报告
    print("💾 Step 5: 保存报告...")
    report_dir = Path(ROOT) / "reports"
    report_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # 保存微信版本
    wechat_path = report_dir / f"report_{date_str}.txt"
    with open(wechat_path, "w", encoding="utf-8") as f:
        f.write(wechat_report)

    # 保存 HTML 版本
    html_path = report_dir / f"report_{date_str}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(email_report["html"])

    # 保存 JSON 版本（用于业绩跟踪）
    json_path = report_dir / f"analysis_{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "timestamp": datetime.now().isoformat(),
            "stock_count": len(analysis_results),
            "results": analysis_results
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 报告已保存到：{report_dir}")
    print(f"   - {wechat_path.name}")
    print(f"   - {html_path.name}")
    print(f"   - {json_path.name}")
    print()

    # 总结
    print("=" * 60)
    print("📊 执行完成")
    print("=" * 60)
    print(f"分析股票：{len(analysis_results)} 只")
    print(f"买入评级：{sum(1 for r in analysis_results if r.get('rating') == '买入')} 只")
    print(f"持有评级：{sum(1 for r in analysis_results if r.get('rating') == '持有')} 只")
    print(f"卖出评级：{sum(1 for r in analysis_results if r.get('rating') == '卖出')} 只")
    print()
    print(f"推送状态:")
    print(f"  微信：{'✅' if push_results.get('wechat') else '⚠️ 未配置'}")
    print(f"  邮件：{'✅' if push_results.get('email') else '⚠️ 未配置'}")
    print()
    print("下次运行时间：明天 08:00")
    print("=" * 60)


def load_config() -> dict:
    """加载配置"""
    config_path = Path(ROOT) / "config.json"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    # 从环境变量加载
    config.setdefault("db_path", os.getenv("QUANT_SYSTEM_DUCKDB_PATH"))
    config.setdefault("deepseek_api_key", os.getenv("DEEPSEEK_API_KEY"))
    config.setdefault("serverchan_sendkey", os.getenv("SERVERCHAN_SENDKEY"))

    # 默认配置
    config.setdefault("fixed_count", 10)
    config.setdefault("dynamic_count", 10)

    return config


if __name__ == "__main__":
    main()
