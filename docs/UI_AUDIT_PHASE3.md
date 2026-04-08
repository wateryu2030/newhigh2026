# UI 审计报告（第三阶段 · `DESIGN.md` 对齐）

**范围**：`frontend/src` 内页面与组件相对设计 token 的收敛情况。  
**时间**：与 `UI_OPTIMIZATION_SPEC.md` 第三阶段同步执行。

## 优先级说明

| 级别 | 含义 |
|------|------|
| P0 | 全局壳层、主路径仪表盘、侧栏/顶栏/移动端导航 |
| P1 | 股东策略大块、系统数据概览、K 线穿透面板 |
| P2 | Alpha Lab / Market / Portfolio / Risk 等独立页图表与文案色 |

## 已完成项（本轮）

- **Token 源**：`frontend/src/app/globals.css` 的 `:root` 与 `tailwind.config.js` 的 `var(--color-*)` 映射。
- **共用图表工具**：`frontend/src/lib/chartTheme.ts`（Recharts 轴/Tooltip、漏斗色、组合饼图、`lightweight-charts` 镜像色、`appIconColors`）。
- **P0**：`Layout`/`MainContent`/`TopBar`/`Sidebar`/`MobileBottomNav`/`MobileDrawer`、`dashboard/*`（第二阶段已做）。
- **P1**：`ShareholderStrategyLayout`、`ShareholderHeader`、`StockDrawer`、`CompareModal`、`ConcentrationHeatmap`、`IndustryRadarChart`、`ShareholderSidebarRight`、`shareholder-strategy/KPICard`、`SystemDataOverview` 弹层等。
- **P2**：`alpha-lab/page`、`market/page`（K 线区）、`portfolio/page`、`risk/page`、`StockPenetrationPanel`（lightweight-charts）、`Nav.tsx`。

## 已知例外（可接受）

- **`layout.tsx` 的 `themeColor`**：仍为 `#FF3B30`（metadata，非 CSS 变量）。
- **`lightweight-charts`**：使用 `lwChartColors` 中的**小写 hex**，与 `:root` 语义一致；库本身不读 `var()`。
- **Alpha Lab / 部分页面**：仍保留 Tailwind 语义类（如 `text-slate-*`、`ring-indigo-*`）作**阶段强调**，未整页改为 `text-text-*`，可在后续统一为设计 token 类名。

## 自检命令

```bash
cd frontend && rm -rf .next && npm run build
```

在仓库内检索残留硬编码（排除 `globals.css`、`chartTheme.ts` 中的定义性 hex）：

```bash
rg "#[0-9A-Fa-f]{3,8}" frontend/src --glob "*.tsx" --glob "*.ts"
```

## 后续建议

- 将 **alpha-lab** 内 `slate-*` / `indigo-*` 逐步替换为 `text-on-surface`、`text-text-secondary`、`ring-primary-fixed` 等。
- 为 **Button / Input / Table** 抽一层薄封装组件，减少页面级重复 class 串。
