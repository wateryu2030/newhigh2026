'use client';

import { useLang } from '@/context/LangContext';

export default function ReportsPage() {
  const { t } = useLang();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('reports.title')}</h1>
      <div className="grid-dashboard">
        <div className="card"><p className="text-sm text-slate-400">Return</p><p className="text-2xl font-bold text-emerald-400">+12.4%</p></div>
        <div className="card"><p className="text-sm text-slate-400">Sharpe</p><p className="text-2xl font-bold text-white">2.1</p></div>
        <div className="card"><p className="text-sm text-slate-400">Drawdown</p><p className="text-2xl font-bold text-white">6.3%</p></div>
      </div>
      <div className="card">
        <p className="mb-2 text-sm text-slate-400">Export</p>
        <button className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          Export PDF (stub)
        </button>
      </div>
    </div>
  );
}
