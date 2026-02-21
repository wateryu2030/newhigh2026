#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻采集 + 舆情分析示例。
用法: python scripts/fetch_news_sentiment.py [股票代码]
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "600519"
    print(f"采集新闻并分析舆情: {symbol}\n")
    from news import fetch_all_news, analyze_sentiment, aggregate_sentiment

    raw = fetch_all_news(symbol=symbol, sources=["eastmoney", "caixin"], limit_per_source=20)

    all_items = []
    for site, items in raw.items():
        filtered = [x for x in items if not x.get("error")]
        print(f"[{site}] 采集 {len(filtered)} 条")
        all_items.extend(filtered)

    if not all_items:
        print("无有效新闻")
        return 0

    analyzed = analyze_sentiment(all_items)
    agg = aggregate_sentiment(analyzed)
    print("\n舆情汇总:")
    print(f"  平均分: {agg['avg_score']:.4f}")
    print(f"  正面: {agg['positive_ratio']:.1%}  负面: {agg['negative_ratio']:.1%}  中性: {agg['neutral_ratio']:.1%}")
    print(f"\n前 5 条:")
    for i, x in enumerate(analyzed[:5]):
        title = (x.get("title") or "")[:50]
        score = x.get("sentiment_score", 0)
        label = x.get("sentiment_label", "?")
        print(f"  {i+1}. [{label}] {score:.3f} {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
