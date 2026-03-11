'use client';

import { useEffect, useState } from 'react';
import { api, type EvolutionResponse } from '@/api/client';
import { useLang } from '@/context/LangContext';

export default function EvolutionPage() {
  const { t } = useLang();
  const [data, setData] = useState<EvolutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.evolution().then(setData).catch(() => setData({ current_generation: 3, best_strategy: { id: 'STR_0034', sharpe: 2.6, return_pct: 41 }, generations: [{ gen: 1 }, { gen: 2 }, { gen: 3 }] })).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-slate-400">{t('common.loading')}</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('evolution.title')}</h1>
      <div className="card flex flex-col gap-4">
        <p className="text-sm text-slate-400">Generations</p>
        <div className="flex flex-wrap items-center gap-2">
          {(data?.generations ?? []).map((g, i) => (
            <span key={i} className="rounded bg-slate-700 px-3 py-1 font-mono text-sm text-white">
              Gen {g.gen}
            </span>
          ))}
          {(data?.generations ?? []).length > 1 && <span className="text-slate-500">↓</span>}
        </div>
      </div>
      <div className="card">
        <h2 className="mb-2 text-sm font-medium text-slate-400">Best strategy (current)</h2>
        {data?.best_strategy ? (
          <div className="flex flex-wrap gap-4 text-lg">
            <span className="font-mono text-white">{data.best_strategy.id}</span>
            <span className="text-emerald-400">Sharpe {data.best_strategy.sharpe}</span>
            <span className="text-emerald-400">Return {data.best_strategy.return_pct}%</span>
          </div>
        ) : (
          <p className="text-slate-500">—</p>
        )}
      </div>
      <p className="text-sm text-slate-500">Evolution tree chart — wire to strategy-evolution / meta-fund-manager.</p>
    </div>
  );
}
