"""
daily_stock_analysis 主模块
提供完整的股票分析流程
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .config import DailyStockConfig
from .data_fetcher import DataFetcher
from .news_analyzer import NewsAnalyzer
from .ai_decision import AIDecisionMaker
from .notification import NotificationSender


class DailyStockAnalyzer:
    """每日股票分析器主类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化分析器

        Args:
            config_path: 配置文件路径
        """
        self.config = DailyStockConfig.from_yaml(config_path)
        self.logger = self._setup_logger()

        # 验证配置
        errors = self.config.validate()
        if errors:
            self.logger.warning("配置验证警告: %s", errors)

        # 初始化组件
        self.data_fetcher = DataFetcher(self.config)
        self.news_analyzer = NewsAnalyzer(self.config)
        self.ai_decision_maker = AIDecisionMaker(self.config)
        self.notification_sender = NotificationSender(self.config)

        self.logger.info("DailyStockAnalyzer初始化完成，配置: %s", self.config.to_dict())

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"daily_stock_analysis.{self.config.name}")

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    async def analyze_market(
        self, markets: Optional[List[str]] = None, symbols: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        分析指定市场和股票

        Args:
            markets: 市场列表，如["A", "HK", "US"]
            symbols: 按市场分类的股票代码字典

        Returns:
            分析结果字典
        """
        start_time = datetime.now()
        self.logger.info("开始市场分析: markets=%s, symbols=%s", markets, symbols)

        # 使用配置中的默认值
        if markets is None:
            markets = self.config.markets

        if symbols is None:
            symbols = self.config.symbol_examples

        results = {
            "timestamp": start_time.isoformat(),
            "markets": markets,
            "symbols": symbols,
            "data": {},
            "news": {},
            "analysis": {},
            "recommendations": {},
            "summary": {},
            "duration_seconds": 0,
        }

        try:
            # 1. 获取数据
            self.logger.info("步骤1: 获取市场数据")
            market_data = await self.data_fetcher.fetch_market_data(markets, symbols)
            results["data"] = market_data

            # 2. 获取新闻
            self.logger.info("步骤2: 获取新闻数据")
            news_data = await self.news_analyzer.fetch_news(markets)
            results["news"] = news_data

            # 3. AI分析
            self.logger.info("步骤3: AI分析")
            analysis_results = await self.ai_decision_maker.analyze(
                market_data=market_data, news_data=news_data
            )
            results["analysis"] = analysis_results

            # 4. 生成推荐
            self.logger.info("步骤4: 生成投资推荐")
            recommendations = await self.ai_decision_maker.generate_recommendations(
                analysis_results
            )
            results["recommendations"] = recommendations

            # 5. 生成摘要
            self.logger.info("步骤5: 生成分析摘要")
            summary = await self.ai_decision_maker.generate_summary(results)
            results["summary"] = summary

            # 计算耗时
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            results["duration_seconds"] = duration

            self.logger.info("市场分析完成，耗时：%.2f 秒", duration)

            return results

        except Exception as e:
            self.logger.error("市场分析失败: %s", e, exc_info=True)
            results["error"] = str(e)
            return results

    async def get_recommendations(
        self, analysis_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        获取投资推荐（可基于现有分析结果）

        Args:
            analysis_results: 可选的分析结果，如果为None则重新分析

        Returns:
            推荐结果
        """
        if analysis_results is None:
            self.logger.info("未提供分析结果，重新运行完整分析")
            analysis_results = await self.analyze_market()

        try:
            recommendations = await self.ai_decision_maker.generate_recommendations(
                analysis_results
            )
            return recommendations
        except Exception as e:
            self.logger.error("生成推荐失败: %s", e, exc_info=True)
            return {"error": str(e)}

    async def send_notifications(
        self, results: Dict[str, Any], channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        发送通知

        Args:
            results: 分析结果
            channels: 通知渠道列表

        Returns:
            各渠道发送状态字典
        """
        if channels is None:
            channels = self.config.notification_channels

        self.logger.info("发送通知到渠道: %s", channels)

        try:
            status = await self.notification_sender.send_all(results, channels)
            return status
        except Exception as e:
            self.logger.error("发送通知失败: %s", e, exc_info=True)
            return {channel: False for channel in channels}

    async def run_daily_analysis(self) -> Dict[str, Any]:
        """
        运行每日分析（完整流程）

        Returns:
            完整分析结果
        """
        self.logger.info("开始每日分析流程")

        # 运行分析
        analysis_results = await self.analyze_market()

        # 发送通知
        if self.config.enabled and analysis_results.get("error") is None:
            notification_status = await self.send_notifications(analysis_results)
            analysis_results["notification_status"] = notification_status

        self.logger.info("每日分析流程完成")
        return analysis_results

    def run_sync(self) -> Dict[str, Any]:
        """
        同步运行每日分析

        Returns:
            分析结果
        """
        return asyncio.run(self.run_daily_analysis())


# 简单的命令行接口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="每日股票分析器")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--markets", "-m", nargs="+", help="市场列表")
    parser.add_argument("--symbols", "-s", nargs="+", help="股票代码列表")
    parser.add_argument("--test", "-t", action="store_true", help="测试模式")

    args = parser.parse_args()

    # 创建分析器
    analyzer = DailyStockAnalyzer(args.config)

    if args.test:
        print("测试模式: 检查配置和组件")
        print(f"配置: {analyzer.config.to_dict()}")
        print("测试完成")
    else:
        # 运行分析
        print("开始股票分析...")
        results = analyzer.run_sync()

        if "error" in results:
            print(f"分析失败: {results['error']}")
        else:
            print(f"分析完成，耗时: {results['duration_seconds']:.2f}秒")
            print(f"分析摘要: {results.get('summary', {}).get('overview', '无摘要')}")
