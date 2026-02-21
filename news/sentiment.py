# -*- coding: utf-8 -*-
"""
舆情分析：简单情感打分、汇总。
支持扩展：接入 NLP 模型、SnowNLP、百度 API 等。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# 简单正面/负面词库（可扩展）
_POSITIVE_WORDS = {
    "涨", "利好", "突破", "创新高", "大涨", "飙升", "暴涨", "强势", "看好",
    "增长", "盈利", "超预期", "上调", "买入", "增持", "推荐", "牛市",
}
_NEGATIVE_WORDS = {
    "跌", "利空", "暴跌", "大跌", "破位", "回调", "下调", "减持", "卖出",
    "亏损", "暴雷", "爆仓", "风险", "熊市", "崩盘", "停牌", "退市",
}


class SentimentAnalyzer:
    """
    舆情分析器。
    默认使用关键词打分；可扩展为 SnowNLP、百度 NLP、自训练模型等。
    """

    def __init__(
        self,
        positive_words: Optional[set] = None,
        negative_words: Optional[set] = None,
    ):
        self.positive = positive_words or _POSITIVE_WORDS
        self.negative = negative_words or _NEGATIVE_WORDS

    def score(self, text: str) -> float:
        """
        单条文本情感得分：[-1, 1]，正为正面，负为负面。
        基于关键词计数。
        """
        if not text or not isinstance(text, str):
            return 0.0
        t = text.strip()
        if len(t) < 2:
            return 0.0
        pos = sum(1 for w in self.positive if w in t)
        neg = sum(1 for w in self.negative if w in t)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def analyze_one(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """单条新闻分析。"""
        title = item.get("title", "") or ""
        content = item.get("content", "") or ""
        text = f"{title} {content}"
        score = self.score(text)
        label = "positive" if score > 0.2 else ("negative" if score < -0.2 else "neutral")
        return {
            **item,
            "sentiment_score": round(score, 4),
            "sentiment_label": label,
        }

    def analyze_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量分析。"""
        return [self.analyze_one(x) for x in items]


def analyze_sentiment(
    items: List[Dict[str, Any]],
    analyzer: Optional[SentimentAnalyzer] = None,
) -> List[Dict[str, Any]]:
    """对新闻列表做舆情分析。"""
    a = analyzer or SentimentAnalyzer()
    return a.analyze_batch(items)


def aggregate_sentiment(
    analyzed: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    汇总舆情：平均分、正/负/中性占比。
    """
    if not analyzed:
        return {"avg_score": 0.0, "positive_ratio": 0.0, "negative_ratio": 0.0, "neutral_ratio": 0.0}
    scores = [x.get("sentiment_score", 0) for x in analyzed if "sentiment_score" in x]
    labels = [x.get("sentiment_label", "neutral") for x in analyzed if "sentiment_label" in x]
    n = len(scores)
    if n == 0:
        return {"avg_score": 0.0, "positive_ratio": 0.0, "negative_ratio": 0.0, "neutral_ratio": 0.0}
    avg = sum(scores) / n
    pos = sum(1 for l in labels if l == "positive") / n
    neg = sum(1 for l in labels if l == "negative") / n
    neu = 1.0 - pos - neg
    return {
        "avg_score": round(avg, 4),
        "positive_ratio": round(pos, 4),
        "negative_ratio": round(neg, 4),
        "neutral_ratio": round(neu, 4),
        "count": n,
    }
