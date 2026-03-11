# alpha-scoring

Alpha 评分引擎。公式：alpha_score = sharpe + stability + return - drawdown - volatility。

- 输入：backtest results（metrics dict）
- 输出：alpha_score，策略排名，top 10% 进入策略池。
