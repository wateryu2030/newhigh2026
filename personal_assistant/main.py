#!/usr/bin/env python3
"""
个人量化投资助手 - 主程序
功能：每日自动分析股票，生成报告，推送到微信和邮件
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加项目路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# 导入模块
sys.path.insert(0, os.path.join(ROOT, "personal_assistant", "src"))

from stock_screener import StockScreener
from ai_analyzer import AIStockAnalyzer
from report_generator import ReportGenerator
from pusher import ReportPusher


class PersonalAssistant:
    """个人量化投资助手"""
    
    def __init__(self, config: dict = None):
        """
        初始化助手
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.date = datetime.now().strftime("%Y-%m-%d")
        
        # 初始化组件
        print("🚀 初始化个人量化投资助手...")
        
        # 股票筛选器
        fixed_stocks = self.config.get("fixed_stocks", [])
        self.screener = StockScreener(fixed_stocks=fixed_stocks)
        
        # AI分析器
        api_key = self.config.get("deepseek_api_key")
        self.analyzer = AIStockAnalyzer(api_key=api_key)
        
        # 报告生成器
        self.report_gen = ReportGenerator()
        
        # 推送器
        self.pusher = ReportPusher()
        
        print("✅ 初始化完成\n")
    
    def run(self) -> dict:
        """
        运行一次完整分析流程
        
        Returns:
            运行结果字典
        """
        print(f"=" * 60)
        print(f"📊 个人量化投资助手 - 每日分析")
        print(f"日期：{self.date}")
        print(f"=" * 60)
        
        result = {
            "date": self.date,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stocks_analyzed": 0,
            "push_success": False,
            "analysis_results": []
        }
        
        try:
            # Step 1: 筛选股票
            print("\n📋 Step 1: 筛选股票池...")
            stock_pool = self.screener.get_stock_pool(
                fixed_count=self.config.get("fixed_count", 10),
                dynamic_count=self.config.get("dynamic_count", 10)
            )
            
            if not stock_pool:
                print("❌ 股票池为空，终止分析")
                result["error"] = "股票池为空"
                return result
            
            result["stocks_analyzed"] = len(stock_pool)
            print(f"✅ 获得 {len(stock_pool)} 只股票\n")
            
            # Step 2: AI分析
            print("\n🤖 Step 2: AI 分析股票...")
            analysis_results = []
            
            for i, stock in enumerate(stock_pool, 1):
                print(f"  分析 [{i}/{len(stock_pool)}]: {stock['name']} ({stock['code'][:6]})...")
                result = self.analyzer.analyze_stock(stock)
                analysis_results.append(result)
                
                # 简单延迟，避免API限制
                import time
                time.sleep(0.5)
            
            result["analysis_results"] = analysis_results
            print(f"✅ 完成 {len(analysis_results)} 只股票分析\n")
            
            # Step 3: 生成报告
            print("\n📝 Step 3: 生成报告...")
            wechat_report = self.report_gen.generate_wechat_report(analysis_results)
            email_report = self.report_gen.generate_email_report(analysis_results)
            print(f"✅ 报告生成完成\n")
            
            # Step 4: 推送报告
            print("\n📤 Step 4: 推送报告...")
            push_results = self.pusher.push_report(
                wechat_content=wechat_report,
                email_subject=email_report["subject"],
                email_html=email_report["html"],
                email_text=email_report["text"]
            )
            
            result["push_results"] = push_results
            result["push_success"] = push_results.get("wechat") or push_results.get("email")
            
            # Step 5: 保存报告到本地（备用）
            print("\n💾 Step 5: 保存报告到本地...")
            self._save_report(wechat_report, email_report["html"])
            
            # 完成
            print("\n" + "=" * 60)
            print("✅ 每日分析完成！")
            print("=" * 60)
            
            # 统计
            buy_count = sum(1 for r in analysis_results if r.get("rating") == "买入")
            hold_count = sum(1 for r in analysis_results if r.get("rating") == "持有")
            sell_count = sum(1 for r in analysis_results if r.get("rating") == "卖出")
            
            print(f"\n📊 统计:")
            print(f"  买入：{buy_count} 只")
            print(f"  持有：{hold_count} 只")
            print(f"  卖出：{sell_count} 只")
            print(f"\n📤 推送:")
            print(f"  微信：{'✅' if push_results.get('wechat') else '❌'}")
            print(f"  邮件：{'✅' if push_results.get('email') else '❌'}")
            
            return result
            
        except Exception as e:
            print(f"\n❌ 分析过程出错：{e}")
            result["error"] = str(e)
            return result
    
    def _save_report(self, wechat_report: str, email_html: str):
        """保存报告到本地"""
        output_dir = os.path.join(ROOT, "personal_assistant", "reports")
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存微信报告
        wechat_path = os.path.join(output_dir, f"report_{self.date}.txt")
        with open(wechat_path, "w", encoding="utf-8") as f:
            f.write(wechat_report)
        
        # 保存邮件报告
        email_path = os.path.join(output_dir, f"report_{self.date}.html")
        with open(email_path, "w", encoding="utf-8") as f:
            f.write(email_html)
        
        print(f"✅ 报告已保存到：{output_dir}")


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(ROOT, "personal_assistant", "config.json")
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # 创建默认配置
        default_config = {
            "fixed_count": 10,
            "dynamic_count": 10,
            "fixed_stocks": [
                "600519.XSHG",  # 贵州茅台
                "000858.XSHE",  # 五粮液
                "300750.XSHE",  # 宁德时代
                "002594.XSHE",  # 比亚迪
                "601318.XSHG",  # 中国平安
                "600036.XSHG",  # 招商银行
                "000538.XSHE",  # 云南白药
                "600276.XSHG",  # 恒瑞医药
            ]
        }
        
        # 保存默认配置
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"📝 创建默认配置文件：{config_path}")
        
        return default_config


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🤖 个人量化投资助手 v1.0")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    
    # 从环境变量加载 API Keys
    if "DEEPSEEK_API_KEY" not in config:
        config["deepseek_api_key"] = os.getenv("DEEPSEEK_API_KEY")
    
    # 创建助手
    assistant = PersonalAssistant(config)
    
    # 运行分析
    result = assistant.run()
    
    # 返回结果
    if result.get("error"):
        print(f"\n❌ 运行失败：{result['error']}")
        sys.exit(1)
    else:
        print(f"\n✅ 运行成功！")
        sys.exit(0)


if __name__ == "__main__":
    main()
