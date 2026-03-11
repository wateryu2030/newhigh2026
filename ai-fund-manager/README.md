# ai-fund-manager

AI 基金经理控制系统：策略选择、风险控制、资金配置。

- **Strategy Selector** — 挑选上线/暂停/淘汰策略
- **Risk Controller** — 回撤/敞口/波动规则，输出 suspend/reduce
- **Capital Allocator** — 按 equal / alpha_weighted 分配资金

依赖 evolution-engine（策略池与 Alpha 分）。
