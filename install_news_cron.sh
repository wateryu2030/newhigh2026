#!/bin/bash
# 新闻采集器 - 定时任务安装脚本
# 使用方法：./install_news_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
COLLECTOR_SCRIPT="$SCRIPT_DIR/api_news_collector.py"
LOG_DIR="$SCRIPT_DIR/logs/news_api"

echo "============================================================"
echo "📰 新闻采集器 - 定时任务安装"
echo "============================================================"

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ 错误：虚拟环境不存在 ($VENV_PYTHON)"
    echo "请先运行：python3 -m venv .venv"
    exit 1
fi

# 检查采集器脚本
if [ ! -f "$COLLECTOR_SCRIPT" ]; then
    echo "❌ 错误：采集器脚本不存在 ($COLLECTOR_SCRIPT)"
    exit 1
fi

# 创建日志目录
mkdir -p "$LOG_DIR"
echo "✅ 日志目录：$LOG_DIR"

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "检测到 macOS 系统"
    echo ""
    echo "请选择安装方式:"
    echo "  1) Cron (简单推荐)"
    echo "  2) LaunchAgent (macOS 原生)"
    echo "  3) 仅测试，不安装"
    echo ""
    read -p "请输入选项 (1/2/3): " choice
    
    case $choice in
        1)
            echo ""
            echo "📝 添加到 crontab..."
            echo ""
            
            # 备份当前 crontab
            crontab -l > /tmp/crontab_backup.$$ 2>/dev/null || true
            echo "✅ 已备份当前 crontab"
            
            # 添加新闻采集任务
            (crontab -l 2>/dev/null | grep -v "news_collector" || true; \
             echo "# 新闻采集 - 早间 (6:00)"; \
             echo "0 6 * * * cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT >> $LOG_DIR/cron_morning.log 2>&1"; \
             echo "# 新闻采集 - 午间 (12:00)"; \
             echo "0 12 * * * cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT >> $LOG_DIR/cron_noon.log 2>&1"; \
             echo "# 新闻采集 - 晚间 (18:00)"; \
             echo "0 18 * * * cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT >> $LOG_DIR/cron_evening.log 2>&1") | crontab -
            
            echo "✅ 已安装 Cron 任务"
            echo ""
            echo "📋 当前 crontab:"
            crontab -l | grep news_collector || echo "(无)"
            ;;
            
        2)
            echo ""
            echo "📝 创建 LaunchAgent..."
            
            PLIST_FILE="$HOME/Library/LaunchAgents/com.newhigh.news-collector.plist"
            
            cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.newhigh.news-collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/launchd.err</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
</dict>
</plist>
EOF
            
            # 加载服务
            launchctl unload "$PLIST_FILE" 2>/dev/null || true
            launchctl load "$PLIST_FILE"
            
            echo "✅ 已安装 LaunchAgent: $PLIST_FILE"
            echo ""
            echo "📋 服务状态:"
            launchctl list | grep newhigh || echo "(未运行)"
            ;;
            
        3)
            echo ""
            echo "🧪 执行测试运行..."
            echo ""
            source .venv/bin/activate
            python3 "$COLLECTOR_SCRIPT"
            ;;
            
        *)
            echo "❌ 无效选项"
            exit 1
            ;;
    esac
    
else
    # Linux 系统
    echo ""
    echo "📝 添加到 crontab (Linux)..."
    
    (crontab -l 2>/dev/null | grep -v "news_collector" || true; \
     echo "# 新闻采集 - 早间 (6:00)"; \
     echo "0 6 * * * cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT >> $LOG_DIR/cron_morning.log 2>&1"; \
     echo "# 新闻采集 - 午间 (12:00)"; \
     echo "0 12 * * * cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT >> $LOG_DIR/cron_noon.log 2>&1"; \
     echo "# 新闻采集 - 晚间 (18:00)"; \
     echo "0 18 * * * cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT >> $LOG_DIR/cron_evening.log 2>&1") | crontab -
    
    echo "✅ 已安装 Cron 任务"
fi

echo ""
echo "============================================================"
echo "✅ 安装完成!"
echo "============================================================"
echo ""
echo "📋 下一步:"
echo "  1. 配置聚合数据 API Key (可选但推荐)"
echo "     编辑：$SCRIPT_DIR/.env"
echo "     添加：JUHE_API_KEY=your_key_here"
echo ""
echo "  2. 查看日志:"
echo "     tail -f $LOG_DIR/cron_*.log"
echo ""
echo "  3. 手动测试:"
echo "     cd $SCRIPT_DIR && source .venv/bin/activate && python3 $COLLECTOR_SCRIPT"
echo ""
echo "============================================================"
