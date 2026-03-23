#!/bin/bash
# 自动格式化脚本
# 用法：./scripts/auto_format.sh [file_or_directory]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🎨 自动格式化代码..."
echo ""

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 检查 autopep8
if ! command -v autopep8 &> /dev/null; then
    echo "❌ autopep8 未安装"
    echo "运行：pip install autopep8"
    exit 1
fi

# 确定目标
if [ -n "$1" ]; then
    TARGET="$1"
else
    TARGET="core/src/ strategy/src/ data/src/ gateway/src/"
fi

echo "📁 目标：$TARGET"
echo ""

# 运行 autopep8
echo "正在格式化..."
autopep8 --in-place --aggressive --aggressive --recursive $TARGET

echo ""
echo "✅ 格式化完成!"
echo ""

# 显示统计
CHANGED=$(git diff --name-only 2>/dev/null | wc -l || echo "0")
if [ "$CHANGED" -gt 0 ]; then
    echo "📊 修改了 $CHANGED 个文件"
    echo ""
    echo "💡 提示：运行 'git diff' 查看变更"
fi
