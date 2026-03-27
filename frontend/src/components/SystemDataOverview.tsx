'use client';

import { useEffect, useState, type ReactNode } from 'react';
import {
  api,
  type DailyCoverageResponse,
  type FundflowDrillItem,
  type LimitupDrillItem,
  type LonghubangDrillItem,
  type SniperCandidateItem,
  type SystemDataOverviewResponse,
  type TradeSignalItem,
} from '@/api/client';
import {
  FundflowDrillTable,
  LimitupDrillTable,
  LonghubangDrillTable,
} from '@/components/MarketDrillTables';
import { SniperCandidatesTable } from '@/components/SniperCandidatesTable';
import { StockPenetrationPanel, type StockPenetrationRow } from '@/components/StockPenetrationPanel';
import { TradeSignalsTable } from '@/components/TradeSignalsTable';
import { useLang } from '@/context/LangContext';

function shortNewsTime(s?: string | null): string {
  if (!s) return '—';
  const x = String(s).replace('T', ' ');
  if (x.length >= 16 && x[4] === '-') return x.slice(5, 16);
  return x.length > 16 ? x.slice(0, 16) : x;
}

function useCountSuffix(value: number | string, clickable: boolean): string {
  const { lang } = useLang();
  if (!clickable || typeof value !== 'number') return '';
  return lang === 'en' ? ' rows' : '条';
}

type OverviewDrillKey =
  | 'limitup_pool'
  | 'sniper_candidates'
  | 'trade_signals'
  | 'news_items'
  | 'stock_pool'
  | 'daily_bars'
  | 'longhubang'
  | 'fundflow'
  | 'hotmoney_seats'
  | 'emotion_state';

type DrillPayload =
  | { kind: 'rows'; rows: Record<string, unknown>[]; titleLinksToUrl?: boolean }
  | { kind: 'trade_signals'; rows: TradeSignalItem[] }
  | { kind: 'sniper'; rows: SniperCandidateItem[] }
  | { kind: 'limitup'; rows: LimitupDrillItem[] }
  | { kind: 'longhubang'; rows: LonghubangDrillItem[] }
  | { kind: 'fundflow'; rows: FundflowDrillItem[] }
  | { kind: 'daily'; data: DailyCoverageResponse }
  | { kind: 'text'; text: string };

function formatCell(v: unknown): string {
  if (v == null) return '—';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function isHttpUrl(s: unknown): s is string {
  return typeof s === 'string' && /^https?:\/\//i.test(s.trim());
}

function renderRowsCell(
  k: string,
  row: Record<string, unknown>,
  titleLinksToUrl: boolean,
): ReactNode {
  if (titleLinksToUrl && k === 'title' && isHttpUrl(row.url)) {
    const label = formatCell(row[k]);
    if (label === '—') return label;
    return (
      <a
        href={String(row.url).trim()}
        target="_blank"
        rel="noopener noreferrer"
        className="max-w-[min(28rem,55vw)] truncate text-indigo-400 hover:underline"
        title={label}
      >
        {label}
      </a>
    );
  }
  return formatCell(row[k]);
}

function RowsTable({
  rows,
  emptyMessage,
  titleLinksToUrl = false,
}: {
  rows: Record<string, unknown>[];
  emptyMessage: string;
  titleLinksToUrl?: boolean;
}) {
  if (!rows.length) {
    return <p className="text-sm text-text-secondary">{emptyMessage}</p>;
  }
  const rawKeys = Object.keys(rows[0]).slice(0, 14);
  const keys = titleLinksToUrl ? rawKeys.filter((k) => k !== 'url') : rawKeys;
  return (
    <div className="max-h-[50vh] overflow-x-auto overflow-y-auto rounded-lg border border-card-border">
      <table className="w-full min-w-[480px] text-left text-xs text-text-primary">
        <thead className="sticky top-0 bg-card-bg">
          <tr>
            {keys.map((k) => (
              <th key={k} className="border-b border-card-border p-2 font-medium text-text-secondary">
                {k}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-card-border/40 hover:bg-white/5">
              {keys.map((k) => (
                <td
                  key={k}
                  className="max-w-[220px] truncate p-2 whitespace-nowrap"
                  title={typeof row[k] === 'string' ? row[k] : formatCell(row[k])}
                >
                  {renderRowsCell(k, row, titleLinksToUrl)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DailyCoveragePanel({
  data,
  t,
  emptyMessage,
}: {
  data: DailyCoverageResponse;
  t: (k: string) => string;
  emptyMessage: string;
}) {
  if (!data.ok) {
    return (
      <p className="text-sm text-accent-red">
        {t('common.error')}: {data.error ?? '—'}
      </p>
    );
  }
  const top = data.top_codes ?? [];
  const rows: Record<string, unknown>[] = top.map((x) => ({
    code: x.code,
    bar_count: x.bar_count,
    date_min: x.date_min,
    date_max: x.date_max,
  }));
  return (
    <div className="space-y-3 text-sm text-text-secondary">
      <ul className="list-inside list-disc space-y-1">
        <li>
          {t('systemData.drill.dailyTotal')}: <strong className="text-text-primary">{data.total_rows}</strong>
        </li>
        <li>
          {t('systemData.drill.dailyDistinct')}:{' '}
          <strong className="text-text-primary">{data.distinct_codes}</strong> · {t('systemData.drill.stockPool')}:{' '}
          <strong className="text-text-primary">{data.stock_pool_codes}</strong>
        </li>
        <li>
          {t('systemData.drill.dailyAvg')}:{' '}
          <strong className="text-text-primary">{data.avg_bars_per_code}</strong>
        </li>
        <li>
          {t('data.dateMin')} {data.date_min ?? '—'} → {t('data.dateMax')} {data.date_max ?? '—'}
        </li>
      </ul>
      <p className="text-xs text-amber-200/90">{t('systemData.drill.dailyHint')}</p>
      <p className="text-xs font-medium text-text-secondary">{t('systemData.drill.topByBars')}</p>
      <RowsTable rows={rows} emptyMessage={emptyMessage} />
    </div>
  );
}

interface DataCardProps {
  label: string;
  value: number | string;
  icon?: string;
  onClick?: () => void;
  clickHint: string;
  /** 卡片底部辅文案（如 trade_signals 按策略拆分） */
  footer?: ReactNode;
}

function DataCard({ label, value, icon = '📊', onClick, clickHint, footer }: DataCardProps) {
  const extra = useCountSuffix(value, Boolean(onClick));
  const inner = (
    <>
      <p className="mb-1 text-xs font-medium uppercase tracking-wider text-text-secondary">{label}</p>
      <p className="flex items-baseline gap-2 text-2xl font-bold text-text-primary">
        {icon && <span className="text-lg opacity-70">{icon}</span>}
        <span>{typeof value === 'number' ? value.toLocaleString() : value}</span>
        {extra ? <span className="text-xs text-text-secondary">{extra}</span> : null}
      </p>
      {footer ? <div className="mt-1.5 text-[10px] leading-snug text-text-secondary/85">{footer}</div> : null}
      {onClick && <p className="mt-2 text-[10px] text-text-secondary/80">{clickHint}</p>}
    </>
  );
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="rounded-card w-full border border-card-border bg-card-bg p-4 text-left transition-colors hover:border-accent-red/40 hover:bg-white/[0.03] focus:outline-none focus:ring-1 focus:ring-accent-red/50"
      >
        {inner}
      </button>
    );
  }
  return (
    <div className="rounded-card border border-card-border bg-card-bg p-4 transition-colors">{inner}</div>
  );
}

export function SystemDataOverview({
  prefetched,
}: {
  /** 由父组件与 Dashboard 一并请求时可传入，避免重复打 /system/data-overview */
  prefetched?: SystemDataOverviewResponse | null;
}) {
  const { t, lang } = useLang();
  const [data, setData] = useState<SystemDataOverviewResponse | null>(
    () => (prefetched?.ok ? prefetched : null),
  );
  const [loading, setLoading] = useState(!prefetched?.ok);
  const [error, setError] = useState<string | null>(
    () => (prefetched && !prefetched.ok ? prefetched.error || t('common.error') : null),
  );

  const [drill, setDrill] = useState<{ key: OverviewDrillKey; title: string; emotion?: string } | null>(
    null
  );
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillError, setDrillError] = useState<string | null>(null);
  const [drillPayload, setDrillPayload] = useState<DrillPayload | null>(null);
  const [drillStockDetail, setDrillStockDetail] = useState<StockPenetrationRow | null>(null);

  useEffect(() => {
    if (prefetched?.ok) {
      setData(prefetched);
      setError(null);
      setLoading(false);
      return;
    }
    if (prefetched && !prefetched.ok) {
      setError(prefetched.error || t('common.error'));
      setLoading(false);
      return;
    }
    setLoading(true);
    api
      .systemDataOverview()
      .then((res) => {
        if (res.ok) {
          setData(res);
          setError(null);
        } else {
          setError(res.error || t('common.error'));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : t('common.error')))
      .finally(() => setLoading(false));
  }, [prefetched, t]);

  useEffect(() => {
    if (!drill) return;
    let cancelled = false;
    setDrillLoading(true);
    setDrillError(null);
    setDrillPayload(null);
    (async () => {
      try {
        let payload: DrillPayload | null = null;
        switch (drill.key) {
          case 'limitup_pool': {
            const rows = await api.marketLimitup(300);
            payload = { kind: 'limitup', rows: Array.isArray(rows) ? rows : [] };
            break;
          }
          case 'sniper_candidates': {
            const rows = await api.sniperCandidates(200);
            payload = { kind: 'sniper', rows: Array.isArray(rows) ? rows : [] };
            break;
          }
          case 'trade_signals': {
            const rows = await api.strategySignals(200);
            payload = { kind: 'trade_signals', rows: Array.isArray(rows) ? rows : [] };
            break;
          }
          case 'news_items': {
            const r = await api.news(undefined, 120);
            const news = r.news ?? [];
            payload = {
              kind: 'rows',
              titleLinksToUrl: true,
              rows: news.map((n) => ({
                symbol: n.symbol ?? '',
                title: n.title ?? '',
                time: shortNewsTime(n.publish_time),
                source: n.source ?? n.source_site ?? '',
                url: (n.url ?? '').trim(),
              })) as Record<string, unknown>[],
            };
            break;
          }
          case 'stock_pool': {
            const rows = await api.stocks(500);
            payload = { kind: 'rows', rows: rows as unknown as Record<string, unknown>[] };
            break;
          }
          case 'daily_bars': {
            const d = await api.dataDailyCoverage(300);
            payload = { kind: 'daily', data: d };
            break;
          }
          case 'longhubang': {
            const rows = await api.marketLonghubangRows(300);
            payload = { kind: 'longhubang', rows: Array.isArray(rows) ? rows : [] };
            break;
          }
          case 'fundflow': {
            const rows = await api.marketFundflow(200);
            payload = { kind: 'fundflow', rows: Array.isArray(rows) ? rows : [] };
            break;
          }
          case 'hotmoney_seats': {
            const rows = await api.marketHotmoney(120);
            payload = { kind: 'rows', rows: rows as unknown as Record<string, unknown>[] };
            break;
          }
          case 'emotion_state': {
            payload = {
              kind: 'text',
              text: `${t('systemData.drill.emotionExplain')}\n\n${t('systemData.drill.emotionCurrent')}: ${drill.emotion ?? '—'}`,
            };
            break;
          }
          default:
            payload = { kind: 'text', text: t('systemData.drill.unsupported') };
        }
        if (!cancelled && payload) setDrillPayload(payload);
      } catch (e) {
        if (!cancelled) setDrillError(e instanceof Error ? e.message : t('common.error'));
      } finally {
        if (!cancelled) setDrillLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [drill, t]);

  const openDrill = (key: OverviewDrillKey, title: string, emotion?: string) => {
    setDrillStockDetail(null);
    setDrill({ key, title, emotion });
  };

  const closeDrill = () => {
    setDrill(null);
    setDrillPayload(null);
    setDrillError(null);
    setDrillStockDetail(null);
  };

  if (loading) {
    return (
      <div className="rounded-card border border-card-border bg-card-bg space-y-4 p-4">
        <h2 className="text-sm font-medium text-text-secondary">📊 {t('data.systemOverview')}</h2>
        <div className="py-4 text-center text-text-secondary">{t('common.loading')}</div>
      </div>
    );
  }

  if (error) {
    const isDbConfig =
      /different configuration|Can't open a connection to same database file/i.test(error);
    return (
      <div className="rounded-card border border-card-border bg-card-bg p-4">
        <h2 className="text-sm font-medium text-accent-red">📊 {t('data.systemOverview')}</h2>
        <p className="mt-2 text-xs text-text-secondary">
          {t('common.error')}: {error}
        </p>
        {isDbConfig ? (
          <p className="mt-2 text-xs text-amber-200/90">
            此为 DuckDB 连接模式冲突（同一进程内混用了只读/读写）。请<strong>重启 Gateway</strong> 以加载最新后端代码。
            若仍出现，请确认 <code className="text-[10px]">QUANT_SYSTEM_DUCKDB_PATH</code> 与{' '}
            <code className="text-[10px]">lib.database</code> 指向同一库文件。
          </p>
        ) : (
          <p className="mt-1 text-xs text-text-secondary">
            {t('common.dataNotReady')}，请运行：
            <code
              className="mt-2 block rounded p-2 text-[10px] text-accent-red"
              style={{ backgroundColor: '#0A0C10' }}
            >
              python scripts/ensure_market_data.py
            </code>
            <span className="mt-1 block">或：python scripts/ensure_ashare_data_completeness.py</span>
          </p>
        )}
      </div>
    );
  }

  const defaultCounts: SystemDataOverviewResponse['counts'] = {
    limitup_pool: 0,
    sniper_candidates: 0,
    trade_signals: 0,
    trade_signals_by_strategy: {},
    news_items: 0,
    stock_pool: 0,
    daily_bars: 0,
    longhubang: 0,
    fundflow: 0,
    emotion_state: null,
    hotmoney_seats: 0,
  };
  const counts = data?.counts ?? defaultCounts;

  const tradeSignalsByStrategyLine = (() => {
    const by = counts.trade_signals_by_strategy;
    if (!by || typeof by !== 'object') return null;
    const entries = Object.entries(by).sort((a, b) => b[1] - a[1]);
    if (!entries.length) return null;
    return entries.map(([k, n]) => `${k}: ${n}`).join(' · ');
  })();
  const emotionStr =
    counts.emotion_state != null && counts.emotion_state !== ''
      ? String(counts.emotion_state)
      : '—';

  return (
    <div className="rounded-card border border-card-border bg-card-bg space-y-4 p-4 transition-transform duration-200 hover:scale-[1.01]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-medium text-text-secondary">📊 {t('data.systemOverview')}</h2>
        <div className="flex flex-col items-start gap-1 text-[11px] text-text-secondary sm:items-end">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-accent-red/80" />
            {t('systemData.loadTime')}:{' '}
            {new Date().toLocaleTimeString(lang === 'en' ? 'en-US' : 'zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          <span className="max-w-md text-[10px] leading-snug opacity-90">{t('systemData.drill.banner')}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <DataCard
          label={t('systemData.overview.limitupPool')}
          value={counts.limitup_pool ?? 0}
          icon="🔥"
          clickHint={t('systemData.drill.click')}
          onClick={() => openDrill('limitup_pool', t('systemData.overview.limitupPool'))}
        />
        <DataCard
          label={t('systemData.overview.sniperCandidates')}
          value={counts.sniper_candidates ?? 0}
          icon="🎯"
          clickHint={t('systemData.drill.click')}
          onClick={() => openDrill('sniper_candidates', t('systemData.overview.sniperCandidates'))}
        />
        <DataCard
          label={t('systemData.overview.tradeSignals')}
          value={counts.trade_signals ?? 0}
          icon="📈"
          clickHint={t('systemData.drill.click')}
          onClick={() => openDrill('trade_signals', t('systemData.overview.tradeSignals'))}
          footer={
            tradeSignalsByStrategyLine ? (
              <span title="strategy_id 维度（含 shareholder_chip / ai_fusion / market_agg 等）">
                {tradeSignalsByStrategyLine}
              </span>
            ) : undefined
          }
        />
        <DataCard
          label={t('systemData.overview.newsItems')}
          value={counts.news_items ?? 0}
          icon="📰"
          clickHint={t('systemData.drill.click')}
          onClick={() => openDrill('news_items', t('systemData.overview.newsItems'))}
        />
      </div>

      {counts.stock_pool !== undefined && (
        <div className="mt-2 grid grid-cols-2 gap-4 border-t border-card-border/50 pt-3 sm:grid-cols-3 lg:grid-cols-6">
          <DataCard
            label={t('systemData.row2.stockPool')}
            value={counts.stock_pool ?? 0}
            icon="📋"
            clickHint={t('systemData.drill.click')}
            onClick={() => openDrill('stock_pool', t('systemData.row2.stockPool'))}
          />
          <DataCard
            label={t('systemData.row2.dailyK')}
            value={counts.daily_bars ?? 0}
            icon="📅"
            clickHint={t('systemData.drill.click')}
            onClick={() => openDrill('daily_bars', t('systemData.row2.dailyK'))}
          />
          <DataCard
            label={t('systemData.row2.longhubang')}
            value={counts.longhubang ?? 0}
            icon="🏆"
            clickHint={t('systemData.drill.click')}
            onClick={() => openDrill('longhubang', t('systemData.row2.longhubang'))}
          />
          <DataCard
            label={t('systemData.row2.fundflow')}
            value={counts.fundflow ?? 0}
            icon="💧"
            clickHint={t('systemData.drill.click')}
            onClick={() => openDrill('fundflow', t('systemData.row2.fundflow'))}
          />
          <DataCard
            label={t('systemData.row2.hotmoney')}
            value={counts.hotmoney_seats ?? 0}
            icon="👨‍💼"
            clickHint={t('systemData.drill.click')}
            onClick={() =>
              openDrill(
                'hotmoney_seats',
                `${t('systemData.row2.hotmoney')}（${t('systemData.drill.hotmoneyNote')}）`
              )
            }
          />
          <DataCard
            label={t('systemData.row2.emotion')}
            value={emotionStr}
            icon="📉"
            clickHint={t('systemData.drill.click')}
            onClick={() => openDrill('emotion_state', t('systemData.row2.emotion'), emotionStr)}
          />
        </div>
      )}

      {counts.news_items !== undefined && counts.news_items > 15000 && (
        <div className="mt-2 rounded-xl bg-accent-red/10 p-3">
          <p className="flex items-center gap-2 text-xs font-medium text-accent-red">
            <span>✅</span>
            <span>
              📰 新闻数据充足（{counts.news_items.toLocaleString()} 条）， ✅ 涨停池活跃（
              {counts.limitup_pool} 条）， ✅ 狙击候选就绪（{counts.sniper_candidates} 条）， ✅
              交易信号生成（{counts.trade_signals} 条）
            </span>
          </p>
        </div>
      )}

      {/* 下钻弹层 */}
      {drill && (
        <div
          className="fixed inset-0 z-[100] flex items-end justify-center bg-black/70 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-labelledby="drill-title"
          onClick={closeDrill}
        >
          <div
            className="max-h-[85vh] w-full max-w-5xl overflow-hidden rounded-2xl border border-card-border bg-[#14171C] shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-card-border px-4 py-3">
              <div>
                <h3 id="drill-title" className="text-base font-semibold text-text-primary">
                  {drill.title}
                </h3>
                <p className="mt-1 text-[11px] text-text-secondary">{t('systemData.drill.modalFoot')}</p>
              </div>
              <button
                type="button"
                onClick={closeDrill}
                className="rounded-lg px-3 py-1 text-sm text-text-secondary hover:bg-white/10"
              >
                ✕
              </button>
            </div>
            <div className="max-h-[calc(85vh-5rem)] overflow-y-auto p-4">
              {drillLoading && <p className="text-sm text-text-secondary">{t('common.loading')}</p>}
              {drillError && <p className="text-sm text-accent-red">{drillError}</p>}
              {!drillLoading && !drillError && drillPayload?.kind === 'trade_signals' && (
                <>
                  {drillStockDetail ? (
                    <StockPenetrationPanel row={drillStockDetail} onBack={() => setDrillStockDetail(null)} />
                  ) : (
                    <TradeSignalsTable
                      rows={drillPayload.rows}
                      dense
                      onRowClick={(r) =>
                        setDrillStockDetail({
                          code: r.code,
                          stock_name: r.stock_name,
                          last_price: r.last_price,
                          change_pct: r.change_pct,
                        })
                      }
                    />
                  )}
                </>
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'sniper' && (
                <>
                  {drillStockDetail ? (
                    <StockPenetrationPanel row={drillStockDetail} onBack={() => setDrillStockDetail(null)} />
                  ) : (
                    <SniperCandidatesTable
                      rows={drillPayload.rows}
                      dense
                      onRowClick={(r) =>
                        setDrillStockDetail({
                          code: r.code,
                          stock_name: r.stock_name,
                          last_price: r.last_price,
                          change_pct: r.change_pct,
                        })
                      }
                    />
                  )}
                </>
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'limitup' && (
                <>
                  {drillStockDetail ? (
                    <StockPenetrationPanel row={drillStockDetail} onBack={() => setDrillStockDetail(null)} />
                  ) : (
                    <LimitupDrillTable
                      rows={drillPayload.rows}
                      dense
                      onRowClick={(r) =>
                        setDrillStockDetail({
                          code: r.code,
                          stock_name: r.stock_name,
                          last_price: r.last_price,
                          change_pct: r.change_pct,
                        })
                      }
                    />
                  )}
                </>
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'longhubang' && (
                <>
                  {drillStockDetail ? (
                    <StockPenetrationPanel row={drillStockDetail} onBack={() => setDrillStockDetail(null)} />
                  ) : (
                    <LonghubangDrillTable
                      rows={drillPayload.rows}
                      dense
                      onRowClick={(r) =>
                        setDrillStockDetail({
                          code: r.code,
                          stock_name: r.stock_name,
                          last_price: r.last_price,
                          change_pct: r.change_pct,
                        })
                      }
                    />
                  )}
                </>
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'fundflow' && (
                <>
                  {drillStockDetail ? (
                    <StockPenetrationPanel row={drillStockDetail} onBack={() => setDrillStockDetail(null)} />
                  ) : (
                    <FundflowDrillTable
                      rows={drillPayload.rows}
                      dense
                      onRowClick={(r) =>
                        setDrillStockDetail({
                          code: r.code,
                          stock_name: r.stock_name,
                          last_price: r.last_price,
                          change_pct: r.change_pct,
                        })
                      }
                    />
                  )}
                </>
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'rows' && (
                <RowsTable
                  rows={drillPayload.rows}
                  emptyMessage={t('systemData.drill.tableEmpty')}
                  titleLinksToUrl={drillPayload.titleLinksToUrl}
                />
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'daily' && (
                <DailyCoveragePanel
                  data={drillPayload.data}
                  t={t}
                  emptyMessage={t('systemData.drill.tableEmpty')}
                />
              )}
              {!drillLoading && !drillError && drillPayload?.kind === 'text' && (
                <pre className="whitespace-pre-wrap text-sm text-text-secondary">{drillPayload.text}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
