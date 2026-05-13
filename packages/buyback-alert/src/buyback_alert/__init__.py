"""
buyback_alert - 回购/增持/溢价收购数据采集、连跌检测、交叉预警。

Collector:  从 akshare 采集回购、大宗交易等事件写入 buyback_events 表
Detector:   基于 daily_bars 检测 N 日连跌
Alerter:    连跌股票与 buyback_events 交叉匹配，生成预警写入 alerts 表
CLI:        python -m buyback_alert [--collect] [--detect] [--alert] [--run-all]
"""

from __future__ import annotations
