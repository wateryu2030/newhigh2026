'use client';

import type { Holding, ChangeRecord } from '@/data/mockShareholder';

const ACTION_COLORS: Record<string, string> = {
  新进: 'bg-[color:var(--color-success-alpha-15)] text-accent-green',
  增持: 'bg-accent-green/15 text-accent-green',
  减持: 'bg-[color:var(--color-badge-amber-bg)] text-[color:var(--color-badge-amber-text)]',
  退出: 'bg-outline-variant/30 text-text-secondary',
};

interface ShareholderSidebarLeftProps {
  holdings: Holding[];
  changes: ChangeRecord[];
  timeQuarter: string;
  quarters: string[];
  onTimeChange: (q: string) => void;
  onRowClick: (h: Holding) => void;
  onBacktest: (h: Holding) => void;
  onExportCsv: () => void;
}

export function ShareholderSidebarLeft({
  holdings,
  changes,
  timeQuarter,
  quarters,
  onTimeChange,
  onRowClick,
  onBacktest,
  onExportCsv,
}: ShareholderSidebarLeftProps) {
  const idx = Math.max(0, quarters.indexOf(timeQuarter));
  const minIdx = 0;
  const maxIdx = quarters.length - 1;

  return (
    <div className="space-y-4">
      {/* 时间轴滑块 */}
      <div className="card">
        <label className="mb-2 block text-sm font-medium text-text-primary">
          时间范围
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-dim">{quarters[0]}</span>
          <input
            type="range"
            min={minIdx}
            max={maxIdx}
            value={idx}
            onChange={(e) => onTimeChange(quarters[Number(e.target.value)])}
            className="flex-1 accent-fund-indigo"
          />
          <span className="text-xs text-text-dim">{quarters[maxIdx]}</span>
        </div>
        <div className="mt-1 text-center text-sm font-medium text-on-surface">
          {timeQuarter}
        </div>
      </div>

      {/* 当前持仓列表 */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-on-surface">当前持仓</h3>
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-card-border text-left text-text-secondary">
                <th className="py-2 pr-2">代码</th>
                <th className="py-2 pr-2">名称</th>
                <th className="py-2 pr-2">市值(亿)</th>
                <th className="py-2 pr-2">流通比%</th>
                <th className="py-2">首次</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr
                  key={h.stockCode}
                  className="cursor-pointer border-b border-card-border/80 hover:bg-surface-container-high/30"
                  onClick={() => onRowClick(h)}
                >
                  <td className="py-2 pr-2 font-mono text-text-primary">
                    {h.stockCode}
                  </td>
                  <td className="py-2 pr-2 text-on-surface">{h.stockName}</td>
                  <td className="py-2 pr-2 text-text-primary">
                    {h.holdValue.toFixed(2)}
                  </td>
                  <td className="py-2 pr-2 text-text-primary">{h.ratio.toFixed(2)}</td>
                  <td className="py-2 text-text-secondary">{h.firstEntry}</td>
                  <td>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onBacktest(h);
                      }}
                      className="text-xs text-fund-indigo hover:underline"
                    >
                      回溯
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {holdings.length === 0 && (
          <p className="py-4 text-center text-sm text-text-dim">该时点无持仓</p>
        )}
      </div>

      {/* 历史变动流水 */}
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-on-surface">历史变动流水</h3>
          <button
            type="button"
            onClick={onExportCsv}
            className="text-xs text-fund-indigo hover:underline"
          >
            导出 CSV
          </button>
        </div>
        <div className="max-h-72 overflow-auto space-y-2">
          {changes.map((c, i) => (
            <div
              key={`${c.quarter}-${c.stockCode}-${i}`}
              className="flex items-center justify-between rounded border border-card-border/50 bg-surface-container-high/50 px-3 py-2 text-sm"
            >
              <span className="text-text-dim">{c.quarter}</span>
              <span
                className={`rounded px-2 py-0.5 text-xs ${
                  ACTION_COLORS[c.action] ?? 'bg-surface-container-high text-text-secondary'
                }`}
              >
                {c.action}
              </span>
              <span className="text-on-surface">{c.stockName}</span>
              <span className="text-text-secondary">
                {c.changeShares > 0 ? '+' : ''}
                {c.changeShares}万
                {c.changeRatio != null ? ` (${c.changeRatio}%)` : ''}
              </span>
            </div>
          ))}
        </div>
        {changes.length === 0 && (
          <p className="py-4 text-center text-sm text-text-dim">暂无变动记录</p>
        )}
      </div>
    </div>
  );
}
