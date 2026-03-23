'use client';

import type { Holding, ChangeRecord } from '@/data/mockShareholder';

const ACTION_COLORS: Record<string, string> = {
  新进: 'bg-emerald-500/30 text-emerald-400',
  增持: 'bg-emerald-400/20 text-emerald-300',
  减持: 'bg-amber-500/30 text-amber-400',
  退出: 'bg-slate-500/30 text-slate-400',
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
        <label className="mb-2 block text-sm font-medium text-slate-300">
          时间范围
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{quarters[0]}</span>
          <input
            type="range"
            min={minIdx}
            max={maxIdx}
            value={idx}
            onChange={(e) => onTimeChange(quarters[Number(e.target.value)])}
            className="flex-1 accent-fund-indigo"
          />
          <span className="text-xs text-slate-500">{quarters[maxIdx]}</span>
        </div>
        <div className="mt-1 text-center text-sm font-medium text-white">
          {timeQuarter}
        </div>
      </div>

      {/* 当前持仓列表 */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-white">当前持仓</h3>
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-600 text-left text-slate-400">
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
                  className="cursor-pointer border-b border-slate-700/50 hover:bg-slate-700/30"
                  onClick={() => onRowClick(h)}
                >
                  <td className="py-2 pr-2 font-mono text-slate-300">
                    {h.stockCode}
                  </td>
                  <td className="py-2 pr-2 text-white">{h.stockName}</td>
                  <td className="py-2 pr-2 text-slate-300">
                    {h.holdValue.toFixed(2)}
                  </td>
                  <td className="py-2 pr-2 text-slate-300">{h.ratio.toFixed(2)}</td>
                  <td className="py-2 text-slate-400">{h.firstEntry}</td>
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
          <p className="py-4 text-center text-sm text-slate-500">该时点无持仓</p>
        )}
      </div>

      {/* 历史变动流水 */}
      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">历史变动流水</h3>
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
              className="flex items-center justify-between rounded border border-slate-600/50 bg-slate-800/50 px-3 py-2 text-sm"
            >
              <span className="text-slate-500">{c.quarter}</span>
              <span
                className={`rounded px-2 py-0.5 text-xs ${
                  ACTION_COLORS[c.action] ?? 'bg-slate-600 text-slate-400'
                }`}
              >
                {c.action}
              </span>
              <span className="text-white">{c.stockName}</span>
              <span className="text-slate-400">
                {c.changeShares > 0 ? '+' : ''}
                {c.changeShares}万
                {c.changeRatio != null ? ` (${c.changeRatio}%)` : ''}
              </span>
            </div>
          ))}
        </div>
        {changes.length === 0 && (
          <p className="py-4 text-center text-sm text-slate-500">暂无变动记录</p>
        )}
      </div>
    </div>
  );
}
