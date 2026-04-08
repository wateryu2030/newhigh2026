'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type AlphaLabDrillItem, type AlphaLabResponse } from '@/api/client';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useLang } from '@/context/LangContext';
import { StockPenetrationPanel, type StockPenetrationRow } from '@/components/StockPenetrationPanel';
import { AsyncState } from '@/components/AsyncState';
import { PageLoading } from '@/components/LoadingSpinner';
import {
  chartFunnelColors,
  rechartsTooltipContent,
  rechartsTickSecondary,
  rechartsTickSecondary11,
} from '@/lib/chartTheme';

type AlphaStage = 'generated' | 'backtest' | 'risk' | 'deployed';

export default function AlphaLabPage() {
  const { t } = useLang();
  const [data, setData] = useState<AlphaLabResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  /** 始终选中某一阶段，下方表格常驻，避免「没有下钻入口」 */
  const [selectedStage, setSelectedStage] = useState<AlphaStage>('generated');
  const [drillItems, setDrillItems] = useState<AlphaLabDrillItem[]>([]);
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillError, setDrillError] = useState<string | null>(null);
  const [detailRow, setDetailRow] = useState<StockPenetrationRow | null>(null);
  const listAnchorRef = useRef<HTMLDivElement | null>(null);

  const fetchSummary = useCallback(() => {
    setSummaryLoading(true);
    setSummaryError(null);
    api
      .alphaLab()
      .then(setData)
      .catch((e) => {
        setData(null);
        setSummaryError(e instanceof Error ? e.message : t('alphaLab.summaryError'));
      })
      .finally(() => setSummaryLoading(false));
  }, [t]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

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
          setDrillError(e instanceof Error ? e.message : t('alphaLab.drillError'));
        }
      })
      .finally(() => {
        if (!cancelled) setDrillLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedStage, t]);

  const retryDrill = useCallback(() => {
    setDrillLoading(true);
    setDrillError(null);
    api
      .alphaLabDrill(selectedStage, 200)
      .then((r) => {
        setDrillItems(r.items || []);
        setDrillError(null);
      })
      .catch((e) => {
        setDrillItems([]);
        setDrillError(e instanceof Error ? e.message : t('alphaLab.drillError'));
      })
      .finally(() => setDrillLoading(false));
  }, [selectedStage, t]);

  const selectStage = (s: AlphaStage) => {
    setDetailRow(null);
    setSelectedStage(s);
    requestAnimationFrame(() => {
      listAnchorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  if (detailRow) {
    return (
      <div className="space-y-4 min-h-screen pb-24 md:pb-6">
        <StockPenetrationPanel row={detailRow} onBack={() => setDetailRow(null)} />
      </div>
    );
  }

  return (
    <div className="space-y-6 min-h-screen pb-24 md:pb-6">
      <h1 className="text-2xl font-bold text-on-surface">{t('alphaLab.title')}</h1>
      <p className="text-sm text-text-secondary">{t('alphaLab.drillHint')}</p>

      <AsyncState<AlphaLabResponse>
        loading={summaryLoading}
        error={summaryError}
        data={summaryLoading || summaryError ? undefined : data ?? undefined}
        isEmpty={() => false}
        loadingMessage={t('common.loading')}
        onRetry={fetchSummary}
      >
        {(d) => {
          const funnel = [
            {
              stage: 'generated' as const,
              name: t('alphaLab.funnel.generated'),
              value: d.generated_today,
              fill: chartFunnelColors[0],
            },
            {
              stage: 'backtest' as const,
              name: t('alphaLab.funnel.backtest'),
              value: d.passed_backtest,
              fill: chartFunnelColors[1],
            },
            {
              stage: 'risk' as const,
              name: t('alphaLab.funnel.risk'),
              value: d.passed_risk,
              fill: chartFunnelColors[2],
            },
            {
              stage: 'deployed' as const,
              name: t('alphaLab.funnel.deployed'),
              value: d.deployed,
              fill: chartFunnelColors[3],
            },
          ];
          return (
          <>
            {d.binding_note ? (
              <details className="rounded-lg border border-card-border bg-terminal-bg/40 px-3 py-2 text-sm text-text-dim">
                <summary className="cursor-pointer text-text-secondary">{t('alphaLab.bindingNote')}</summary>
                <p className="mt-2 leading-relaxed">{d.binding_note}</p>
              </details>
            ) : null}
            <div className="grid-dashboard">
              {(
                [
                  ['generated', d.generated_today, 'text-on-surface', 'hover:ring-primary-fixed/50'] as const,
                  [
                    'backtest',
                    d.passed_backtest,
                    'text-[color:var(--color-chart-purple)]',
                    'hover:ring-[color:var(--color-chart-purple)]/50',
                  ] as const,
                  ['risk', d.passed_risk, 'text-accent-green', 'hover:ring-accent-green/50'] as const,
                  [
                    'deployed',
                    d.deployed,
                    'text-accent-green',
                    'hover:ring-[color:var(--color-chart-emerald-dark)]/50',
                  ] as const,
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
                      active ? 'ring-2 ring-primary-fixed/70 ring-offset-2 ring-offset-surface' : ''
                    }`}
                    onClick={() => selectStage(st)}
                  >
                    <p className="text-sm text-text-secondary">{label}</p>
                    <p className={`text-2xl font-bold ${color}`}>{num}</p>
                    <p className="mt-1 text-xs text-primary-fixed/90">{t('alphaLab.cardCta')} →</p>
                  </button>
                );
              })}
            </div>
            <div className="card">
              <p className="mb-4 text-sm font-medium text-text-secondary">Pipeline funnel</p>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={funnel} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                  <XAxis dataKey="name" tick={rechartsTickSecondary11} />
                  <YAxis tick={rechartsTickSecondary} />
                  <Tooltip contentStyle={rechartsTooltipContent} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} cursor="pointer">
                    {funnel.map((entry) => (
                      <Cell
                        key={entry.stage}
                        fill={entry.fill}
                        stroke={selectedStage === entry.stage ? 'var(--color-chart-slate-stroke)' : undefined}
                        strokeWidth={selectedStage === entry.stage ? 2 : 0}
                        style={{ cursor: 'pointer' }}
                        onClick={() => selectStage(entry.stage)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="mt-2 text-xs text-text-dim">{t('alphaLab.stockListSub')}</p>
            </div>

            <div ref={listAnchorRef} className="card space-y-3 scroll-mt-4">
              <div className="flex flex-wrap items-end justify-between gap-2 border-b border-[color:var(--color-border-subtle)] pb-3">
                <div>
                  <h2 className="text-lg font-semibold text-on-surface">
                    {t('alphaLab.stockListTitle')} · {funnel.find((x) => x.stage === selectedStage)?.name}
                  </h2>
                  <p className="text-xs text-text-dim">API: /api/alpha-lab/drill · source: {d.source ?? '—'}</p>
                </div>
              </div>
              {drillError ? (
                <div
                  className="rounded-md border border-[color:var(--color-warning-banner-border)] bg-[color:var(--color-warning-banner-bg)] px-3 py-3 text-sm text-[color:var(--color-badge-amber-text)]"
                  role="alert"
                >
                  <p>{drillError}</p>
                  <button
                    type="button"
                    onClick={() => retryDrill()}
                    className="mt-2 rounded-lg bg-[color:var(--color-badge-amber-bg)] px-3 py-1.5 text-on-surface hover:opacity-90"
                  >
                    重试
                  </button>
                </div>
              ) : null}
              {drillLoading ? (
                <PageLoading message={t('common.loading')} />
              ) : drillItems.length === 0 ? (
                <p className="text-text-dim">{t('alphaLab.drillEmpty')}</p>
              ) : (
                <div className="max-h-[min(520px,55vh)] overflow-auto rounded-lg border border-card-border">
                  <table className="w-full text-left text-sm text-on-surface">
                    <thead className="sticky top-0 z-10 bg-terminal-bg/95 text-xs uppercase text-text-dim">
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
                          className="cursor-pointer border-t border-[color:var(--color-border-subtle)] hover:bg-surface-container-high/50 active:bg-surface-container-high/70"
                          onClick={() =>
                            setDetailRow({
                              code: row.code,
                              stock_name: row.stock_name || undefined,
                            })
                          }
                        >
                          <td className="px-3 py-2 font-mono text-primary-fixed">{row.code}</td>
                          <td className="px-3 py-2 text-text-primary">{row.stock_name || '—'}</td>
                          <td className="px-3 py-2 text-text-secondary">{row.subtitle ?? '—'}</td>
                          <td className="px-3 py-2">
                            {row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : '—'}
                          </td>
                          <td className="px-3 py-2 text-xs text-text-dim">
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
          </>
          );
        }}
      </AsyncState>
    </div>
  );
}
