# strategy-evolution

策略进化引擎：遗传算法。选出 Top 策略 → 交叉 → 突变 → 生成新种群。

- select_elite: 按分数取前 elite 个
- crossover: 两条策略参数/指标混合
- mutate: 随机扰动参数与指标
- evolve_population: 生成新一代（elite + 交叉 + 突变），population 1000, elite 100, mutation 20%
