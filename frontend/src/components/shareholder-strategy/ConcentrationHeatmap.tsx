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
        className="flex items-center justify-center rounded-xl text-sm"
        style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', height, color: '#64748B' }}
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
      className="overflow-x-auto overflow-y-auto rounded-xl"
      style={{ backgroundColor: '#14171C', border: '1px solid #2A2E36', minHeight: height }}
    >
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th
              className="sticky left-0 z-10 px-2 py-1.5 text-left font-medium"
              style={{ backgroundColor: '#0A0C10', color: '#94A3B8', borderBottom: '1px solid #2A2E36' }}
            >
              股票
            </th>
            {displayQuarters.map((q) => (
              <th
                key={q}
                className="px-1 py-1.5 text-center font-medium"
                style={{ color: '#94A3B8', borderBottom: '1px solid #2A2E36', minWidth: 48 }}
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
                className="hover:bg-white/5"
                style={{ borderBottom: '1px solid #1E2229' }}
              >
                <td
                  className="sticky left-0 z-10 px-2 py-1.5 font-mono"
                  style={{ backgroundColor: '#14171C', color: '#F1F5F9' }}
                >
                  {row.stock_code}
                </td>
                {values.map((v, i) => (
                  <td key={i} className="px-1 py-1 text-center" title={v != null ? `${v}%` : ''}>
                    {v != null ? (
                      <div
                        className="mx-auto h-5 w-8 rounded"
                        style={{
                          backgroundColor: getColor(v),
                          color: v > 50 ? '#FFF' : '#94A3B8',
                          lineHeight: '20px',
                          fontSize: 10,
                        }}
                      >
                        {v}
                      </div>
                    ) : (
                      <span style={{ color: '#475569' }}>—</span>
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
