# 给 OpenClaw 的续跑提示（修订版：防 Web 复读）

主仓：`/Users/apple/Ahope/newhigh`。

---

## 重要（请先遵守，避免「让我查看 ci.yml…」无限循环）

1. **不要用「连续 read 仓库文件」完成本任务**（尤其在 **Web + DeepSeek** 下会复读）。若必须引用 CI，请在**本机终端**执行后**把输出粘贴到会话**：
   ```bash
   cd /Users/apple/Ahope/newhigh && sed -n '1,200p' .github/workflows/ci.yml 2>/dev/null || sed -n '1,200p' .github/workflows/test.yml
   ```
2. **良性闭环请走终端**（OpenClaw 规划 + Cursor CLI 落地，不由 Web 长对话改代码）：
   ```bash
   cd /Users/apple/Ahope/newhigh && bash scripts/openclaw_benign_loop.sh
   ```
   或 `make openclaw-cursor-iterate`。仅生成规划：`OPENCLAW_CURSOR_PLAN_ONLY=1 bash scripts/openclaw_benign_loop.sh`
3. **Web 会话模型**：优先选 **通义 Qwen**，避免 **DeepSeek** 与读文件工具链叠加。

---

## 已由 Cursor 完成的验证（摘要）

- E2E：`frontend/e2e/smoke.spec.ts` 占位 JWT；`portfolio` 有 `h1`；根目录 `npm run test:e2e`。
- pytest：根 `pytest.ini` 已含 `backtest-engine/src`、`strategy/src`；`make test-python-smoke` 9 项通过。

---

## 请你继续完善（任选 1 条；写路径、命令、勿空洞）

1. **CI 对齐**：对照**粘贴的** workflow 片段与本地 `pytest.ini` / `make test-python-smoke`，建议需改哪几行（不要假设你已 read 成功）。
2. **E2E**：`auth.setup.ts` + `storageState` 或文档化占位 token 边界。
3. **Makefile**：增加 `make test-smoke-all` = `test-python-smoke` + 根 `npm run test:e2e`（若合理）。
4. **文档**：在 `docs/OPENCLAW_PLUS_CURSOR_LOOP.md` §四 加一句链到本文件（若尚未链）。

**禁止**：仅 HEARTBEAT_OK；向仓库写入真实 JWT/密钥。

**产出**：Markdown——所选条目、涉及文件、补丁或命令、验证步骤、需人类/Cursor 接手项。
