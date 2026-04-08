/** 行情类表格共用格式化（数据页下钻、AI 交易等） */

export function fmtPrice(v: number | null | undefined): string {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 3 });
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

export function fmtScore01(v: number | null | undefined): string {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `${(Number(v) * 100).toFixed(1)}%`;
}

export function fmtAmountWan(v: number | null | undefined): string {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (Math.abs(n) >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (Math.abs(n) >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
}

export function chgClass(chg: number | null | undefined): string {
  if (chg == null || Number.isNaN(Number(chg))) return 'text-text-secondary';
  if (Number(chg) > 0) return 'text-accent-green';
  if (Number(chg) < 0) return 'text-accent-red';
  return 'text-text-secondary';
}
