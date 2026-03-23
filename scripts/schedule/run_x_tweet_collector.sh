#!/bin/bash
# X-Twitter 和微信公众号新闻采集器 - 定时任务包装脚本
# 用于 launchd 或 cron 调用

set -e

# 切换到项目目录
cd /Users/apple/Ahope/newhigh

# 激活虚拟环境 (如果存在)
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 运行采集器
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 X-Twitter/微信公众号采集"
python3 news_collector_x_tweet.py --no-db

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 采集完成"
