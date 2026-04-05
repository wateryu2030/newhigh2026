# UI 优化：项目级 Spec（配合 Cursor 与 `DESIGN.md`）

把本文件当作与 AI 协作的「合同」：**目标 / 非目标 / 约束 / 验收** 明确后，再改代码。所有视觉改动须符合仓库根目录 **`DESIGN.md`**。

**技术栈（本仓库）**：`frontend/` 为 Next.js App Router（`src/app/`）、Tailwind（`tailwind.config.js`）、现有图表以 Recharts 等为主。**不要**在未获批准时新增重量级 UI 组件库。

---

## 第一阶段：建立或对齐设计宪法（`DESIGN.md`）

### 目标（Scope）

- 使用、维护项目根目录的 **`DESIGN.md`** 作为**唯一** UI 设计规范来源。
- 若 `DESIGN.md` 已存在：以代码审计结果**增量修订**（颜色、字体、间距、布局与现有实现一致或标明待收敛项）。
- 若需重写：仍须覆盖 **颜色系统、字体排印、间距系统、布局与网格**，并包含涨/跌等**语义色**与图表约定。

### 非目标（Non-goals）

- 本阶段**不修改**业务逻辑、数据获取、后端与 Gateway。
- **不修改**组件行为（仅允许新增/修订 `DESIGN.md` 及必要的注释）。

### 约束（Constraints）

- `DESIGN.md` 结构至少包含：`DESIGN.md` 当前各章（颜色、字体、间距、布局、实现载体、语义色说明）。
- 文中 token 与 `frontend/src/app/globals.css`、`frontend/tailwind.config.js`、主要页面（如 `Dashboard`、`TopBar`、`Sidebar`）**可对齐追溯**。

### 验收（Acceptance）

- `DESIGN.md` 完整、可执行；语义色与图表规则**无内部矛盾**或已明确「待统一」项。
- 团队（或你本人）对草案评审通过后再进入第二阶段。

### 风险与执行

- **分步**：先出 `DESIGN.md` 修订草案，评审通过后再动样式代码。
- **可回滚**：仅文档变更时单独 commit；便于 `git revert`。

**可复制提示词（给 Cursor）**：

```markdown
请阅读 `frontend/tailwind.config.js`、`frontend/src/app/globals.css`、`frontend/src/components/MainContent.tsx`、`TopBar.tsx`、`Sidebar.tsx`、`dashboard/Dashboard.tsx`。对照仓库根目录 `DESIGN.md`，列出与文档不一致的硬编码颜色/间距/字体；只更新 `DESIGN.md` 反映真实设计与待收敛项，不要改 TSX/CSS（本阶段）。
```

---

## 第二阶段：按 `DESIGN.md` 优化仪表盘与主路径 UI

### 目标（Scope）

- **严格**遵循 `DESIGN.md`，对主要控制台/仪表盘相关界面做视觉与结构优化（token 化、减少内联样式）。
- **优先页面/入口**（可按需替换）：
  - 首页/控制台：`frontend/src/app/page.tsx`
  - 终端概览：`frontend/src/components/dashboard/Dashboard.tsx`
  - 全局壳层：`frontend/src/components/Layout.tsx`、`TopBar.tsx`、`Sidebar.tsx`、`MainContent.tsx`

### 非目标（Non-goals）

- **不修改**数据获取、交易逻辑、与后端 API 的契约（除非纯展示字段重命名且无副作用）。
- **不引入**新的外部 UI 框架（如 MUI、Chakra）；仅用现有 Next + Tailwind + CSS 变量。

### 约束（Constraints）

- 颜色、圆角、间距、字体**优先**来自 `DESIGN.md` 定义的 token（CSS 变量 + Tailwind 扩展）。
- **移除**可替代的内联 `style={{ color: '#...' }}`，改为 class 或 `var(--color-*)`。
- 重复模式（KPI 卡片、表格行、区块标题）**提取**为小组件时，须沿用同一 token。
- 图表配色与 `DESIGN.md` **语义色**一致；若文档已规定涨/跌规则，按文档统一（含 Recharts `stroke`/`fill`）。

### 验收（Acceptance）

- 目标页面视觉一致：按钮、卡片、表格、标题层级符合 `DESIGN.md`。
- 深色主题（当前默认）无回归；若 `DESIGN.md` 未定义浅色，本阶段**不要求**浅色模式。
- 响应式：桌面（含宽屏）与移动端无明显错位、横向溢出。
- 无显著性能回退（避免无意义重渲染、过大阴影/模糊）。

### 风险与执行

建议顺序（可与 Cursor 分轮执行）：

1. **分析与计划**：列出将改的组件、拟增加的 CSS 变量名、Tailwind 映射表。
2. **实现**：先 `globals.css` / theme，再壳层，再 `Dashboard` 与子组件。
3. **自检**：`cd frontend && npm run dev:brew`（或项目既定命令）做视觉检查；关键路径点一点。

**可复制提示词（给 Cursor）**：

```markdown
严格遵循仓库根目录 `DESIGN.md`。在 `frontend/` 内：1）在 `globals.css` 的 `:root` 补齐文档中的 CSS 变量，并与 `tailwind.config.js` 对齐；2）重构 `Dashboard.tsx`、`TopBar.tsx`、`Sidebar.tsx`、`MainContent.tsx`，去掉可替代的硬编码 hex，改用 token；3）不改动 API 调用与业务状态。每步完成后简短说明变更文件列表。
```

---

## 第三阶段：全站审计与基础组件收敛

### 目标（Scope）

- 对 `frontend/src` 做 **UI 合规审计**：列出不符合 `DESIGN.md` 的页面/组件，按优先级（P0 主路径 / P1 次要 / P2 边缘）分类。
- 系统性收敛基础模式：`Button`、卡片容器、表单 `Input`、表格行样式等（在现有目录如 `components/` 下复用提取，**不必**新建独立 npm 包）。

### 非目标（Non-goals）

- 不新增产品功能或新页面路由。
- 不改变用户核心操作流程（仅视觉与组件边界）。

### 约束（Constraints）

- 基础样式修改应**全局复用**，避免同一模式多处 copy。
- 重要组件旁可保留简短注释或 Story（若项目已有 Storybook；否则用 `DESIGN.md` + 一处示例即可）。

### 验收（Acceptance）

- 产出**审计清单**（Markdown 即可，可放在 `docs/` 或本文件附录）。
- 主路径与高优先级组件已替换为 token；**约定比例**（如绝大部分主界面无裸 hex）由你根据审计勾选。

### 风险与执行

- 先审计报告，再分批 PR/分支；每批可回滚。

**可复制提示词（给 Cursor）**：

```markdown
根据 `DESIGN.md` 扫描 `frontend/src/**/*.tsx`，列出仍使用硬编码 `#RRGGBB` 或 `rgba(...)` 样式的文件（排除合法第三方、图表数据项若需保留请标注）。输出优先级表。不要一次性改完；先仅修复 `components/dashboard/` 与 `StatCard.tsx`、`KPICard.tsx` 中的重复色值。
```

---

## 优化提示（给产品/设计沟通用语）

- 风格关键词：**data-dense**、**control tower**、**technical**、专业金融终端感；避免过度娱乐化、花哨动效。
- 具体调色示例（可与 `DESIGN.md` 迭代对齐）：**monochromatic dark base + electric red/coral accent**（当前实现接近红珊瑚强调 + 深灰底）。
- 外部结构参考：可参考社区中公开的设计系统文档结构（如 Vercel、Linear 类）**只借鉴章节组织**，token 仍以本仓库 `DESIGN.md` 为准。

---

## 文档关系

| 文件 | 作用 |
|------|------|
| `DESIGN.md` | 设计宪法 / token 与布局真理来源 |
| `UI_OPTIMIZATION_SPEC.md` | 分阶段任务与可复制 Prompt |
| `frontend/tailwind.config.js` + `src/app/globals.css` | 实现载体，须与 `DESIGN.md` 同步演进 |
