#!/bin/bash
# 新闻 API 服务器启动脚本

cd /Users/apple/Ahope/newhigh

echo "============================================================"
echo "📰 启动新闻 API 服务器"
echo "============================================================"

# 检查是否已在运行
if lsof -i :8080 | grep -q python; then
    echo "⚠️  端口 8080 已被占用，先停止现有进程..."
    lsof -ti :8080 | xargs kill -9 2>/dev/null
    sleep 1
fi

# 启动服务器
echo "🚀 启动服务器..."
.venv/bin/python news_api_server.py --port 8080 &

# 等待启动
sleep 3

echo ""
echo "============================================================"
echo "✅ 服务器已启动"
echo "============================================================"
echo ""
echo "📺 新闻网页展示：http://localhost:8080/news"
echo "📡 API 接口列表:"
echo "   - 今日新闻：http://localhost:8080/api/news/today"
echo "   - 新闻列表：http://localhost:8080/api/news/list"
echo "   - 个股新闻：http://localhost:8080/api/news/stock?code=002701"
echo "   - 统计摘要：http://localhost:8080/api/news/summary"
echo "   - API 文档：http://localhost:8080/docs"
echo ""
echo "⏹️  停止服务器：lsof -ti :8080 | xargs kill -9"
echo "============================================================"
