"""
OpenClaw 标准化进化接口

提供统一的进化接口，支持 OpenClaw 自动化代码改进。

架构:
    lib/           ← 基础设施
    core/          ← 核心服务
    openclaw/      ← OpenClaw 集成 (本模块)
    data/          ← 数据层
    ai/            ← AI 层
    scanner/       ← 扫描器
    strategy/      ← 策略引擎
"""

from .evolution_api import EvolutionAPI
from .code_review import CodeReviewer
from .refactoring_suggester import RefactoringSuggester

__version__ = "1.0.0"
__all__ = [
    "EvolutionAPI",
    "CodeReviewer",
    "RefactoringSuggester",
]
