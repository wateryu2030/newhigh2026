'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  api,
  type DashboardResponse,
  type DataStatusResponse,
  type HealthDetailPayload,
  type NewsManualRefreshResponse,
  type SystemDataOverviewResponse,
} from '@/api/client';
import { KPICard } from './KPICard';
import { WarningBanner } from './WarningBanner';
import { HealthDetailStrip } from './HealthDetailStrip';
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

/** Gateway 不可用时占位，与后端 get_dashboard stub 口径接近，避免整页仅显示「错误」 */
const DASHBOARD_STUB: DashboardResponse = {
  total_equity: 12_340_000,
  daily_return_pct: 0,
  sharpe_ratio: null,
  max_drawdown_pct: null,
  equity_curve: [10e6, 10.2e6, 10.5e6, 11e6, 11.8e6, 12.34e6],
  top_strategies: [],
  ai_generated_today: null,
  strategies_alive: null,
  strategies_live: null,
  equity_proxy_symbol: null,
  dashboard_notes: ['gateway_unreachable_frontend_stub'],
};

export function Dashboard() {
  const { t } = useLang();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [emotionState, setEmotionState] = useState<string | null>(null);
  const [sniperCount, setSniperCount] = useState<number | null>(null);
  /** 与首屏请求一并拉取；仅在 loading 结束后挂载子组件，避免 SystemDataOverview 重复请求 */
  const [overviewPrefetched, setOverviewPrefetched] = useState<SystemDataOverviewResponse | null>(null);
  const [healthDetail, setHealthDetail] = useState<HealthDetailPayload | null>(null);
  const [healthDetailFailed, setHealthDetailFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  /** 部分接口失败（如 502）时提示，仍展示降级后的首页 */
  const [partialApiWarning, setPartialApiWarning] = useState<string | null>(null);
  const [dashTab, setDashTab] = useState<'overview' | 'news'>('overview');
  const [newsRefreshBusy, setNewsRefreshBusy] = useState(false);
  const [newsRefreshErr, setNewsRefreshErr] = useState<string | null>(null);
  const [newsLastResult, setNewsLastResult] = useState<NewsManualRefreshResponse | null>(null);
  const [sendNewsWebhook, setSendNewsWebhook] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const results = await Promise.allSettled([
        api.dashboard(),
        api.dataStatus(),
        api.marketEmotion().then((r) => r.stage ?? r.state ?? null).catch(() => null),
        api.systemDataOverview().catch(() => null),
        api.healthDetail().catch(() => null),
      ]);
      if (cancelled) return;
      const warn: string[] = [];
      const d = results[0].status === 'fulfilled' ? results[0].value : null;
      if (results[0].status === 'rejected') {
        const r = results[0].reason;
        warn.push(r instanceof Error ? r.message : String(r));
      }
      const s = results[1].status === 'fulfilled' ? results[1].value : null;
      if (results[1].status === 'rejected') {
        const r = results[1].reason;
        warn.push(r instanceof Error ? r.message : String(r));
      }
      const e = results[2].status === 'fulfilled' ? results[2].value : null;
      const ov = results[3].status === 'fulfilled' ? results[3].value : null;
      const hd = results[4].status === 'fulfilled' ? results[4].value : null;

      setData(d ?? DASHBOARD_STUB);
      setDataStatus(s);
      setEmotionState(e);
      setOverviewPrefetched(ov != null && typeof ov === 'object' ? ov : null);
      if (hd && typeof hd === 'object' && 'status' in hd) {
        setHealthDetail(hd as HealthDetailPayload);
        setHealthDetailFailed(false);
      } else {
        setHealthDetail(null);
        setHealthDetailFailed(true);
      }
      const sn =
        ov && typeof ov === 'object' && ov.ok && ov.counts && typeof ov.counts.sniper_candidates === 'number'
          ? ov.counts.sniper_candidates
          : null;
      setSniperCount(sn);
      setPartialApiWarning(warn.length ? warn.join(' · ') : null);
      setError(null);
    })()
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <div className="py-12 text-center text-on-surface-variant">{t('common.loading')}</div>;
  }

  if (error) {
    return (
      <div className="py-12 text-center text-tertiary">
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
      <h1 className="font-headline text-2xl font-bold text-on-surface sm:text-3xl">
        Terminal <span className="text-primary-fixed">Overview</span>
      </h1>

      <div className="mb-2 flex flex-wrap gap-2 border-b border-card-border pb-2">
        <button
          type="button"
          onClick={() => setDashTab('overview')}
          className={`rounded-t-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            dashTab === 'overview' ? 'bg-card-border text-on-surface' : 'bg-transparent text-text-secondary'
          }`}
        >
          {t('dashboard.tabOverview')}
        </button>
        <button
          type="button"
          onClick={() => setDashTab('news')}
          className={`rounded-t-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            dashTab === 'news' ? 'bg-card-border text-on-surface' : 'bg-transparent text-text-secondary'
          }`}
        >
          {t('dashboard.tabNews')}
        </button>
      </div>

      {dashTab === 'overview' ? (
        <>
      {partialApiWarning ? (
        <div className="animate-fadeIn rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          <p className="font-medium text-amber-50">{t('dashboard.partialApiWarning')}</p>
          <p className="mt-1 font-mono text-xs text-amber-200/90">{partialApiWarning}</p>
        </div>
      ) : null}
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

      <div className="animate-fadeIn" style={{ animationDelay: '40ms' }}>
        <HealthDetailStrip data={healthDetail} loadFailed={healthDetailFailed} />
      </div>

      {/* 系统数据概览 */}
      <div className="animate-fadeIn" style={{ animationDelay: '50ms' }}>
        <SystemDataOverview prefetched={overviewPrefetched} />
      </div>

      {/* 数据状态 OK 时的简要信息 */}
      {dataStatus?.ok && (
        <div
          className="animate-fadeIn rounded-2xl border border-card-border bg-card-bg p-4 shadow-card transition-transform duration-200 hover:scale-[1.01] md:p-5"
          style={{ animationDelay: '100ms' }}
        >
          <h2 className="mb-3 font-label text-sm font-medium text-text-secondary">
            {t('dashboard.dataStatus')}
          </h2>
          <div className="flex flex-wrap gap-4 gap-y-2 text-sm md:gap-6">
            <span className="text-on-surface-variant">
              {t('dashboard.stocks')}{' '}
              <strong className="text-on-surface">{dataStatus.stocks.toLocaleString()}</strong>
            </span>
            <span className="text-on-surface-variant">
              {t('dashboard.dailyBars')}{' '}
              <strong className="text-on-surface">{dataStatus.daily_bars.toLocaleString()}</strong>
            </span>
            <span className="text-on-surface-variant">
              {t('dashboard.range')}{' '}
              <strong className="text-on-surface">
                {dataStatus.date_min ?? '—'} ~ {dataStatus.date_max ?? '—'}
              </strong>
            </span>
            {emotionState != null && (
              <span className="text-on-surface-variant">
                {t('dashboard.emotion')}{' '}
                <strong className="text-primary-fixed">{emotionState}</strong>
              </span>
            )}
            {sniperCount != null && (
              <span className="text-on-surface-variant">
                {t('dashboard.sniperCandidates')}{' '}
                <strong className="text-on-surface">{sniperCount}</strong>
              </span>
            )}
            <span className="text-on-surface-variant">
              {t('dashboard.source')} {formatDataSourceLabel(dataStatus.source, t)}
            </span>
            <Link href="/data" className="font-medium text-primary-fixed hover:underline">
              {t('dashboard.detailAndUpdate')} →
            </Link>
          </div>
        </div>
      )}

      {data.dashboard_notes?.length ? (
        <p className="text-xs leading-relaxed text-text-secondary">
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
            className="animate-fadeIn rounded-2xl border border-card-border bg-card-bg p-5 shadow-card transition-transform duration-200 hover:scale-[1.02]"
            style={{ animationDelay: '250ms' }}
          >
            <h2 className="mb-4 text-sm font-medium text-text-secondary">{t('dashboard.aiSignal')}</h2>
            <ul className="space-y-2 text-sm">
              {emotionState != null && (
                <li className="flex justify-between">
                  <span className="text-on-surface-variant">{t('dashboard.emotion')}</span>
                  <span className="text-primary-fixed">{emotionState}</span>
                </li>
              )}
              {sniperCount != null && (
                <li className="flex justify-between">
                  <span className="text-on-surface-variant">{t('dashboard.sniperCandidates')}</span>
                  <Link href="/ai-trading" className="text-primary-fixed hover:underline">
                    {sniperCount}
                  </Link>
                </li>
              )}
            </ul>
          </div>
        )}
        <div
          className="animate-fadeIn rounded-2xl border border-card-border bg-card-bg p-5 shadow-card transition-transform duration-200 hover:scale-[1.02]"
          style={{ animationDelay: '280ms' } as React.CSSProperties}
        >
          <h2 className="mb-4 text-sm font-medium text-text-secondary">{t('dashboard.leaderboard')}</h2>
          <ul className="space-y-2">
            {(data.top_strategies || []).length === 0 ? (
              <li className="text-sm text-text-dim">{t('dashboard.leaderboardEmpty')}</li>
            ) : (
              (data.top_strategies || []).map((s) => (
                <li key={s.id} className="flex justify-between text-sm">
                  <span className="text-on-surface-variant">{s.name}</span>
                  <span className="font-medium text-primary-fixed">
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
          className="animate-fadeIn rounded-2xl border border-card-border bg-card-bg p-5 shadow-card transition-transform duration-200 hover:scale-[1.02]"
          style={{ animationDelay: '310ms' } as React.CSSProperties}
        >
          <h2 className="mb-4 text-sm font-medium text-text-secondary">{t('dashboard.pipeline')}</h2>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span className="text-on-surface-variant">{t('dashboard.generatedToday')}</span>
              <span className="text-on-surface">
                {data.ai_generated_today != null ? data.ai_generated_today : '—'}
              </span>
            </li>
            <li className="flex justify-between">
              <span className="text-on-surface-variant">{t('dashboard.alive')}</span>
              <span className="text-on-surface">
                {data.strategies_alive != null ? data.strategies_alive : '—'}
              </span>
            </li>
            <li className="flex justify-between">
              <span className="text-on-surface-variant">{t('dashboard.live')}</span>
              <span className="text-primary-fixed">
                {data.strategies_live != null ? data.strategies_live : '—'}
              </span>
            </li>
          </ul>
        </div>
      </div>
        </>
      ) : (
        <div className="animate-fadeIn space-y-4 rounded-2xl border border-card-border bg-card-bg p-4 shadow-card md:p-5">
          <h2 className="text-sm font-medium text-text-secondary">{t('dashboard.newsManualTitle')}</h2>
          <p className="text-xs leading-relaxed text-text-dim">{t('dashboard.newsManualHint')}</p>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-on-surface-variant">
            <input
              type="checkbox"
              checked={sendNewsWebhook}
              onChange={(e) => setSendNewsWebhook(e.target.checked)}
              className="rounded border-outline-variant bg-surface-container"
            />
            {t('dashboard.newsManualSendWebhook')}
          </label>
          <button
            type="button"
            disabled={newsRefreshBusy}
            onClick={async () => {
              setNewsRefreshErr(null);
              setNewsRefreshBusy(true);
              try {
                const r = await api.newsManualRefresh({ send_webhook: sendNewsWebhook });
                setNewsLastResult(r);
              } catch (e) {
                setNewsRefreshErr(e instanceof Error ? e.message : String(e));
              } finally {
                setNewsRefreshBusy(false);
              }
            }}
            className="rounded-lg bg-primary-fixed px-4 py-2 text-sm font-medium text-on-warm-fill disabled:opacity-50"
          >
            {newsRefreshBusy ? t('common.loading') : t('dashboard.newsManualRefresh')}
          </button>
          {newsRefreshErr ? <p className="text-sm text-tertiary">{newsRefreshErr}</p> : null}
          {newsLastResult ? (
            <div className="space-y-2 text-sm text-on-surface-variant">
              {newsLastResult.error ? (
                <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-amber-100">
                  <span className="font-medium">{t('dashboard.newsManualFetchError')}</span>
                  <span className="mt-1 block font-mono text-xs text-amber-200/90">{newsLastResult.error}</span>
                </p>
              ) : null}
              <div>
                {t('dashboard.newsManualRssInserted')}:{' '}
                <strong className="text-on-surface">{newsLastResult.rss_inserted}</strong>
              </div>
              <div>
                {t('dashboard.newsManualSummaryLines')}:{' '}
                <strong className="text-on-surface">{newsLastResult.summary_lines}</strong>
              </div>
              <div>
                {t('dashboard.newsManualWebhookSent')}:{' '}
                <strong className="text-on-surface">
                  {newsLastResult.webhook_sent
                    ? t('dashboard.newsManualWebhookYes')
                    : t('dashboard.newsManualWebhookNo')}
                </strong>
                {newsLastResult.webhook_skipped_reason ? (
                  <>
                    {' '}
                    ({t('dashboard.newsManualSkipReason')}: {newsLastResult.webhook_skipped_reason})
                  </>
                ) : null}
              </div>
              <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-card-border p-3 text-xs text-text-code">
                {newsLastResult.summary || '—'}
              </pre>
              <Link href="/news" className="inline-block text-sm font-medium text-primary-fixed hover:underline">
                {t('dashboard.newsManualOpenNews')} →
              </Link>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
