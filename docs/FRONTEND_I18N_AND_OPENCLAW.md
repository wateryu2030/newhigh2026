# 前端双语与 OpenClaw 持续完善

## 一、双语与默认中文

- **默认语言**：中文（`zh`）。localStorage 键 `newhigh_lang` 存 `zh` 或 `en`，刷新后保持用户选择。
- **切换**：导航栏右侧「EN」/「中」按钮，点击在中文与英文间切换。
- **实现位置**：
  - `frontend/src/lib/i18n.ts`：`Lang` 类型、`translations.zh` / `translations.en`、`getStoredLang` / `setStoredLang`。
  - `frontend/src/context/LangContext.tsx`：`LangProvider`、`useLang()` 返回 `{ lang, setLang, t }`。
  - `frontend/src/components/ClientProviders.tsx`：用 `LangProvider` 包裹应用。
  - 各页面与 `Nav`、`EquityCurve` 等通过 `useLang()` 取 `t('key')` 渲染文案。

## 二、文案 key 约定

- **导航**：`nav.dashboard`、`nav.data`、`nav.market`、`nav.news`、`nav.strategies`、`nav.alphaLab`、`nav.evolution`、`nav.portfolio`、`nav.risk`、`nav.trade`、`nav.reports`、`nav.settings`。
- **通用**：`common.loading`、`common.error`、`common.query`、`common.detail`。
- **页面**：`dashboard.*`、`data.*`、`market.*`、`news.*`、`strategies.*`、`portfolio.*`、`risk.title`、`trade.title`、`evolution.title`、`alphaLab.title`、`reports.title`、`settings.title`。
- 新增页面或新文案时，在 `lib/i18n.ts` 的 `zh` 与 `en` 中同时增加相同 key，再在组件内用 `t('key')` 展示。

## 三、数据直接展示

- 所有列表、表格、卡片均直接绑定后端 API 返回数据（如 `/api/dashboard`、`/api/data/status`、`/api/market/ashare/stocks`、`/api/news`），无硬编码假数据占位（除策略池、组合等尚未接实的 stub）。
- 遇接口报错或空数据时，用 `t('common.error')`、`t('common.loading')` 及各页已有空状态文案展示；需新增提示时同样走 i18n key。

## 四、遇到问题时的调整（参照 .md 与 OpenClaw）

- **文案错误或缺失**：在 `lib/i18n.ts` 中修正或补充对应 key 的 zh/en，必要时在组件中改用或新增 `t('key')`。
- **数据不显示或错绑**：对照 `docs/DUCKDB_SCHEMA.md`、`FRONTEND_DATA_BINDING.yaml`、`docs/CODEBASE_DATA_AND_ANALYSIS_REPORT.md` 检查 API 路径与字段；前端请求与状态与 API 约定一致。
- **布局与交互**：参考 `docs/ARCHITECTURE.md`、astock 前端设计，在现有 Tailwind 类与组件结构上迭代；新文案继续走 i18n。
- **持续完善**：按 `OPENCLAW_AUTONOMOUS_DEV.yaml`、`OPENCLAW_AI_DEV_AGENT.yaml`、`docs/OPENCLAW_SYSTEM.md` 执行进化循环；每次改动后跑测试与前端 build，确保无回归。

## 五、快速检查清单

- [ ] 新增或修改的界面文案是否都在 `i18n.ts` 中有 zh/en？
- [ ] 是否用 `t('key')` 而非硬编码中英文字符串？
- [ ] 数据是否来自 API（或明确标注为 stub）？
- [ ] 语言切换后，新打开的页面是否立即变为当前语言？
- [ ] `npm run build` 是否通过？
