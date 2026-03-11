'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, type SystemStatusResponse, type EvolutionTaskItem } from '@/api/client';
import { useLang } from '@/context/LangContext';

function statusLabel(s: 'running' | 'error' | 'idle', t: (k: string) => string) {
  if (s === 'running') return t('systemMonitor.statusRunning');
  if (s === 'error') return t('systemMonitor.statusError');
  return t('systemMonitor.statusIdle');
}

function statusColor(s: 'running' | 'error' | 'idle') {
  if (s === 'running') return 'text-emerald-400';
  if (s === 'error') return 'text-amber-400';
  return 'text-slate-500';
}

function evolutionBadgeClass(status: string) {
  const s = (status || '').toLowerCase();
  if (s === 'success') return 'bg-emerald-500/80 text-white';
  if (s === 'failed') return 'bg-red-500/80 text-white';
  if (s === 'running') return 'bg-amber-500/80 text-white';
  return 'bg-slate-500/80 text-white';
}

export default function SystemMonitorPage() {
  const { t } = useLang();
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [evolutionTasks, setEvolutionTasks] = useState<EvolutionTaskItem[]>([]);
  const [skillStats, setSkillStats] = useState<{ call_count: number; last_call_time: string | null }>({ call_count: 0, last_call_time: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.systemStatus(20),
      api.getEvolutionTasks(5).then((r) => r.tasks || []),
      api.getSkillStats().catch(() => ({ call_count: 0, last_call_time: null })),
    ])
      .then(([s, tasks, stats]) => {
        setStatus(s);
        setEvolutionTasks(tasks);
        setSkillStats(stats);
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
        <h1 className="text-2xl font-bold text-white">{t('systemMonitor.title')}</h1>
        <p className="text-slate-500">{t('common.loading')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('systemMonitor.title')}</h1>
          <p className="text-slate-400 text-sm mt-1">{t('systemMonitor.hint')}</p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="px-3 py-1.5 rounded bg-slate-600 hover:bg-slate-500 disabled:opacity-50 text-white text-sm"
        >
          刷新
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm p-4">
          <p className="font-medium">{t('common.error')}: {error}</p>
          <p className="mt-2 text-slate-400">{t('systemMonitor.runHint')}</p>
        </div>
      )}

      {status && (
        <>
          <section className="card">
            <h2 className="text-lg font-semibold text-white mb-4">当前状态</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-slate-500 text-sm">{t('systemMonitor.dataPipeline')}</p>
                <p className={`font-medium ${statusColor(status.data_pipeline)}`}>
                  {statusLabel(status.data_pipeline, t)}
                </p>
              </div>
              <div>
                <p className="text-slate-500 text-sm">{t('systemMonitor.scanner')}</p>
                <p className={`font-medium ${statusColor(status.scanner)}`}>
                  {statusLabel(status.scanner, t)}
                </p>
              </div>
              <div>
                <p className="text-slate-500 text-sm">{t('systemMonitor.aiModels')}</p>
                <p className={`font-medium ${statusColor(status.ai_models)}`}>
                  {statusLabel(status.ai_models, t)}
                </p>
              </div>
              <div>
                <p className="text-slate-500 text-sm">{t('systemMonitor.strategyEngine')}</p>
                <p className={`font-medium ${statusColor(status.strategy_engine)}`}>
                  {statusLabel(status.strategy_engine, t)}
                </p>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-slate-700">
              <p className="text-slate-500 text-sm">{t('systemMonitor.lastUpdate')}</p>
              <p className="text-white font-mono text-sm">
                {status.last_update ?? '—'}
              </p>
            </div>
          </section>

          {status.history?.length > 0 && (
            <section className="card">
              <h2 className="text-lg font-semibold text-white mb-4">{t('systemMonitor.history')}</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700">
                      <th className="text-left py-2 pr-4">data_status</th>
                      <th className="text-left py-2 pr-4">scanner_status</th>
                      <th className="text-left py-2 pr-4">ai_status</th>
                      <th className="text-left py-2 pr-4">strategy_status</th>
                      <th className="text-left py-2">snapshot_time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.history.slice(0, 15).map((row, i) => (
                      <tr key={i} className="border-b border-slate-800">
                        <td className="py-2 pr-4 text-slate-300">{row.data_status ?? '—'}</td>
                        <td className="py-2 pr-4 text-slate-300">{row.scanner_status ?? '—'}</td>
                        <td className="py-2 pr-4 text-slate-300">{row.ai_status ?? '—'}</td>
                        <td className="py-2 pr-4 text-slate-300">{row.strategy_status ?? '—'}</td>
                        <td className="py-2 text-slate-500 font-mono">{row.snapshot_time ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="card bg-slate-800/80">
              <h3 className="text-lg font-semibold text-white mb-4">OpenClaw 进化任务</h3>
              <button
                type="button"
                onClick={handleTriggerEvolution}
                disabled={triggering}
                className="mb-4 px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm"
              >
                {triggering ? '触发中…' : '触发策略进化'}
              </button>
              <div className="space-y-2">
                {evolutionTasks.length === 0 ? (
                  <p className="text-slate-500 text-sm">暂无进化任务记录</p>
                ) : (
                  evolutionTasks.map((task) => (
                    <div key={task.id} className="flex justify-between items-center text-sm">
                      <span className="text-slate-300 font-mono truncate max-w-[140px]" title={task.id}>
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
            <section className="card bg-slate-800/80">
              <h3 className="text-lg font-semibold text-white mb-4">Skill 调用统计</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">总调用次数</span>
                  <span className="text-white font-medium">{skillStats.call_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">最近调用时间</span>
                  <span className="text-slate-300">{skillStats.last_call_time ?? '—'}</span>
                </div>
              </div>
            </section>
          </div>

          <p className="text-slate-500 text-sm">{t('systemMonitor.runHint')}</p>
        </>
      )}

      {!status && !error && (
        <p className="text-slate-500">暂无系统状态数据，请先启动 system_core。</p>
      )}
    </div>
  );
}
