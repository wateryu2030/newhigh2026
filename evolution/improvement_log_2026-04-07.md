# 改进记录 · 2026-04-07

## Playwright E2E 冒烟稳定性

**背景**：受保护路由依赖 `AuthContext`（`localStorage.newhigh_jwt_token`）；未登录时侧栏不展示「策略」等链接，`/portfolio` 显示访客拦截页，导致 `smoke.spec.ts` 失败。

**改动**：

- `frontend/e2e/smoke.spec.ts`：`beforeEach` 使用 `page.addInitScript` 注入占位 token，通过 `AuthGate`；策略导航增加可见性等待与 `networkidle` 容错；组合页用 `getByRole('heading', { level: 1 })` 断言。
- `frontend/src/app/portfolio/page.tsx`：增加页面级 `<h1>`（`portfolio.title`），与无障碍及测试一致。
- 仓库根 `package.json`：增加 `npm run test:e2e` → `frontend`。

**验证**（在 `frontend/` 或仓库根）：

```bash
npm run test:e2e
```

**pytest 路径（同日补充）**：根目录 `pytest.ini` 的 `pythonpath` 已增加 `backtest-engine/src`、`strategy/src`，使 `from backtest_engine import …` 在未 `pip install -e backtest-engine` 时亦可解析。

```bash
.venv/bin/python -m pytest tests/test_data_pipeline.py tests/test_strategy_engine.py tests/test_execution_engine.py -q
```
