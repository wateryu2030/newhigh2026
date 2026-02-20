#!/bin/bash
# 清理策略临时文件

cd "$(dirname "$0")/.."
rm -f strategies/.tmp_*
rm -rf strategies/__pycache__/.tmp_*
echo "✅ 已清理所有临时策略文件及其编译缓存"
