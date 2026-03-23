"""
daily_stock_analysis 策略模块

LLM驱动的智能股票分析器，集成到newhigh量化平台。
提供A股、港股、美股的多数据源分析、实时新闻、AI决策和推送功能。
"""

__version__ = "0.1.0"
__author__ = "OpenClaw Integration Team"
__description__ = "LLM驱动的 A/H/美股智能分析器"

from .main import DailyStockAnalyzer
from .config import DailyStockConfig
from .data_fetcher import DataFetcher
from .news_analyzer import NewsAnalyzer
from .ai_decision import AIDecisionMaker
from .notification import NotificationSender

__all__ = [
    "DailyStockAnalyzer",
    "DailyStockConfig",
    "DataFetcher",
    "NewsAnalyzer",
    "AIDecisionMaker",
    "NotificationSender",
]
