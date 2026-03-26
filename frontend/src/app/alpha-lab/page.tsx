'use client';

import { useEffect, useState } from 'react';
import { api, type AlphaLabDrillItem, type AlphaLabResponse } from '@/api/client';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useLang } from '@/context/LangContext';
import { StockPenetrationPanel, type StockPenetrationRow } from '@/components/StockPenetrationPanel';

type AlphaStage = 'generated' | 'backtest' | 'risk' | 'deployed';

const EMPTY_ALPHA: AlphaLabResponse = {
  generated_today: 0,
  passed_backtest: 0,
  passed_risk: 0,
  deployed: 0,
};

export default function AlphaLabPage() {
  const { t } = useLang();
  const [data, setData] = useState<AlphaLabResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [drillStage, setDrillStage] = useState<AlphaStage | null>(null);
  const [drillItems, setDrillItems] = useState<AlphaLabDrillItem[]>([]);
  const [drillLoading, setDrillLoading] = useState(false);
  const [detailRow, setDetailRow] = useState<StockPenetrationRow | null>(null);

  useEffect(() => {
    api
      .alphaLab()
      .then(setData)
      .catch(() => setData(EMPTY_ALPHA))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!drillStage) {
      setDrillItems([]);
      return;
    }
    setDrillLoading(true);
    api
      .alphaLabDrill(drillStage, 200)
      .then((r) => setDrillItems(r.items || []))
      .catch(() => setDrillItems([]))
      .finally(() => setDrillLoading(false));
  }, [drillStage]);

  if (loading) return <div className="py-12 text-center text-slate-400">{t('common.loading')}</div>;

  const d = data ?? EMPTY_ALPHA;

  const funnel = [
    {
      stage: 'generated' as const,
      name: t('alphaLab.funnel.generated'),
      value: d.generated_today,
      fill: '#6366F1',
    },
    {
      stage: 'backtest' as const,
      name: t('alphaLab.funnel.backtest'),
      value: d.passed_backtest,
      fill: '#8b5cf6',
    },
    {
      stage: 'risk' as const,
      name: t('alphaLab.funnel.risk'),
      value: d.passed_risk,
      fill: '#10B981',
    },
    {
      stage: 'deployed' as const,
      name: t('alphaLab.funnel.deployed'),
      value: d.deployed,
      fill: '#059669',
    },
  ];

  const openStage = (s: AlphaStage) => {
    setDetailRow(null);
    setDrillStage(s);
  };

  if (detailRow) {
    return (
      <div className="space-y-4">
        <StockPenetrationPanel
          row={detailRow}
          onBack={() => setDetailRow(null)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('alphaLab.title')}</h1>
      <p className="text-sm text-slate-400">{t('alphaLab.drillHint')}</p>
      {d.binding_note ? (
        <details className="rounded-lg border border-slate-700/80 bg-slate-900/40 px-3 py-2 text-sm text-slate-500">
          <summary className="cursor-pointer text-slate-400">{t('alphaLab.bindingNote')}</summary>
          <p className="mt-2 leading-relaxed">{d.binding_note}</p>
        </details>
      ) : null}
      <div className="grid-dashboard">
        <button
          type="button"
          className="card cursor-pointer text-left transition hover:ring-1 hover:ring-indigo-500/50"
          onClick={() => openStage('generated')}
        >
          <p className="text-sm text-slate-400">{t('alphaLab.funnel.generated')}</p>
          <p className="text-2xl font-bold text-white">{d.generated_today}</p>
        </button>
        <button
          type="button"
          className="card cursor-pointer text-left transition hover:ring-1 hover:ring-violet-500/50"
          onClick={() => openStage('backtest')}
        >
          <p className="text-sm text-slate-400">{t('alphaLab.funnel.backtest')}</p>
          <p className="text-2xl font-bold text-violet-400">{d.passed_backtest}</p>
        </button>
        <button
          type="button"
          className="card cursor-pointer text-left transition hover:ring-1 hover:ring-emerald-500/50"
          onClick={() => openStage('risk')}
        >
          <p className="text-sm text-slate-400">{t('alphaLab.funnel.risk')}</p>
          <p className="text-2xl font-bold text-emerald-500">{d.passed_risk}</p>
        </button>
        <button
          type="button"
          className="card cursor-pointer text-left transition hover:ring-1 hover:ring-emerald-600/50"
          onClick={() => openStage('deployed')}
        >
          <p className="text-sm text-slate-400">{t('alphaLab.funnel.deployed')}</p>
          <p className="text-2xl font-bold text-emerald-400">{d.deployed}</p>
        </button>
      </div>
      <div className="card">
        <p className="mb-4 text-sm font-medium text-slate-400">Pipeline funnel</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={funnel} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
            <Bar
              dataKey="value"
              radius={[4, 4, 0, 0]}
              cursor="pointer"
              onClick={(e) => {
                const payload = (e as { payload?: { stage?: AlphaStage } }).payload;
                if (payload?.stage) openStage(payload.stage);
              }}
            >
              {funnel.map((entry) => (
                <Cell key={entry.stage} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {drillStage ? (
        <div className="card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-white">
              {t('alphaLab.drillTitle')} · {funnel.find((x) => x.stage === drillStage)?.name}
            </h2>
            <button
              type="button"
              className="rounded-md border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
              onClick={() => setDrillStage(null)}
            >
              {t('alphaLab.backList')}
            </button>
          </div>
          {drillLoading ? (
            <p className="text-slate-400">{t('common.loading')}</p>
          ) : drillItems.length === 0 ? (
            <p className="text-slate-500">{t('alphaLab.drillEmpty')}</p>
          ) : (
            <div className="max-h-[420px] overflow-auto rounded-lg border border-slate-700/60">
              <table className="w-full text-left text-sm text-slate-200">
                <thead className="sticky top-0 bg-slate-900/95 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">{t('alphaLab.col.code')}</th>
                    <th className="px-3 py-2">{t('alphaLab.col.name')}</th>
                    <th className="px-3 py-2">{t('alphaLab.col.detail')}</th>
                    <th className="px-3 py-2">{t('alphaLab.col.conf')}</th>
                    <th className="px-3 py-2">{t('alphaLab.col.time')}</th>
                  </tr>
                </thead>
                <tbody>
                  {drillItems.map((row) => (
                    <tr
                      key={`${row.code}-${row.snapshot_time ?? ''}-${row.subtitle ?? ''}`}
                      className="cursor-pointer border-t border-slate-800/80 hover:bg-slate-800/50"
                      onClick={() =>
                        setDetailRow({
                          code: row.code,
                          stock_name: row.stock_name || undefined,
                        })
                      }
                    >
                      <td className="px-3 py-2 font-mono text-indigo-300">{row.code}</td>
                      <td className="px-3 py-2 text-slate-300">{row.stock_name || '—'}</td>
                      <td className="px-3 py-2 text-slate-400">{row.subtitle ?? '—'}</td>
                      <td className="px-3 py-2">
                        {row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-500">
                        {row.snapshot_time
                          ? String(row.snapshot_time).replace('T', ' ').slice(0, 19)
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="text-xs text-slate-600">source: {d.source ?? '—'}</p>
        </div>
      ) : null}
    </div>
  );
}
