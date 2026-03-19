"""
配置管理模块
处理daily_stock_analysis的配置加载和验证
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

# yaml作为可选依赖
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None


@dataclass
class DailyStockConfig:
    """daily_stock_analysis配置类"""

    # 基本配置
    enabled: bool = True
    name: str = "daily_stock_analysis"

    # 数据源配置
    data_sources: List[str] = field(default_factory=lambda: ["akshare", "tushare", "yahoo_finance"])

    # 市场配置
    markets: List[str] = field(default_factory=lambda: ["A", "HK", "US"])

    # 股票代码配置（示例）
    symbol_examples: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "A": ["000001.SZ", "000002.SZ", "600000.SH"],
            "HK": ["00700.HK", "00941.HK", "01299.HK"],
            "US": ["AAPL", "GOOGL", "TSLA"],
        }
    )

    # 新闻源配置
    news_sources: List[str] = field(default_factory=lambda: ["xinhua", "caixin", "government"])

    # AI配置
    ai_model: str = "gemini-pro"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1000

    # 推送配置
    notification_channels: List[str] = field(
        default_factory=lambda: ["telegram", "email", "webhook"]
    )

    # 调度配置
    schedule: str = "0 9 * * *"  # 每天9点运行
    run_on_startup: bool = False

    # 分析配置
    analysis_depth: str = "standard"  # simple/standard/deep
    include_technical: bool = True
    include_fundamental: bool = True
    include_sentiment: bool = True

    @classmethod
    def from_yaml(cls, config_path: Optional[str] = None) -> "DailyStockConfig":
        """
        从YAML或JSON文件加载配置

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径

        Returns:
            DailyStockConfig实例
        """
        if config_path is None:
            # 尝试从多个位置查找配置文件
            possible_paths = [
                "config/daily_stock_analysis.yaml",
                "config/daily_stock_analysis.json",
                "../config/daily_stock_analysis.yaml",
                "../config/daily_stock_analysis.json",
                "../../config/daily_stock_analysis.yaml",
                "../../config/daily_stock_analysis.json",
            ]

            for path in possible_paths:
                if Path(path).exists():
                    config_path = path
                    break

            if config_path is None:
                # 使用默认配置
                return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.endswith(".json"):
                    config_data = json.load(f)
                elif config_path.endswith(".yaml") or config_path.endswith(".yml"):
                    if not YAML_AVAILABLE:
                        print("警告: yaml模块未安装，无法加载YAML配置文件，使用默认配置")
                        return cls()
                    config_data = yaml.safe_load(f)
                else:
                    # 尝试自动检测格式
                    content = f.read()
                    try:
                        config_data = json.loads(content)
                    except json.JSONDecodeError:
                        if YAML_AVAILABLE:
                            config_data = yaml.safe_load(content)
                        else:
                            print("警告: 无法解析配置文件格式，使用默认配置")
                            return cls()

            # 从字典创建配置对象
            return cls(**config_data)
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}, 使用默认配置")
            return cls()

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            "enabled": self.enabled,
            "name": self.name,
            "data_sources": self.data_sources,
            "markets": self.markets,
            "symbol_examples": self.symbol_examples,
            "news_sources": self.news_sources,
            "ai_model": self.ai_model,
            "ai_temperature": self.ai_temperature,
            "ai_max_tokens": self.ai_max_tokens,
            "notification_channels": self.notification_channels,
            "schedule": self.schedule,
            "run_on_startup": self.run_on_startup,
            "analysis_depth": self.analysis_depth,
            "include_technical": self.include_technical,
            "include_fundamental": self.include_fundamental,
            "include_sentiment": self.include_sentiment,
        }

    def validate(self) -> List[str]:
        """验证配置，返回错误消息列表"""
        errors = []

        if not self.enabled:
            return errors

        # 验证数据源
        valid_data_sources = ["akshare", "tushare", "yahoo_finance", "binance", "local"]
        for source in self.data_sources:
            if source not in valid_data_sources:
                errors.append(f"无效的数据源: {source}")

        # 验证市场
        valid_markets = ["A", "HK", "US", "EU", "JP", "KR"]
        for market in self.markets:
            if market not in valid_markets:
                errors.append(f"无效的市场: {market}")

        # 验证AI模型
        valid_ai_models = ["gemini-pro", "gpt-4", "claude-3", "qwen-max"]
        if self.ai_model not in valid_ai_models:
            errors.append(f"无效的AI模型: {self.ai_model}")

        # 验证温度
        if not 0 <= self.ai_temperature <= 2:
            errors.append(f"AI温度必须在0-2之间: {self.ai_temperature}")

        return errors

    @classmethod
    def from_json(cls, config_path: Optional[str] = None) -> "DailyStockConfig":
        """
        从JSON文件加载配置

        Args:
            config_path: JSON配置文件路径，如果为None则使用默认路径

        Returns:
            DailyStockConfig实例
        """
        if config_path is None:
            # 尝试从多个位置查找配置文件
            possible_paths = [
                "config/daily_stock_analysis.json",
                "../config/daily_stock_analysis.json",
                "../../config/daily_stock_analysis.json",
            ]

            for path in possible_paths:
                if Path(path).exists():
                    config_path = path
                    break

            if config_path is None:
                # 使用默认配置
                return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # 从字典创建配置对象
            return cls(**config_data)
        except Exception as e:
            print(f"警告: 加载JSON配置文件失败: {e}, 使用默认配置")
            return cls()

    def to_yaml(self) -> str:
        """将配置转换为YAML字符串"""
        if not YAML_AVAILABLE:
            return "yaml模块未安装，无法生成YAML"

        try:
            return yaml.dump(self.to_dict(), allow_unicode=True, sort_keys=False)
        except Exception as e:
            return f"生成YAML失败: {e}"

    def to_json(self) -> str:
        """将配置转换为JSON字符串"""
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            return f"生成JSON失败: {e}"

    def save_to_file(self, config_path: str) -> bool:
        """保存配置到文件"""
        try:
            config_dir = Path(config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)

            if config_path.endswith(".json"):
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            elif config_path.endswith(".yaml") or config_path.endswith(".yml"):
                if not YAML_AVAILABLE:
                    print("警告: yaml模块未安装，无法保存YAML文件")
                    return False
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(self.to_dict(), f, allow_unicode=True, sort_keys=False)
            else:
                # 默认使用JSON
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
