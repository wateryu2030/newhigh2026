#!/bin/bash
# 安装 X-Twitter/微信公众号采集器定时任务
# 使用方法：./install_x_tweet_schedule.sh

set -e

NEWHIGH_ROOT="/Users/apple/Ahope/newhigh"
SCHEDULE_DIR="$NEWHIGH_ROOT/scripts/schedule"

echo "🦞 安装 x-tweet-fetcher 定时任务..."

# 创建日志目录
mkdir -p "$NEWHIGH_ROOT/logs"

# 复制并配置 plist 文件
echo "📋 配置 launchd 任务..."

# 1. X-Twitter 每 30 分钟采集
PLIST_X_TWEET="$SCHEDULE_DIR/com.redmountain.newhigh.x-tweet.plist"
if [ -f "$PLIST_X_TWEET" ]; then
    # 替换路径占位符 (如果有)
    sed -i '' "s|__NEWHIGH_ROOT__|$NEWHIGH_ROOT|g" "$PLIST_X_TWEET" 2>/dev/null || true
    
    # 加载到 launchd
    launchctl unload "$PLIST_X_TWEET" 2>/dev/null || true
    launchctl load "$PLIST_X_TWEET"
    echo "✅ X-Twitter 定时任务已安装 (每 30 分钟)"
else
    echo "❌ 未找到 plist 文件：$PLIST_X_TWEET"
fi

# 2. 微信公众号每日采集
PLIST_WECHAT="$SCHEDULE_DIR/com.redmountain.newhigh.wechat-daily.plist"
if [ -f "$PLIST_WECHAT" ]; then
    launchctl unload "$PLIST_WECHAT" 2>/dev/null || true
    launchctl load "$PLIST_WECHAT"
    echo "✅ 微信公众号定时任务已安装 (每天 9:00)"
else
    echo "❌ 未找到 plist 文件：$PLIST_WECHAT"
fi

echo ""
echo "📊 查看已安装的任务:"
launchctl list | grep "com.redmountain.newhigh" || echo "暂无任务运行"

echo ""
echo "📝 日志文件位置:"
echo "  - X-Twitter: $NEWHIGH_ROOT/logs/x_tweet_stdout.log"
echo "  - 微信公众号：$NEWHIGH_ROOT/logs/wechat_daily_stdout.log"

echo ""
echo "✅ 安装完成!"
echo ""
echo "💡 手动测试运行:"
echo "  cd $NEWHIGH_ROOT"
echo "  python3 news_collector_x_tweet.py --no-db"
echo ""
echo "🔧 卸载命令:"
echo "  launchctl unload $PLIST_X_TWEET"
echo "  launchctl unload $PLIST_WECHAT"
