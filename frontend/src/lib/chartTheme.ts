/** Recharts / 可视化与 DESIGN.md 对齐的共用样式（避免散落 hex） */

export const rechartsTooltipContent = {
  backgroundColor: 'var(--color-surface-high)',
  border: '1px solid var(--color-outline-variant)',
  borderRadius: 8,
} as const;

export const rechartsTooltipLabel = { color: 'var(--color-text-secondary)' } as const;

export const rechartsTickSecondary = { fill: 'var(--color-text-secondary)', fontSize: 10 } as const;
export const rechartsTickSecondary11 = { fill: 'var(--color-text-secondary)', fontSize: 11 } as const;
export const rechartsTickDim = { fill: 'var(--color-text-dim)', fontSize: 10 } as const;

export const rechartsCursorStroke = { strokeDasharray: '3 3', stroke: 'var(--color-outline-variant)' };

/** 漏斗 / 多序列（Alpha Lab 等） */
export const chartFunnelColors = [
  'var(--color-chart-indigo)',
  'var(--color-chart-purple)',
  'var(--color-chart-emerald)',
  'var(--color-chart-emerald-dark)',
] as const;

/** 组合页饼图等（SVG 支持 var） */
export const portfolioPieFills = [
  'var(--color-chart-indigo)',
  'var(--color-chart-emerald)',
  'var(--color-chart-amber)',
] as const;

/**
 * lightweight-charts 仅接受具体颜色字符串，与 globals.css :root 保持同步。
 */
export const lwChartColors = {
  layoutBg: '#14171c',
  text: '#94a3b8',
  grid: '#2a2e36',
  candleUp: '#22c55e',
  candleDown: '#ff3b30',
  volume: '#6366f1',
} as const;

/** next/og ImageResponse 等不支持 CSS 变量时与 --color-icon-canvas / --color-primary 同步 */
export const appIconColors = {
  canvas: '#0f172a',
  foreground: '#ff3b30',
} as const;
