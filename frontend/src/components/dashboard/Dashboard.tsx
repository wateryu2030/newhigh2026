'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  api,
  type DashboardResponse,
  type DataStatusResponse,
  type SystemDataOverviewResponse,
} from '@/api/client';
import { KPICard } from './KPICard';
import { WarningBanner } from './WarningBanner';
import { SystemDataOverview } from '../SystemDataOverview';
import { EquityCurve } from '../EquityCurve';
import { useLang } from '@/context/LangContext';

function formatDataSourceLabel(source: string | null, t: (k: string) => string): string {
  if (source === 'duckdb_pipeline') return t('data.source.pipeline');
  if (source === 'duckdb_astock') return t('data.source.astock');
  if (source === 'duckdb') return 'DuckDB';
  return source ?? '—';
}

/** 取权益曲线末段作 KPI 迷你图（百万单位） */
function equitySparklineFromCurve(equity: number[], maxPts = 14): number[] {
  if (!equity.length) return [];
  const slice = equity.slice(-maxPts);
  return slice.map((x) => x / 1e6);
}

export function Dashboard() {
  const { t } = useLang();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [emotionState, setEmotionState] = useState<string | null>(null);
  const [sniperCount, setSniperCount] = useState<number | null>(null);
  /** 与首屏请求一并拉取；仅在 loading 结束后挂载子组件，避免 SystemDataOverview 重复请求 */
  const [overviewPrefetched, setOverviewPrefetched] = useState<SystemDataOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.dashboard(),
      api.dataStatus(),
      api.marketEmotion().then((r) => r.stage ?? r.state ?? null).catch(() => null),
      api.systemDataOverview().catch(() => null),
    ])
      .then(([d, s, e, ov]) => {
        setData(d);
        setDataStatus(s);
        setEmotionState(e);
        setOverviewPrefetched(ov != null && typeof ov === 'object' ? ov : null);
        const sn =
          ov && typeof ov === 'object' && ov.ok && ov.counts && typeof ov.counts.sniper_candidates === 'number'
            ? ov.counts.sniper_candidates
            : null;
        setSniperCount(sn);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-12 text-center" style={{ color: '#A9ABB3' }}>
        {t('common.loading')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center" style={{ color: '#FF7439' }}>
        {t('common.error')}: {error}
      </div>
    );
  }

  if (!data) return null;

  const formatMoney = (n: number) =>
    n >= 1e6 ? `¥${(n / 1e6).toFixed(1)}M` : `¥${n.toLocaleString()}`;

  const equityArr = data.equity_curve ?? [];
  const sparkAum = equitySparklineFromCurve(equityArr);
  const aumDayDeltaPct =
    equityArr.length >= 2
      ? ((equityArr[equityArr.length - 1] - equityArr[equityArr.length - 2]) /
          equityArr[equityArr.length - 2]) *
        100
      : data.daily_return_pct;

  return (
    <div className="max-w-[1200px] space-y-4">
      <h1
        className="text-2xl font-bold sm:text-3xl"
        style={{ color: '#ECEDF6', fontFamily: 'Manrope' }}
      >
        Terminal <span style={{ color: '#FF3B30' }}>Overview</span>
      </h1>

      {/* 数据完整性提醒 - 占满宽度 */}
      {dataStatus && !dataStatus.ok && (
        <div className="animate-fadeIn">
          <WarningBanner
            title={t('dashboard.dataIncomplete')}
            description={t('dashboard.dataIncompleteHint')}
            hint={t('dashboard.scriptEnsure')}
            linkLabel={`${t('dashboard.detailAndUpdate')} →`}
          />
        </div>
      )}

      {/* 系统数据概览 */}
      <div className="animate-fadeIn" style={{ animationDelay: '50ms' }}>
        <SystemDataOverview prefetched={overviewPrefetched} />
      </div>

      {/* 数据状态 OK 时的简要信息 */}
      {dataStatus?.ok && (
        <div
          className="animate-fadeIn rounded-2xl border p-4 transition-transform duration-200 hover:scale-[1.01] md:p-5"
          style={{
            backgroundColor: '#14171C',
            borderColor: '#2A2E36',
            animationDelay: '100ms',
          }}
        >
          <h2
            className="mb-3 text-sm font-medium"
            style={{ color: '#94A3B8', fontFamily: 'Space Grotesk' }}
          >
            {t('dashboard.dataStatus')}
          </h2>
          <div className="flex flex-wrap gap-4 gap-y-2 text-sm md:gap-6">
            <span style={{ color: '#A9ABB3' }}>
              {t('dashboard.stocks')}{' '}
              <strong style={{ color: '#ECEDF6' }}>{dataStatus.stocks.toLocaleString()}</strong>
            </span>
            <span style={{ color: '#A9ABB3' }}>
              {t('dashboard.dailyBars')}{' '}
              <strong style={{ color: '#ECEDF6' }}>{dataStatus.daily_bars.toLocaleString()}</strong>
            </span>
            <span style={{ color: '#A9ABB3' }}>
              {t('dashboard.range')}{' '}
              <strong style={{ color: '#ECEDF6' }}>
                {dataStatus.date_min ?? '—'} ~ {dataStatus.date_max ?? '—'}
              </strong>
            </span>
            {emotionState != null && (
              <span style={{ color: '#A9ABB3' }}>
                {t('dashboard.emotion')}{' '}
                <strong style={{ color: '#FF3B30' }}>{emotionState}</strong>
              </span>
            )}
            {sniperCount != null && (
              <span style={{ color: '#A9ABB3' }}>
                {t('dashboard.sniperCandidates')}{' '}
                <strong style={{ color: '#ECEDF6' }}>{sniperCount}</strong>
              </span>
            )}
            <span style={{ color: '#A9ABB3' }}>
              {t('dashboard.source')} {formatDataSourceLabel(dataStatus.source, t)}
            </span>
            <Link href="/data" className="font-medium hover:underline" style={{ color: '#FF3B30' }}>
              {t('dashboard.detailAndUpdate')} →
            </Link>
          </div>
        </div>
      )}

      {data.dashboard_notes?.length ? (
        <p className="text-xs leading-relaxed" style={{ color: '#94A3B8' }}>
          {t('dashboard.dataBindingHint')}
          {data.equity_proxy_symbol ? (
            <>
              {' '}
              {t('dashboard.equityProxySymbol')}
              <code className="mx-1 rounded bg-white/10 px-1">{data.equity_proxy_symbol}</code>
            </>
          ) : null}
        </p>
      ) : null}

      {/* 核心指标 KPI - grid-cols-2 on md */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="animate-fadeIn">
          <KPICard
            title={t('dashboard.totalAum')}
            value={formatMoney(data.total_equity)}
            change={aumDayDeltaPct}
            sparklineData={sparkAum.length > 1 ? sparkAum : undefined}
          />
        </div>
        <div className="animate-fadeIn" style={{ animationDelay: '30ms' } as React.CSSProperties}>
          <KPICard
            title={t('dashboard.today')}
            value={`${data.daily_return_pct >= 0 ? '+' : ''}${data.daily_return_pct}%`}
            positive={data.daily_return_pct >= 0}
          />
        </div>
        <div className="animate-fadeIn" style={{ animationDelay: '60ms' } as React.CSSProperties}>
          <KPICard
            title={t('dashboard.sharpe')}
            value={data.sharpe_ratio != null ? data.sharpe_ratio.toFixed(2) : '—'}
            sub={t('dashboard.sharpeHint')}
          />
        </div>
        <div className="animate-fadeIn" style={{ animationDelay: '90ms' } as React.CSSProperties}>
          <KPICard
            title={t('dashboard.maxDrawdown')}
            value={data.max_drawdown_pct != null ? `${data.max_drawdown_pct}%` : '—'}
            positive={false}
            sub={t('dashboard.drawdownHint')}
          />
        </div>
      </div>

      {/* 权益曲线 */}
      <div className="animate-fadeIn" style={{ animationDelay: '200ms' } as React.CSSProperties}>
        <div className="transition-transform duration-200 hover:scale-[1.01]">
          <EquityCurve data={data.equity_curve} />
        </div>
      </div>

      {/* 底部卡片：AI 信号 / Leaderboard / Pipeline */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(emotionState != null || sniperCount != null) && (
          <div
            className="animate-fadeIn rounded-2xl border p-5 transition-transform duration-200 hover:scale-[1.02]"
            style={{
              backgroundColor: '#14171C',
              borderColor: '#2A2E36',
              animationDelay: '250ms',
            }}
          >
            <h2 className="mb-4 text-sm font-medium" style={{ color: '#94A3B8' }}>
              {t('dashboard.aiSignal')}
            </h2>
            <ul className="space-y-2 text-sm">
              {emotionState != null && (
                <li className="flex justify-between">
                  <span style={{ color: '#A9ABB3' }}>{t('dashboard.emotion')}</span>
                  <span style={{ color: '#FF3B30' }}>{emotionState}</span>
                </li>
              )}
              {sniperCount != null && (
                <li className="flex justify-between">
                  <span style={{ color: '#A9ABB3' }}>{t('dashboard.sniperCandidates')}</span>
                  <Link href="/ai-trading" className="hover:underline" style={{ color: '#FF3B30' }}>
                    {sniperCount}
                  </Link>
                </li>
              )}
            </ul>
          </div>
        )}
        <div
          className="animate-fadeIn rounded-2xl border p-5 transition-transform duration-200 hover:scale-[1.02]"
          style={{
            backgroundColor: '#14171C',
            borderColor: '#2A2E36',
            animationDelay: '280ms',
          } as React.CSSProperties}
        >
          <h2 className="mb-4 text-sm font-medium" style={{ color: '#94A3B8' }}>
            {t('dashboard.leaderboard')}
          </h2>
          <ul className="space-y-2">
            {(data.top_strategies || []).length === 0 ? (
              <li className="text-sm" style={{ color: '#64748B' }}>
                {t('dashboard.leaderboardEmpty')}
              </li>
            ) : (
              (data.top_strategies || []).map((s) => (
                <li key={s.id} className="flex justify-between text-sm">
                  <span style={{ color: '#A9ABB3' }}>{s.name}</span>
                  <span className="font-medium" style={{ color: '#FF3B30' }}>
                    {s.return_pct != null && !Number.isNaN(s.return_pct)
                      ? `${s.return_pct >= 0 ? '+' : ''}${Number(s.return_pct).toFixed(2)}%`
                      : '—'}
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
        <div
          className="animate-fadeIn rounded-2xl border p-5 transition-transform duration-200 hover:scale-[1.02]"
          style={{
            backgroundColor: '#14171C',
            borderColor: '#2A2E36',
            animationDelay: '310ms',
          } as React.CSSProperties}
        >
          <h2 className="mb-4 text-sm font-medium" style={{ color: '#94A3B8' }}>
            {t('dashboard.pipeline')}
          </h2>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span style={{ color: '#A9ABB3' }}>{t('dashboard.generatedToday')}</span>
              <span style={{ color: '#ECEDF6' }}>
                {data.ai_generated_today != null ? data.ai_generated_today : '—'}
              </span>
            </li>
            <li className="flex justify-between">
              <span style={{ color: '#A9ABB3' }}>{t('dashboard.alive')}</span>
              <span style={{ color: '#ECEDF6' }}>
                {data.strategies_alive != null ? data.strategies_alive : '—'}
              </span>
            </li>
            <li className="flex justify-between">
              <span style={{ color: '#A9ABB3' }}>{t('dashboard.live')}</span>
              <span style={{ color: '#FF3B30' }}>
                {data.strategies_live != null ? data.strategies_live : '—'}
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
