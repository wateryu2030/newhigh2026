# AI 自进化交易系统（Self-Evolving Trading System）

## 一、架构概览

```
market_data → data_split (train/val/test)
       ↓
strategy_generator (LLM) → 策略代码
       ↓
strategy_runner → 回测 → equity
       ↓
strategy_evaluator → sharpe, max_dd, score
       ↓
evolution_engine → 多轮进化，保留最优
       ↓
strategy_pool → 达标策略入池（自动上线候选）
       ↓
genetic_engine → 优秀策略交叉/变异再进化
```

## 二、模块说明

| 模块 | 文件 | 作用 |
|------|------|------|
| 策略生成 | `evolution/strategy_generator.py` | LLM 根据描述生成 Python 策略代码（需 OPENAI_API_KEY） |
| 策略执行 | `evolution/strategy_runner.py` | 安全执行生成代码，输出 equity 曲线 |
| 策略评估 | `evolution/strategy_evaluator.py` | 夏普、最大回撤、胜率、综合 score |
| 进化引擎 | `evolution/evolution_engine.py` | 循环：生成→回测→评分→保留最优 |
| 策略池 | `evolution/strategy_pool.py` | 仅 score/sharpe/回撤达标策略入池，持久化 |
| 遗传引擎 | `evolution/genetic_engine.py` | 策略代码交叉与变异 |
| 数据划分 | `evolution/data_split.py` | train/val/test 按时间切分，防止未来数据泄露 |

## 三、数据与流程

### 1. 数据准备（必须）

- **自动下载与清洗**：`python scripts/ensure_evolution_data.py`  
  - 默认标的：`000001,600519`，可环境变量 `EVOLUTION_SYMBOLS`、`EVOLUTION_DAYS`
  - 写入 `data/evolution/*.csv`，供进化使用

### 2. 训练/验证/测试划分

- 使用 `split_train_val_test(df, 0.6, 0.2, 0.2)` 按时间顺序划分，**禁止打乱**，避免未来信息泄露。
- 进化时仅在 **训练集** 上生成与评估；验证集用于调参/早停；测试集仅最终评估。

### 3. 运行进化

```bash
# 仅验证流程（不调 LLM）
python run_evolution.py --no-llm --symbol 000001

# 使用 LLM 生成策略（需 OPENAI_API_KEY）
python run_evolution.py --symbol 000001 --rounds 5 --idea "双均线金叉死叉"
```

### 4. 策略池与 API

- 策略池持久化：`data/evolution/strategy_pool.json`
- **GET /api/evolution/pool**：返回池内策略 id、metrics（不含代码）
- **POST /api/evolution/run**：Body `{ "symbol", "rounds", "idea" }` 触发一轮进化

## 四、上线与风控建议

1. **过拟合**：严格 train/val/test，最终表现以 **测试集** 为准；可做 walk-forward 验证。
2. **数据泄露**：生成策略时禁止使用未来数据；回测引擎仅用当前及历史 bar。
3. **交易成本**：评估时可加入滑点、手续费，再算 score。
4. **自动上线条件示例**：夏普 > 1.5、最大回撤 < 20%、验证集稳定盈利再考虑实盘。

## 五、后续可扩展

- **AI 基金经理**：在策略池基础上做资金分配与风险预算。
- **遗传再进化**：用 `GeneticEngine.evolve_pair(code_a, code_b)` 对池内优秀策略做交叉/变异。
- **定时任务**：每日收盘后跑一轮进化、更新策略池、淘汰长期表现差的策略。
