export function formatMoney(n: number): string {
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toLocaleString()}`;
}

export function formatPct(n: number, signed = false): string {
  const s = n.toFixed(2);
  if (!signed) return `${s}%`;
  return n >= 0 ? `+${s}%` : `${s}%`;
}
