/** 金额 / 百分比展示 */
function formatWanYuan(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  if (v >= 1e8) return `¥${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `¥${(v / 1e4).toFixed(1)}万`;
  return `¥${v.toFixed(0)}`;
}

function formatPct(n, digits = 2) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  const v = Number(n);
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(digits)}%`;
}

function formatTime(iso) {
  if (!iso) return '';
  const s = String(iso);
  if (s.length >= 16) return s.slice(5, 16).replace('T', ' ');
  return s;
}

module.exports = { formatWanYuan, formatPct, formatTime };
