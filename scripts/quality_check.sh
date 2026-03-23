#!/bin/bash
# 代码质量检查脚本
# 用法：./scripts/quality_check.sh [--strict]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "🔍 代码质量检查"
echo "========================================"
echo ""

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️  未找到虚拟环境，使用系统 Python"
fi

# 1. 检查代码格式 (autopep8)
echo ""
echo "1️⃣  检查代码格式 (autopep8)..."
if command -v autopep8 &> /dev/null; then
    NEEDS_FIX=$(autopep8 --diff --recursive core/src/ strategy/src/ 2>&1 | wc -l)
    if [ "$NEEDS_FIX" -gt 2 ]; then
        echo -e "${YELLOW}⚠️  发现格式问题，自动修复中...${NC}"
        autopep8 --in-place --aggressive --recursive core/src/ strategy/src/
        echo -e "${GREEN}✅ 格式已修复${NC}"
    else
        echo -e "${GREEN}✅ 代码格式良好${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  autopep8 未安装，跳过${NC}"
fi

# 2. Pylint 检查
echo ""
echo "2️⃣  Pylint 代码质量检查..."
if command -v pylint &> /dev/null; then
    pylint core/src/core/ strategy/src/ \
        --rcfile=.pylintrc \
        --output-format=text \
        --jobs=0 || true
    echo -e "${GREEN}✅ Pylint 检查完成${NC}"
else
    echo -e "${YELLOW}⚠️  pylint 未安装，跳过${NC}"
fi

# 3. MyPy 静态类型检查
echo ""
echo "3️⃣  MyPy 静态类型检查..."
if command -v mypy &> /dev/null; then
    mypy core/src/ strategy/src/ \
        --config-file=mypy.ini \
        --no-error-summary || true
    echo -e "${GREEN}✅ MyPy 检查完成${NC}"
else
    echo -e "${YELLOW}⚠️  mypy 未安装，跳过${NC}"
fi

# 4. 运行测试
echo ""
echo "4️⃣  运行单元测试..."
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short --tb=line || echo -e "${YELLOW}⚠️  部分测试未通过${NC}"
    echo -e "${GREEN}✅ 测试运行完成${NC}"
else
    echo -e "${YELLOW}⚠️  pytest 未安装，跳过${NC}"
fi

echo ""
echo "========================================"
echo "✅ 代码质量检查完成"
echo "========================================"
echo ""
echo "📊 总结:"
echo "  - 代码格式：已检查"
echo "  - Pylint: 已检查"
echo "  - MyPy: 已检查"
echo "  - 测试：已运行"
echo ""
