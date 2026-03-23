"""
常量定义

统一常量管理，避免硬编码和魔法数字。
"""

from __future__ import annotations
from pathlib import Path

# === 项目路径 ===
LIB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LIB_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "quant_system.duckdb"

# === 数据库配置 ===
DEFAULT_DB_READ_ONLY = False
DB_CONNECTION_TIMEOUT = 30  # 秒

# === A 股市场配置 ===
ASHARE_MARKET_OPEN_TIME = "09:30"
ASHARE_MARKET_CLOSE_TIME = "15:00"
ASHARE_TRADING_DAYS_PER_YEAR = 242

# === 涨跌停配置 ===
LIMIT_UP_RATIO_MAIN = 0.10      # 主板 10%
LIMIT_UP_RATIO_STAR = 0.20      # 科创板/创业板 20%
LIMIT_UP_RATIO_BSE = 0.30       # 北交所 30%

# === 信号评分配置 ===
SIGNAL_SCORE_MIN = 0.0
SIGNAL_SCORE_MAX = 100.0
SIGNAL_SCORE_THRESHOLD = 60.0   # 信号触发阈值

# === AI 模型配置 ===
DEFAULT_LLM_PROVIDER = "dashscope"
DEFAULT_LLM_MODEL = "qwen3.5-plus"
DEFAULT_SENTIMENT_THRESHOLD = 0.5

# === 定时任务配置 ===
NEWS_COLLECTION_INTERVAL = 3600     # 新闻采集间隔 (秒)
SCANNER_INTERVAL = 300              # 扫描器间隔 (秒)
EMOTION_UPDATE_INTERVAL = 1800      # 情绪更新间隔 (秒)

# === OpenClaw 配置 ===
OPENCLAW_EVOLUTION_POPULATION_LIMIT = 100
OPENCLAW_EVOLUTION_GENERATION_LIMIT = 10
OPENCLAW_BACKTEST_DAYS = 60

# === 日志配置 ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# === API 配置 ===
API_HOST = "0.0.0.0"
API_PORT = 8000
API_PREFIX = "/api"

# === 前端配置 ===
FRONTEND_HOST = "localhost"
FRONTEND_PORT = 3000
