'use client';

import type { AntiQuantPoolItem } from '@/api/client';

interface ConcentrationHeatmapProps {
  stocks: AntiQuantPoolItem[];
  quarters?: string[];
  concentrationByQuarter?: Record<string, Record<string, number>>;
  height?: number;
}

export function ConcentrationHeatmap({
  stocks,
  quarters = [],
  concentrationByQuarter = {},
  height = 200,
}: ConcentrationHeatmapProps) {
  const displayQuarters = quarters.length > 0 ? quarters : ['近期'];
  const displayStocks = stocks.slice(0, 12);

  if (displayStocks.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-card-border bg-card-bg text-sm text-text-dim"
        style={{ height }}
      >
        暂无热力图数据
      </div>
    );
  }

  const getColor = (ratio: number) => {
    const p = Math.min(100, Math.max(0, ratio)) / 100;
    const r = Math.round(255 * (1 - p * 0.6));
    const g = Math.round(59 + (1 - p) * 100);
    const b = Math.round(48 + (1 - p) * 80);
    return `rgb(${r},${g},${b})`;
  };

  return (
    <div
      className="min-h-0 overflow-x-auto overflow-y-auto rounded-xl border border-card-border bg-card-bg"
      style={{ minHeight: height }}
    >
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 border-b border-card-border bg-terminal-bg px-2 py-1.5 text-left font-medium text-text-secondary">
              股票
            </th>
            {displayQuarters.map((q) => (
              <th
                key={q}
                className="min-w-[48px] border-b border-card-border px-1 py-1.5 text-center font-medium text-text-secondary"
              >
                {q}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayStocks.map((row) => {
            const byQ = concentrationByQuarter[row.stock_code] ?? {};
            const values = displayQuarters.map(
              (q) => byQ[q] ?? (q === '近期' ? row.top10_ratio : null)
            );
            return (
              <tr
                key={row.stock_code}
                className="border-b border-[color:var(--color-border-subtle)] hover:bg-white/5"
              >
                <td className="sticky left-0 z-10 bg-card-bg px-2 py-1.5 font-mono text-text-primary">
                  {row.stock_code}
                </td>
                {values.map((v, i) => (
                  <td key={i} className="px-1 py-1 text-center" title={v != null ? `${v}%` : ''}>
                    {v != null ? (
                      <div
                        className="mx-auto h-5 w-8 rounded text-[10px] leading-5"
                        style={{
                          backgroundColor: getColor(v),
                          color: v > 50 ? 'var(--color-text-on-warm-fill)' : 'var(--color-text-secondary)',
                        }}
                      >
                        {v}
                      </div>
                    ) : (
                      <span className="text-outline-variant">—</span>
                    )}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
