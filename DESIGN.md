# newhigh 量化交易平台 · UI 设计规范（Design Constitution）

本文档为 **`frontend/` 内所有 UI 的唯一视觉规范来源**。新增页面、重构组件、图表配色均须对齐此处；与实现不一致时，**以本文档为准逐步收敛代码**（通过 CSS 变量 / Tailwind theme，避免散落硬编码）。

**美学取向**：数据密度高、专业控制台（control tower）、技术感强；避免花哨、低龄化装饰。默认 **深色终端** 主题；`tailwind.config.js` 已启用 `darkMode: 'class'`，浅色主题可在本文档增补 token 后再实现。

---

## 1. 颜色系统（Color System）

### 1.1 品牌与强调（Brand / Accent）

| Token（建议 CSS 变量名） | Hex | 用途 |
|---------------------------|-----|------|
| `--color-primary` | `#FF3B30` | 主强调、CTA、选中态、主题色（与 `themeColor` 一致） |
| `--color-primary-soft` | `#FF6B6B` | 次要强调，Tailwind `primary` |
| `--color-tertiary` | `#FF7439` | 辅助强调、部分负向/警示数值 |

### 1.2 表面与背景（Surface / Background）

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-bg-terminal` | `#0A0C10` | 顶栏、部分全屏底（`terminal-bg`、`TopBar`） |
| `--color-bg-app` | `#0B0E14` | 主内容区、全局 surface（`MainContent`、`body`） |
| `--color-surface-low` | `#10131A` | 低层表面（`surface-container-low`） |
| `--color-surface-mid` | `#14171C` | 卡片/侧栏（`card-bg`） |
| `--color-surface-high` | `#1C2028` | 抬升表面（`surface-container-high`） |
| `--color-surface-highest` | `#22262F` | 更高层级 |

**已知漂移（待收敛）**：`#0A0C10` 与 `#0B0E14` 混用于顶栏与主区；语义为「顶栏条」与「应用画布」，保留两档，**禁止再引入第三套相近灰黑**。

### 1.3 边框与分割线

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-border` | `#2A2E36` | 卡片、侧栏（`card-border`） |
| `--color-outline` | `#73757D` | 通用轮廓 |
| `--color-outline-variant` | `#45484F` | 弱轮廓 |

### 1.4 文本

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-text-primary` | `#ECEDF6` | 主文案（`on-surface`） |
| `--color-text-primary-alt` | `#F1F5F9` | 侧栏激活等（与上式收敛选一） |
| `--color-text-secondary` | `#94A3B8` | 次要文案 |
| `--color-text-muted` | `#A9ABB3` | 辅助说明 |
| `--color-text-dim` | `#64748B` | 更弱层级 |

### 1.5 语义与市场（Semantic / Market）

| Token | Hex | 用途 |
|-------|-----|------|
| `--color-success` | `#22C55E` | 成功、部分涨跌额正向（`accent-green`） |
| `--color-danger` | `#FF3B30` | 错误、删除、负向涨跌、主强调 |
| `--color-warning` | `#FF7439` | 警告、次要负向 |

**当前代码约定（优化时需统一）**：

- `StatCard` / `dashboard/KPICard` 的 `positive`：正向 `#FF3B30`，负向 `#FF7439`（偏 A 股语境）。
- `KPICard` 的 `change`：`change >= 0` 为 `#22C55E`，`change < 0` 为 `#FF3B30`（与国际绿涨红跌一致）。
- 股东策略等页面存在与仪表盘不一致的涨跌色，**须在迭代中选定单一规则**并替换图表 `stroke`/`fill`。

图表主序列建议与 `--color-primary` 对齐（现多为 `#FF3B30`）。

### 1.6 叠加与特效

- `--shadow-glass`: `0px 24px 48px rgba(0,0,0,0.4)`
- `--shadow-card`: `0 2px 8px rgba(0,0,0,0.2)`（卡片/侧栏）
- `--glow-primary`: `0 0 20px rgba(255,59,48,0.3)`
- 毛玻璃：`--color-glass-bg`（`rgba(28,32,40,0.6)`）+ `blur(20px)`（`.glass-card`）
- `--color-primary-alpha-15`: `rgba(255,59,48,0.15)`（顶栏热点标签底）
- `--color-hot-ticker-bar`: `rgba(16,19,26,0.95)`（独立热点条背景）
- `--color-text-code`: `#CBD5E1`（`<pre>` / 代码块正文）
- `--color-surface-container`: `#161A21`（表单控件底等，与 Tailwind `surface-container` 对齐）
- `--color-chart-amber`: `#f59e0b`（风险曲线等辅助序列）
- `--color-text-on-warm-fill`: `#ffffff`（热力图等高饱和格内文字）
- **`chartTheme.ts` / `lwChartColors`**：`lightweight-charts` 使用与上表一致的小写 hex 镜像，因第三方库不解析 `var()`。

---

## 2. 字体排印（Typography）

| 角色 | 字体 | 来源 |
|------|------|------|
| 正文 UI | Inter | `next/font`，`--font-inter`，Tailwind `font-sans` |
| 标题/品牌 | Manrope | `--font-manrope`，`font-headline` |
| 数据标签/KPI | Space Grotesk | 显式指定，回退 `ui-monospace` |
| 图标 | Material Symbols Outlined | `globals.css` |

| 层级 | 建议 |
|------|------|
| 页面主标题 | `text-2xl`–`text-3xl`，Manrope / `font-headline` |
| 区块标题 | `text-sm font-medium`，次要色 |
| KPI 数值 | `text-2xl md:text-3xl font-bold`，Space Grotesk |
| 正文 | `text-sm`，Inter |

---

## 3. 间距系统（Spacing Scale）

基准：**4px**（Tailwind `1` = 0.25rem）。

| Token | rem | px |
|-------|-----|-----|
| xs | 0.25 | 4 |
| sm | 0.5 | 8 |
| md | 1 | 16 |
| lg | 1.5 | 24 |
| xl | 2 | 32 |

常用：统计网格 `gap-4`；页面 `px-4`、`md:px-6`；卡片 `p-4`/`p-5`；圆角目标统一为 `rounded-2xl` 与 `theme borderRadius.card`。

---

## 4. 布局与网格（Layout & Grid）

| 区域 | 规格 |
|------|------|
| TopBar | 固定，`h-16`，背景 `#0A0C10`，底边 `#2A2E36` |
| Sidebar | 宽 260px，`fixed`，`left-3`，顶距 `calc(4rem + 0.75rem)`，`rounded-2xl` |
| MainContent | `pt-20`，桌面 `pl-[calc(0.75rem+260px+1.5rem)]`，背景 `#0B0E14` |
| 股东策略页 | 无全局侧栏时 `md:pl-6` |
| 移动端 | 底部导航 + 抽屉，`pb-24` |

可选：阅读型内容 `max-w-6xl`/`7xl`；仪表盘维持全宽以提高数据密度。

---

## 5. 组件与模式（简要）

- 卡片：表面 `#14171C`，边框 `#2A2E36`，阴影 `0 2px 8px rgba(0,0,0,0.2)`。
- 导航：激活态背景 `surface-container-high`，文字主色/主色固定。
- 滚动条：宽 4px，见 `globals.css` 与 `.sidebar-scroll`。

---

## 6. 实现载体（Implementation）

1. 在 `globals.css` 的 `:root` 补齐 CSS 变量，与现有 `--kt-*` 合并并逐步去重 hex。
2. `tailwind.config.js` 的 `theme.extend.colors` 与变量对齐。
3. 禁止新增大段内联 `style={{ color: '#...' }}`；新代码用 class + token。

---

## 7. 修订与评审

变更本文档时应在 PR 中说明，并同步 `UI_OPTIMIZATION_SPEC.md` 相关阶段任务。
