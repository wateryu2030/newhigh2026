# 给 OpenClaw 的续跑提示词（粘贴到 Web 或 `openclaw agent --local`）

主仓：`/Users/apple/Ahope/newhigh`。请先 **read** 本文件与 `tasks/current_task.md`（各一遍即可）。

## 已在本轮由 Cursor 完成

- **E2E**：`frontend/e2e/smoke.spec.ts` 用 `localStorage` 占位 JWT 通过 `AuthGate`；`portfolio` 页补充 `h1`；仓库根 `npm run test:e2e` 与 `frontend` 下等价。
- **pytest**：`pytest.ini` 的 `pythonpath` 已包含 `backtest-engine/src`、`strategy/src`，根目录可跑通  
  `tests/test_data_pipeline.py`、`tests/test_strategy_engine.py`、`tests/test_execution_engine.py`（建议 `.venv/bin/python -m pytest …`）。

## 请你继续完善（任选 1 条，写清路径与验证命令）

1. **CI**：确认 `.github/workflows/ci.yml`（或 `test.yml`）中 Python 测试是否使用仓库根 `pytest.ini`；若 job 只装部分包，补全 `pythonpath` 或与本地一致，避免 CI 仅因路径漂移失败。
2. **E2E 可选增强**：在 `frontend/e2e/` 增加独立 `auth.setup.ts` + `storageState`，减少 `addInitScript` 重复；或文档化「占位 token 不调用真实 API」的边界。
3. **Makefile**：根目录已有 `make test-python-smoke`（9 个 pytest）。可再增加「pytest + `npm run test:e2e`」组合目标（若命名与 CI 一致更好）。
4. **文档**：在 `docs/OPENCLAW_PLUS_CURSOR_LOOP.md` 或 `tasks/openclaw_handoff.md` 用一句话链到 `tasks/openclaw_followup_prompt.md`。

**禁止**：仅回复 HEARTBEAT_OK；不要把真实 JWT/密钥写入仓库。

**产出格式**：Markdown 分节——所选条目、涉及文件、建议补丁或命令、验证步骤、需 Cursor 接手项（若有）。
