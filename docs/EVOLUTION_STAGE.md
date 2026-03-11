# 第二阶段：系统进化（OPENCLAW_EVOLUTION）

目标：从 **AI 交易平台** 升级为 **自进化 AI 基金经理**。

## 新增模块

| 模块 | 职责 |
|------|------|
| **alpha-factory** | 策略工厂：LLM/遗传/随机组合生成大量策略候选 |
| **alpha-scoring** | Alpha 评分：sharpe + stability + return - drawdown - volatility，top 10% 入池 |
| **strategy-evolution** | 策略进化：遗传算法（elite + crossover + mutate） |
| **simulation-world** | 市场模拟：gym 风格 reset/step/reward，供 PPO/SAC 训练 |
| **meta-fund-manager** | AI 基金经理：选择策略、分配资金、监控、关闭差策略 |

## 进化循环

```
generate_strategies   → alpha-factory 生成候选
backtest_strategies   → 回测
score_alpha           → alpha-scoring 评分
evolve_population     → strategy-evolution 进化
deploy_top_strategies → meta-fund-manager 选策略并部署
```

## 运行进化管道

```python
from scheduler import connect_pipeline
s = connect_pipeline()
s.run_evolution_pipeline()
```

## 与现有模块关系

- **evolution-engine**：策略池、达尔文淘汰（已有）
- **ai-fund-manager**：策略选择、风控、资金配置（已有）
- 本阶段新增的 **meta-fund-manager** 可调用 evolution-engine 与 ai-fund-manager，或独立使用

## 控制文件

- **OPENCLAW_EVOLUTION.yaml**：phase、new_modules、development_order、loop、rules
