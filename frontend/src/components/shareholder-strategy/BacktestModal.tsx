'use client';

import type { Holding } from '@/data/mockShareholder';

interface BacktestModalProps {
  open: boolean;
  onClose: () => void;
  stock: Holding | null;
}

export function BacktestModal({ open, onClose, stock }: BacktestModalProps) {
  if (!open || !stock) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-600 bg-slate-800 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">策略回溯</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-2 text-slate-400 hover:bg-slate-700 hover:text-white"
          >
            ✕
          </button>
        </div>
        <p className="text-slate-300">
          <span className="font-medium text-white">{stock.stockName}</span>（
          {stock.stockCode}）自 {stock.firstEntry} 建仓
          {stock.exitQuarter ? ` 至 ${stock.exitQuarter} 清仓` : ' 至今持有'}。
        </p>
        <p className="mt-2 text-sm text-slate-500">
          模拟收益计算需接入历史行情数据，此处仅作提示。完整回溯功能将在后续版本提供。
        </p>
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-fund-indigo px-4 py-2 text-sm text-white hover:bg-fund-indigo/90"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
