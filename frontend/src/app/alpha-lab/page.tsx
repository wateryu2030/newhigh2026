'use client';

import { useEffect, useRef, useState } from 'react';
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
  /** 始终选中某一阶段，下方表格常驻，避免「没有下钻入口」 */
  const [selectedStage, setSelectedStage] = useState<AlphaStage>('generated');
  const [drillItems, setDrillItems] = useState<AlphaLabDrillItem[]>([]);
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillError, setDrillError] = useState<string | null>(null);
  const [detailRow, setDetailRow] = useState<StockPenetrationRow | null>(null);
  const listAnchorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    api
      .alphaLab()
      .then(setData)
      .catch(() => setData(EMPTY_ALPHA))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setDrillLoading(true);
    setDrillError(null);
    api
      .alphaLabDrill(selectedStage, 200)
      .then((r) => {
        if (!cancelled) {
          setDrillItems(r.items || []);
          setDrillError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setDrillItems([]);
          setDrillError(e instanceof Error ? e.message : 'alpha-lab/drill error');
        }
      })
      .finally(() => {
        if (!cancelled) setDrillLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedStage]);

  const selectStage = (s: AlphaStage) => {
    setDetailRow(null);
    setSelectedStage(s);
    requestAnimationFrame(() => {
      listAnchorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

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
        {(
          [
            ['generated', d.generated_today, 'text-white', 'hover:ring-indigo-500/50'] as const,
            ['backtest', d.passed_backtest, 'text-violet-400', 'hover:ring-violet-500/50'] as const,
            ['risk', d.passed_risk, 'text-emerald-500', 'hover:ring-emerald-500/50'] as const,
            ['deployed', d.deployed, 'text-emerald-400', 'hover:ring-emerald-600/50'] as const,
          ] as const
        ).map(([key, num, color, hoverRing]) => {
          const st = key as AlphaStage;
          const label =
            key === 'generated'
              ? t('alphaLab.funnel.generated')
              : key === 'backtest'
                ? t('alphaLab.funnel.backtest')
                : key === 'risk'
                  ? t('alphaLab.funnel.risk')
                  : t('alphaLab.funnel.deployed');
          const active = selectedStage === st;
          return (
            <button
              key={key}
              type="button"
              className={`card cursor-pointer text-left transition ${hoverRing} ${
                active ? 'ring-2 ring-indigo-400/70 ring-offset-2 ring-offset-[#0B0E14]' : ''
              }`}
              onClick={() => selectStage(st)}
            >
              <p className="text-sm text-slate-400">{label}</p>
              <p className={`text-2xl font-bold ${color}`}>{num}</p>
              <p className="mt-1 text-xs text-indigo-400/90">{t('alphaLab.cardCta')} →</p>
            </button>
          );
        })}
      </div>
      <div className="card">
        <p className="mb-4 text-sm font-medium text-slate-400">Pipeline funnel</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={funnel} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} cursor="pointer">
              {funnel.map((entry) => (
                <Cell
                  key={entry.stage}
                  fill={entry.fill}
                  stroke={selectedStage === entry.stage ? '#e2e8f0' : undefined}
                  strokeWidth={selectedStage === entry.stage ? 2 : 0}
                  style={{ cursor: 'pointer' }}
                  onClick={() => selectStage(entry.stage)}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="mt-2 text-xs text-slate-500">{t('alphaLab.stockListSub')}</p>
      </div>

      <div ref={listAnchorRef} className="card space-y-3 scroll-mt-4">
        <div className="flex flex-wrap items-end justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {t('alphaLab.stockListTitle')} · {funnel.find((x) => x.stage === selectedStage)?.name}
            </h2>
            <p className="text-xs text-slate-500">
              API: /api/alpha-lab/drill · source: {d.source ?? '—'}
            </p>
          </div>
        </div>
        {drillError ? (
          <p className="rounded-md border border-amber-900/50 bg-amber-950/30 px-3 py-2 text-sm text-amber-200">
            {drillError}
          </p>
        ) : null}
        {drillLoading ? (
          <p className="text-slate-400">{t('common.loading')}</p>
        ) : drillItems.length === 0 ? (
          <p className="text-slate-500">{t('alphaLab.drillEmpty')}</p>
        ) : (
          <div className="max-h-[min(520px,55vh)] overflow-auto rounded-lg border border-slate-700/60">
            <table className="w-full text-left text-sm text-slate-200">
              <thead className="sticky top-0 z-10 bg-slate-900/95 text-xs uppercase text-slate-500">
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
      </div>
    </div>
  );
}
