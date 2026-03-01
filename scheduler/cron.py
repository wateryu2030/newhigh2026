# -*- coding: utf-8 -*-
"""
定时任务配置：交易日 15:30 拉取数据等，可与 APScheduler 或系统 crontab 配合。
"""
# 示例 crontab（工作日 15:30 执行每日拉取）:
# 30 15 * * 1-5 cd /path/to/astock && .venv/bin/python scripts/daily_fetch_after_close.py
#
# 若使用 web_platform 内置调度，无需单独配置 cron。
