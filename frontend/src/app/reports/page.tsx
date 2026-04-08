'use client';

import { useLang } from '@/context/LangContext';

export default function ReportsPage() {
  const { t } = useLang();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-on-surface">{t('reports.title')}</h1>
      <div className="grid-dashboard">
        <div className="card">
          <p className="text-sm text-text-secondary">Return</p>
          <p className="text-2xl font-bold text-accent-green">+12.4%</p>
        </div>
        <div className="card">
          <p className="text-sm text-text-secondary">Sharpe</p>
          <p className="text-2xl font-bold text-on-surface">2.1</p>
        </div>
        <div className="card">
          <p className="text-sm text-text-secondary">Drawdown</p>
          <p className="text-2xl font-bold text-on-surface">6.3%</p>
        </div>
      </div>
      <div className="card">
        <p className="mb-2 text-sm text-text-secondary">Export</p>
        <button className="rounded-lg bg-primary-fixed px-4 py-2 text-sm font-medium text-on-warm-fill hover:opacity-90">
          Export PDF (stub)
        </button>
      </div>
    </div>
  );
}
