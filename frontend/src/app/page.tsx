'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, type DashboardResponse, type DataStatusResponse } from '@/api/client';
import { StatCard } from '@/components/StatCard';
import { EquityCurve } from '@/components/EquityCurve';
import { SystemDataOverview } from '@/components/SystemDataOverview';
import { useLang } from '@/context/LangContext';

export default function DashboardPage() {
  const { t } = useLang();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [emotionState, setEmotionState] = useState<string | null>(null);
  const [sniperCount, setSniperCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.dashboard(),
      api.dataStatus(),
      api.marketEmotion().then((r) => r.stage ?? r.state ?? null).catch(() => null),
      api.sniperCandidates(10).then((r) => (Array.isArray(r) ? r.length : 0)).catch(() => 0),
    ])
      .then(([d, s, e, sn]) => {
        setData(d);
        setDataStatus(s);
        setEmotionState(e);
        setSniperCount(sn);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-slate-400">{t('common.loading')}</div>;
  if (error) return <div className="py-12 text-center text-red-400">{t('common.error')}: {error}</div>;
  if (!data) return null;

  const formatMoney = (n: number) => (n >= 1e6 ? `¥${(n / 1e6).toFixed(1)}M` : `¥${n.toLocaleString()}`);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white sm:text-3xl">{t('dashboard.title')}</h1>

      {/* 系统数据概览 */}
      <SystemDataOverview />

      {dataStatus && !dataStatus.ok && (
        <div className="card border-amber-500/30 bg-slate-800/80">
          <h2 className="mb-2 text-sm font-medium text-amber-200">{t('dashboard.dataIncomplete')}</h2>
          <p className="text-sm text-slate-400">{t('dashboard.dataIncompleteHint')}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Link href="/data" className="text-indigo-400 hover:underline">{t('dashboard.detailAndUpdate')} →</Link>
            <span className="text-slate-500">|</span>
            <span className="text-slate-500 text-xs">{t('dashboard.scriptEnsure')}</span>
          </div>
        </div>
      )}

      {dataStatus && dataStatus.ok && (
        <div className="card border-emerald-500/30 bg-slate-800/80">
          <h2 className="mb-3 text-sm font-medium text-slate-400">{t('dashboard.dataStatus')}</h2>
          <div className="flex flex-wrap gap-6 text-sm">
            <span className="text-slate-300">{t('dashboard.stocks')} <strong className="text-white">{dataStatus.stocks.toLocaleString()}</strong></span>
            <span className="text-slate-300">{t('dashboard.dailyBars')} <strong className="text-white">{dataStatus.daily_bars.toLocaleString()}</strong></span>
            <span className="text-slate-300">{t('dashboard.range')} <strong className="text-white">{dataStatus.date_min ?? '—'} ~ {dataStatus.date_max ?? '—'}</strong></span>
            {emotionState != null && (
              <span className="text-slate-300">{t('dashboard.emotion')} <strong className="text-amber-300">{emotionState}</strong></span>
            )}
            {sniperCount != null && sniperCount > 0 && (
              <span className="text-slate-300">{t('dashboard.sniperCandidates')} <strong className="text-white">{sniperCount}</strong></span>
            )}
            <span className="text-slate-500">{t('dashboard.source')} {dataStatus.source ?? '—'}</span>
            <Link href="/data" className="text-indigo-400 hover:underline">{t('dashboard.detailAndUpdate')} →</Link>
          </div>
        </div>
      )}

      <div className="grid-dashboard">
        <StatCard title={t('dashboard.totalAum')} value={formatMoney(data.total_equity)} />
        <StatCard title={t('dashboard.today')} value={`${data.daily_return_pct >= 0 ? '+' : ''}${data.daily_return_pct}%`} positive={data.daily_return_pct >= 0} />
        <StatCard title={t('dashboard.sharpe')} value={data.sharpe_ratio?.toFixed(1) ?? '—'} />
        <StatCard title={t('dashboard.maxDrawdown')} value={`${data.max_drawdown_pct}%`} />
      </div>

      <EquityCurve data={data.equity_curve} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {(emotionState != null || (sniperCount != null && sniperCount > 0)) && (
          <div className="card">
            <h2 className="mb-4 text-sm font-medium text-slate-400">{t('dashboard.aiSignal')}</h2>
            <ul className="space-y-2 text-sm">
              {emotionState != null && (
                <li className="flex justify-between">
                  <span className="text-slate-400">{t('dashboard.emotion')}</span>
                  <span className="text-amber-300">{emotionState}</span>
                </li>
              )}
              {sniperCount != null && sniperCount > 0 && (
                <li className="flex justify-between">
                  <span className="text-slate-400">{t('dashboard.sniperCandidates')}</span>
                  <Link href="/ai-trading" className="text-indigo-400 hover:underline">{sniperCount}</Link>
                </li>
              )}
            </ul>
          </div>
        )}
        <div className="card">
          <h2 className="mb-4 text-sm font-medium text-slate-400">{t('dashboard.leaderboard')}</h2>
          <ul className="space-y-2">
            {(data.top_strategies || []).map((s) => (
              <li key={s.id} className="flex justify-between text-sm">
                <span className="text-slate-300">{s.name}</span>
                <span className="font-medium text-emerald-400">+{s.return_pct}%</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2 className="mb-4 text-sm font-medium text-slate-400">{t('dashboard.pipeline')}</h2>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between"><span className="text-slate-400">{t('dashboard.generatedToday')}</span><span className="text-white">{data.ai_generated_today}</span></li>
            <li className="flex justify-between"><span className="text-slate-400">{t('dashboard.alive')}</span><span className="text-white">{data.strategies_alive}</span></li>
            <li className="flex justify-between"><span className="text-slate-400">{t('dashboard.live')}</span><span className="text-emerald-400">{data.strategies_live}</span></li>
          </ul>
        </div>
      </div>
    </div>
  );
}
