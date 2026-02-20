# 临时文件清理改进

## 问题描述

Web 平台回测时，策略尝试买入 `002701.XSHE`，但用户选择的是 `600745.XSHG`。这是因为旧的临时策略文件没有被清理，导致使用了错误的股票代码。

## 问题原因

1. **临时文件残留**：每次回测都会生成临时文件（如 `.tmp_buy_and_hold_akshare_20260219222236.py`），但清理逻辑可能失败，导致文件残留。
2. **使用旧文件**：如果临时文件清理失败，下次回测可能使用旧的临时文件，导致股票代码错误。
3. **数据库中没有对应股票**：`002701.XSHE` 不在数据库中，导致 "No market data" 警告。

## 修复方案

### 1. 改进清理逻辑

在 `web_platform.py` 中，每次生成临时文件前先清理所有旧的临时文件：

```python
# 清理旧的临时文件（避免使用过期文件）
import glob
old_tmp_files = glob.glob(os.path.join("strategies", ".tmp_*"))
for old_file in old_tmp_files:
    try:
        if os.path.exists(old_file):
            os.remove(old_file)
    except:
        pass
```

### 2. 改进股票代码注入

在 `web_platform_helper.py` 中，使用全局替换确保替换所有股票代码引用：

```python
patterns = [
    (r'context\.s1\s*=\s*["\'][^"\']+["\']', f'context.s1 = "{stock_code}"'),  # 全局替换
    # ...
]
```

### 3. 添加清理脚本

创建 `scripts/cleanup_temp_files.sh`，可以手动清理所有临时文件：

```bash
./scripts/cleanup_temp_files.sh
```

## 验证

修复后：
- ✅ 每次回测前自动清理旧临时文件
- ✅ 股票代码正确注入到临时文件
- ✅ 回测完成后自动清理临时文件
- ✅ 提供手动清理脚本

## 使用建议

1. **定期清理**：如果发现回测结果异常，可以运行清理脚本：
   ```bash
   ./scripts/cleanup_temp_files.sh
   ```

2. **检查数据库**：确保要回测的股票数据已同步到数据库：
   ```bash
   python database/sync_data.py --symbol 600745 --days 365
   ```

3. **使用通用策略**：推荐使用 `universal_ma_strategy.py`，它支持通过环境变量动态设置股票代码，不需要生成临时文件。

## 注意事项

- 临时文件以 `.tmp_` 开头，位于 `strategies/` 目录
- 临时文件会在回测完成后自动清理，但如果回测异常退出，可能需要手动清理
- 如果回测时出现 "No market data" 警告，检查：
  1. 股票代码是否正确
  2. 数据库中是否有该股票的数据
  3. 临时文件是否使用了正确的股票代码
