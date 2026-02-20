# 快速开始指南

## ✅ 已完成的自检和配置

运行 `python auto_test.py` 或 `python setup_complete.py` 已完成：
- ✅ 依赖检查与安装
- ✅ Bundle 文件结构创建
- ✅ AKShare 数据获取测试
- ✅ RQAlpha 导入测试
- ✅ 策略语法检查
- ✅ Web 平台检查

## 🚀 快速测试

### 1. 测试 AKShare 数据获取（无需 bundle）

```bash
source venv/bin/activate
python test_wentai.py
```

### 2. 运行策略回测

**注意**: RQAlpha 默认需要真实的历史数据包（bundle）。当前 bundle 为空结构，仅用于测试。

**选项 A: 使用 RQAlpha 官方数据源**
```bash
# 下载真实数据包（需要配置数据源）
rqalpha download-bundle

# 然后运行回测
python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30
```

**选项 B: 使用 AKShare 数据适配器（推荐）**
```bash
# 使用 AKShare 数据源运行（无需 bundle）
python run_backtest_akshare.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30
```

### 3. 启动 Web 平台

```bash
source venv/bin/activate
python web_platform.py
```

访问: http://127.0.0.1:5050

## 📋 当前状态

- ✅ **依赖**: 已安装（akshare, rqalpha, flask）
- ✅ **Bundle 结构**: 已创建（空文件，用于测试）
- ✅ **AKShare 数据**: 可正常获取（闻泰科技测试通过）
- ✅ **RQAlpha 导入**: run_file 可正常导入
- ✅ **Web 平台**: 运行正常
- ⚠️  **回测数据**: Bundle 为空，需要真实数据或使用 AKShare 适配器

## 🔧 问题排查

### 如果遇到 "cannot import name 'run_file'"
- 已修复：使用子进程 + 路径隔离
- 确保运行 `python run_backtest.py`（不是直接导入）

### 如果遇到 "bundle path not exist"
- 运行: `python setup_complete.py` 创建 bundle 结构

### 如果遇到 "There is no data"
- Bundle 为空，需要：
  1. 下载真实数据: `rqalpha download-bundle`，或
  2. 使用 AKShare 适配器: `python run_backtest_akshare.py`

## 📝 下一步

1. **获取真实数据**: 配置 RQAlpha 数据源并下载 bundle
2. **完善 AKShare 适配器**: 实现完整的 AbstractDataSource 接口
3. **运行策略**: 在 Web 平台或命令行运行回测
4. **查看结果**: 检查 output/ 目录下的回测结果
