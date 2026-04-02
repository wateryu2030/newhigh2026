'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, type EvolutionResponse } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { AsyncState } from '@/components/AsyncState';

export default function EvolutionPage() {
  const { t } = useLang();
  const [data, setData] = useState<EvolutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvolution = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .evolution()
      .then(setData)
      .catch(() => {
        setData(null);
        setError(t('evolution.loadError'));
      })
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    fetchEvolution();
  }, [fetchEvolution]);

  return (
    <div className="space-y-6 min-h-screen pb-24 md:pb-6">
      <h1 className="text-2xl font-bold text-white">{t('evolution.title')}</h1>
      <AsyncState<EvolutionResponse>
        loading={loading}
        error={error}
        data={loading || error ? undefined : data ?? undefined}
        isEmpty={(d) => (d.generations?.length ?? 0) === 0 && d.best_strategy == null}
        emptyTitle={t('evolution.emptyTitle')}
        emptyDescription={t('evolution.emptyDesc')}
        loadingMessage={t('common.loading')}
        onRetry={fetchEvolution}
      >
        {(d) => (
          <>
            <div className="card flex flex-col gap-4">
              <p className="text-sm text-slate-400">Generations</p>
              <div className="flex flex-wrap items-center gap-2">
                {(d.generations ?? []).map((g, i) => (
                  <span key={i} className="rounded bg-slate-700 px-3 py-1 font-mono text-sm text-white">
                    Gen {g.gen}
                  </span>
                ))}
                {(d.generations ?? []).length > 1 && <span className="text-slate-500">↓</span>}
              </div>
            </div>
            <div className="card">
              <h2 className="mb-2 text-sm font-medium text-slate-400">Best strategy (current)</h2>
              {d.best_strategy ? (
                <div className="flex flex-wrap gap-4 text-lg">
                  <span className="font-mono text-white">{d.best_strategy.id}</span>
                  <span className="text-emerald-400">Sharpe {d.best_strategy.sharpe}</span>
                  <span className="text-emerald-400">Return {d.best_strategy.return_pct}%</span>
                </div>
              ) : (
                <p className="text-slate-500">—</p>
              )}
            </div>
            <p className="text-sm text-slate-500">Evolution tree — wire to strategy-evolution / meta-fund-manager.</p>
          </>
        )}
      </AsyncState>
    </div>
  );
}
