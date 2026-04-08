'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  api,
  type DataQualityLatest,
  type SystemStatusResponse,
  type EvolutionTaskItem,
} from '@/api/client';
import { useLang } from '@/context/LangContext';

function statusLabel(s: 'running' | 'error' | 'idle', t: (k: string) => string) {
  if (s === 'running') return t('systemMonitor.statusRunning');
  if (s === 'error') return t('systemMonitor.statusError');
  return t('systemMonitor.statusIdle');
}

function statusColor(s: 'running' | 'error' | 'idle') {
  if (s === 'running') return 'text-accent-green';
  if (s === 'error') return 'text-[color:var(--color-chart-amber)]';
  return 'text-text-dim';
}

function evolutionBadgeClass(status: string) {
  const s = (status || '').toLowerCase();
  if (s === 'success') return 'bg-accent-green/90 text-on-surface';
  if (s === 'failed') return 'bg-accent-red/90 text-on-surface';
  if (s === 'running') return 'bg-[color:var(--color-chart-amber)]/90 text-on-surface';
  return 'bg-outline-variant/80 text-on-surface';
}

export default function SystemMonitorPage() {
  const { t } = useLang();
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [evolutionTasks, setEvolutionTasks] = useState<EvolutionTaskItem[]>([]);
  const [skillStats, setSkillStats] = useState<{ call_count: number; last_call_time: string | null }>({ call_count: 0, last_call_time: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [dataQuality, setDataQuality] = useState<DataQualityLatest | null | undefined>(undefined);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.systemStatus(20),
      api.getEvolutionTasks(5).then((r) => r.tasks || []),
      api.getSkillStats().catch(() => ({ call_count: 0, last_call_time: null })),
      api.dataQuality().catch(() => null),
    ])
      .then(([s, tasks, stats, dq]) => {
        setStatus(s);
        setEvolutionTasks(tasks);
        setSkillStats(stats);
        setDataQuality(dq);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'API error'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleTriggerEvolution = () => {
    setTriggering(true);
    api
      .triggerEvolution('strategy_generation')
      .then(() => refresh())
      .catch((e) => setError(e instanceof Error ? e.message : 'Trigger failed'))
      .finally(() => setTriggering(false));
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <p className="text-text-dim">{t('common.loading')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-lg border border-[color:var(--color-warning-banner-border)] bg-[color:var(--color-warning-banner-bg)] p-4 text-sm text-[color:var(--color-badge-amber-text)]">
          <p className="font-medium">
            {t('common.error')}: {error}
          </p>
          <p className="mt-2 text-text-secondary">{t('systemMonitor.runHint')}</p>
          <button
            type="button"
            onClick={refresh}
            disabled={loading}
            className="mt-3 rounded bg-surface-container-highest px-3 py-1.5 text-sm text-on-surface hover:opacity-90 disabled:opacity-50"
          >
            刷新
          </button>
        </div>
      )}

      {status && (
        <>
          <section className="card">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-on-surface">当前状态</h2>
              <button
                type="button"
                onClick={refresh}
                disabled={loading}
                className="rounded bg-surface-container-highest px-3 py-1.5 text-sm text-on-surface hover:opacity-90 disabled:opacity-50"
              >
                刷新
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-sm text-text-dim">{t('systemMonitor.dataPipeline')}</p>
                <p className={`font-medium ${statusColor(status.data_pipeline)}`}>
                  {statusLabel(status.data_pipeline, t)}
                </p>
              </div>
              <div>
                <p className="text-sm text-text-dim">{t('systemMonitor.scanner')}</p>
                <p className={`font-medium ${statusColor(status.scanner)}`}>
                  {statusLabel(status.scanner, t)}
                </p>
              </div>
              <div>
                <p className="text-sm text-text-dim">{t('systemMonitor.aiModels')}</p>
                <p className={`font-medium ${statusColor(status.ai_models)}`}>
                  {statusLabel(status.ai_models, t)}
                </p>
              </div>
              <div>
                <p className="text-sm text-text-dim">{t('systemMonitor.strategyEngine')}</p>
                <p className={`font-medium ${statusColor(status.strategy_engine)}`}>
                  {statusLabel(status.strategy_engine, t)}
                </p>
              </div>
            </div>
            <div className="mt-4 border-t border-card-border pt-4">
              <p className="text-sm text-text-dim">{t('systemMonitor.lastUpdate')}</p>
              <p className="font-mono text-sm text-on-surface">
                {status.last_update ?? '—'}
              </p>
            </div>
          </section>

          {status.history?.length > 0 && (
            <section className="card">
              <h2 className="mb-4 text-lg font-semibold text-on-surface">{t('systemMonitor.history')}</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-card-border text-text-secondary">
                      <th className="text-left py-2 pr-4">data_status</th>
                      <th className="text-left py-2 pr-4">scanner_status</th>
                      <th className="text-left py-2 pr-4">ai_status</th>
                      <th className="text-left py-2 pr-4">strategy_status</th>
                      <th className="text-left py-2">snapshot_time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.history.slice(0, 15).map((row, i) => (
                      <tr key={i} className="border-b border-[color:var(--color-border-subtle)]">
                        <td className="py-2 pr-4 text-text-primary">{row.data_status ?? '—'}</td>
                        <td className="py-2 pr-4 text-text-primary">{row.scanner_status ?? '—'}</td>
                        <td className="py-2 pr-4 text-text-primary">{row.ai_status ?? '—'}</td>
                        <td className="py-2 pr-4 text-text-primary">{row.strategy_status ?? '—'}</td>
                        <td className="py-2 font-mono text-text-dim">{row.snapshot_time ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <section
            className={`card ${
              (() => {
                const sh = dataQuality?.report?.checks?.find((c) => c.name === 'shareholder_top10')
                  ?.result as { coverage_rate_pct?: number } | undefined;
                const cov = sh?.coverage_rate_pct;
                return typeof cov === 'number' && cov < 90
                  ? 'border border-[color:var(--color-error-banner-border)] bg-[color:var(--color-error-banner-bg)]'
                  : 'bg-card-bg/80';
              })()
            }`}
          >
            <h3 className="mb-4 text-lg font-semibold text-on-surface">数据质量</h3>
            {dataQuality === undefined ? (
              <p className="text-sm text-text-dim">加载中…</p>
            ) : dataQuality === null ? (
              <p className="text-sm text-text-dim">暂无巡检记录。可运行 scripts/run_data_quality_checks.py 或等待定时任务。</p>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">最近检查时间</span>
                  <span className="font-mono text-xs text-on-surface">
                    {dataQuality.run_at ?? dataQuality.report?.timestamp ?? '—'}
                  </span>
                </div>
                {(() => {
                  const sh = dataQuality.report?.checks?.find((c) => c.name === 'shareholder_top10')
                    ?.result as
                    | {
                        coverage_rate_pct?: number;
                        missing_stocks_count?: number;
                        a_stock_basic_count?: number;
                        ok?: boolean;
                      }
                    | undefined;
                  if (!sh) {
                    return <p className="text-text-dim">报告中无股东覆盖项</p>;
                  }
                  const low = typeof sh.coverage_rate_pct === 'number' && sh.coverage_rate_pct < 90;
                  return (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-text-secondary">股东数据覆盖率</span>
                        <span
                          className={
                            low ? 'font-semibold text-accent-red' : 'font-medium text-accent-green'
                          }
                        >
                          {sh.coverage_rate_pct != null ? `${sh.coverage_rate_pct}%` : '—'}
                          {low ? ' ⚠' : ''}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-text-secondary">股票表标的数</span>
                        <span className="text-on-surface">{sh.a_stock_basic_count ?? '—'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-text-secondary">缺失股东记录数</span>
                        <span className="text-on-surface">{sh.missing_stocks_count ?? '—'}</span>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="card bg-card-bg/80">
              <h3 className="mb-4 text-lg font-semibold text-on-surface">OpenClaw 进化任务</h3>
              <button
                type="button"
                onClick={handleTriggerEvolution}
                disabled={triggering}
                className="mb-4 rounded bg-primary-fixed px-3 py-1.5 text-sm text-on-warm-fill hover:opacity-90 disabled:opacity-50"
              >
                {triggering ? '触发中…' : '触发策略进化'}
              </button>
              <div className="space-y-2">
                {evolutionTasks.length === 0 ? (
                  <p className="text-sm text-text-dim">暂无进化任务记录</p>
                ) : (
                  evolutionTasks.map((task) => (
                    <div key={task.id} className="flex justify-between items-center text-sm">
                      <span className="max-w-[140px] truncate font-mono text-text-primary" title={task.id}>
                        {task.id.slice(0, 8)}…
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs ${evolutionBadgeClass(task.status)}`}>
                        {task.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </section>
            <section className="card bg-card-bg/80">
              <h3 className="mb-4 text-lg font-semibold text-on-surface">Skill 调用统计</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">总调用次数</span>
                  <span className="font-medium text-on-surface">{skillStats.call_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">最近调用时间</span>
                  <span className="text-text-primary">{skillStats.last_call_time ?? '—'}</span>
                </div>
              </div>
            </section>
          </div>

          <p className="text-sm text-text-dim">{t('systemMonitor.runHint')}</p>
        </>
      )}

      {!status && !error && (
        <p className="text-text-dim">暂无系统状态数据，请先启动 system_core。</p>
      )}
    </div>
  );
}
