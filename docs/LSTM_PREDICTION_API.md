# LSTM 价格预测 API

## 模块说明

**文件**: `ai-models/src/ai_models/lstm_price_predictor.py`

### 功能

- 基于历史 K 线数据预测未来 5 日价格走势
- 使用技术指标（MA、MACD、RSI、波动率）
- 输出预测价格、趋势方向、置信度

### 使用方法

```bash
# 单只股票预测
.venv/bin/python3 ai-models/src/ai_models/lstm_price_predictor.py --code 600889

# 批量预测（默认 50 只）
.venv/bin/python3 ai-models/src/ai_models/lstm_price_predictor.py --batch --limit 100
```

### API 接口（待实现）

```python
# GET /api/ai/prediction?code=600889
{
    "code": "600889",
    "current_price": 16.60,
    "predicted_prices": [16.50, 16.45, 16.24, 16.58, 16.44],
    "predicted_dates": ["2026-03-17", "2026-03-18", ...],
    "confidence": 0.03,
    "trend": "flat",  # up/down/flat
    "created_at": "2026-03-18T06:55:00"
}
```

### 数据库表

```sql
CREATE TABLE price_predictions (
    code VARCHAR,
    current_price DOUBLE,
    predicted_prices VARCHAR,  -- JSON 数组
    predicted_dates VARCHAR,   -- JSON 数组
    confidence DOUBLE,
    trend VARCHAR,
    created_at TIMESTAMP,
    PRIMARY KEY (code, created_at)
)
```

### 注意事项

1. **数据要求**: 至少需要 30 日历史数据
2. **模型简化**: 当前为简化版（趋势外推），实际应使用 PyTorch LSTM
3. **置信度**: 基于趋势强度和波动率计算，仅供参考
4. **更新频率**: 建议每日收盘后更新一次

### 后续优化

- [ ] 使用 PyTorch 实现真正的 LSTM 模型
- [ ] 增加多特征输入（新闻情绪、资金流等）
- [ ] 模型训练与回测验证
- [ ] 增加预测准确率监控
