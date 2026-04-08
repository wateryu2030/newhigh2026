'use client';

import { useState, useEffect } from 'react';
import { api, type MarketSentiment7dResponse } from '@/api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';
import { rechartsTooltipContent, rechartsTickSecondary } from '@/lib/chartTheme';

const FALLBACK_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SP500', 'NASDAQ', 'GOLD'];

function isAshare(s: string) {
  const code = s.split('.')[0];
  return code.length === 6 && /^\d+$/.test(code);
}

type TabKey = 'chart' | 'list' | 'sentiment';

const DIM_LABELS: Record<string, string> = {
  gain_loss_ratio: '涨跌家数比',
  avg_change: '平均涨幅',
  limit_up_down: '涨跌停比',
  strong_stock_ratio: '强势股占比',
  volume_activity: '成交活跃度',
  volatility: '波动率',
  trend_strength: '趋势强度',
};

export default function MarketPage() {
  const { t } = useLang();
  const [symbolList, setSymbolList] = useState<{ symbol: string; name: string }[]>([]);
  const [symbol, setSymbol] = useState('');
  const [prices, setPrices] = useState<{ t: string; p: number; o?: number; h?: number; l?: number }[]>([]);
  const [klineSource, setKlineSource] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabKey>('chart');
  const [sent7, setSent7] = useState<MarketSentiment7dResponse | null>(null);
  const [sent7Loading, setSent7Loading] = useState(false);

  useEffect(() => {
    api.ashareStocks()
      .then((r) => {
        if (r.stocks?.length) {
          setSymbolList(r.stocks);
          if (!symbol) setSymbol(r.stocks[0].symbol);
        } else {
          setSymbolList(FALLBACK_SYMBOLS.map((s) => ({ symbol: s, name: s })));
          if (!symbol) setSymbol(FALLBACK_SYMBOLS[0]);
        }
      })
      .catch(() => {
        setSymbolList(FALLBACK_SYMBOLS.map((s) => ({ symbol: s, name: s })));
        if (!symbol) setSymbol(FALLBACK_SYMBOLS[0]);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab !== 'sentiment') return;
    setSent7Loading(true);
    api
      .marketSentiment7d()
      .then(setSent7)
      .catch((e: unknown) => {
        const aborted = e instanceof Error && e.name === 'AbortError';
        const msg = e instanceof Error ? e.message : String(e);
        setSent7({
          error: aborted
            ? '请求超时（后端拉东财全市场现货或查库较慢，可稍后重试或先跑 Tushare 日 K / 写入实时表）'
            : msg || 'API 不可用',
          score: 0,
        });
      })
      .finally(() => setSent7Loading(false));
  }, [tab]);

  useEffect(() => {
    if (!symbol) return;
    setKlineSource(undefined);
    const u = symbol.toUpperCase();
    const interval = isAshare(symbol) ? '1d' : u.endsWith('USDT') ? '1h' : '1d';
    api.market(symbol, interval).then((r) => {
      setKlineSource(r.source);
      const d = r.data || [];
      if (d.length) {
        setPrices(d.map((bar) => ({
          t: typeof bar.t === 'string' ? bar.t.slice(0, 10) : String(bar.t),
          p: bar.close ?? bar.c ?? 0,
          o: bar.o,
          h: bar.h,
          l: bar.l,
        })));
      } else {
        setPrices([]);
      }
    }).catch(() => {
      setKlineSource(undefined);
      setPrices([]);
    });
  }, [symbol]);

  const displayList = symbolList.length ? symbolList : FALLBACK_SYMBOLS.map((s) => ({ symbol: s, name: s }));
  const current = symbol || displayList[0]?.symbol;

  function klineSubtitle(s: string): string {
    if (isAshare(s)) return '(A股日线 · DuckDB)';
    if (klineSource === 'binance') return '(USDT · Binance)';
    if (klineSource === 'stooq') return '(日线 · Stooq)';
    if (klineSource === 'duckdb' || klineSource === 'duckdb_pipeline') return '(DuckDB)';
    if (klineSource === 'akshare') return '(akshare 日线)';
    if (klineSource === 'none') return '(无本地数据)';
    if (!prices.length) {
      if (klineSource === 'stub') return '(暂无数据源，仅占位)';
      return '(暂无 K 线)';
    }
    return '';
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-on-surface">{t('market.title')}</h1>
      <p className="text-text-secondary text-sm">{t('market.hint')}</p>

      <div className="flex gap-2 border-b border-card-border pb-2">
        <button
          type="button"
          onClick={() => setTab('chart')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${tab === 'chart' ? 'bg-primary-fixed text-on-warm-fill' : 'bg-surface-container-high text-text-primary hover:bg-surface-container-highest'}`}
        >
          {t('market.quotes')}
        </button>
        <button
          type="button"
          onClick={() => setTab('list')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${tab === 'list' ? 'bg-primary-fixed text-on-warm-fill' : 'bg-surface-container-high text-text-primary hover:bg-surface-container-highest'}`}
        >
          {t('market.list')} ({displayList.length})
        </button>
        <button
          type="button"
          onClick={() => setTab('sentiment')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${tab === 'sentiment' ? 'bg-primary-fixed text-on-warm-fill' : 'bg-surface-container-high text-text-primary hover:bg-surface-container-highest'}`}
        >
          7 维情绪
        </button>
      </div>

      {tab === 'chart' && (
        <>
          <div className="flex flex-wrap gap-2">
            {displayList.slice(0, 80).map(({ symbol: s, name }) => (
              <button
                key={s}
                onClick={() => setSymbol(s)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${current === s ? 'bg-primary-fixed text-on-warm-fill' : 'bg-surface-container-high text-text-primary hover:bg-surface-container-highest'}`}
                title={name}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="card">
            <p className="mb-2 text-sm text-text-secondary">
              {current} — {t('market.kline')} {klineSubtitle(current)}
            </p>
            {loading ? (
              <p className="text-text-dim">{t('common.loading')}</p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={prices} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                  <XAxis dataKey="t" tick={rechartsTickSecondary} />
                  <YAxis tick={rechartsTickSecondary} />
                  <Tooltip
                    contentStyle={rechartsTooltipContent}
                    labelFormatter={(t) => t}
                    formatter={(value: number, _name: string, props: { payload?: { o?: number; h?: number; l?: number; p?: number } }) => {
                      const p = props?.payload;
                      if (p && (p.o != null || p.h != null || p.l != null)) {
                        return [`开 ${p.o ?? '—'} 高 ${p.h ?? '—'} 低 ${p.l ?? '—'} 收 ${value}`, '收'];
                      }
                      return [value, '收'];
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="p"
                    stroke="var(--color-chart-indigo)"
                    strokeWidth={2}
                    dot={false}
                    name="收"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}

      {tab === 'sentiment' && (
        <div className="card space-y-4">
          <p className="text-text-secondary text-sm">
            数据来源聚焦 <strong>东方财富</strong>（AkShare 全市场现货 / 库内实时表）与 <strong>Tushare 日 K</strong>：
            顺序为库内 <code className="text-xs bg-surface-container-high px-1 rounded">a_stock_realtime</code>
            → 东财现货接口 → 日 K 近似。请用调度或{' '}
            <code className="text-xs bg-surface-container-high px-1 rounded">python scripts/run_tushare_incremental.py</code>{' '}
            保持 <code className="text-xs bg-surface-container-high px-1 rounded">a_stock_daily</code> 的 MAX(date) 最新；盘中可{' '}
            <code className="text-xs bg-surface-container-high px-1 rounded">UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py</code>{' '}
            写入东财快照。
          </p>
          {sent7Loading ? (
            <p className="text-text-dim">{t('common.loading')}</p>
          ) : sent7?.error && !sent7.score ? (
            <div className="rounded-lg border border-[color:var(--color-warning-banner-border)] bg-[color:var(--color-warning-banner-bg)] p-4 text-sm text-[color:var(--color-badge-amber-text)]">
              <p className="font-medium">暂无法计算</p>
              <p className="mt-1">{sent7.error}{sent7.detail ? ` — ${sent7.detail}` : ''}</p>
              <p className="mt-2 text-text-secondary">
                请确认 <code className="text-xs bg-terminal-bg px-1 rounded">SENTIMENT_7D_AKSHARE_ENABLE=1</code> 且本机可访问东财，或已写入足够的
                a_stock_realtime；并跑 Tushare 日 K 增量以免日 K 口径滞后。
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <p className="text-text-dim text-sm">综合得分</p>
                  <p className="text-4xl font-bold text-on-surface tabular-nums">{sent7?.score ?? '—'}</p>
                </div>
                <div>
                  <p className="text-text-dim text-sm">情绪等级</p>
                  <p className="text-2xl">
                    {sent7?.emoji} {sent7?.level}
                  </p>
                </div>
                <p className="text-text-dim text-sm flex-1 min-w-[200px]">{sent7?.description}</p>
              </div>
              {(sent7?.data_source || sent7?.trade_date) && (
                <p className="text-xs text-text-dim">
                  {sent7.data_source === 'duckdb_a_stock_realtime' && '数据源：实时快照 · a_stock_realtime'}
                  {sent7.data_source === 'duckdb_a_stock_daily' && '数据源：日 K 近似 · a_stock_daily'}
                  {sent7.data_source === 'akshare_stock_zh_a_spot_em' && '数据源：AkShare 东财现货'}
                  {sent7.data_source === 'akshare_stock_zh_a_spot_sina' && '数据源：AkShare 新浪现货（盘中）'}
                  {sent7.trade_date ? ` · 交易日 ${sent7.trade_date}` : ''}
                  {sent7.calendar_lag_days != null && sent7.calendar_lag_days > 0
                    ? ` · 日 K 滞后 ${sent7.calendar_lag_days} 天（自然日）`
                    : ''}
                </p>
              )}
              {sent7?.stats && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                  {Object.entries(sent7.stats).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-surface-container-high/50 px-3 py-2">
                      <span className="block text-xs text-text-dim">{k}</span>
                      <span className="font-mono text-on-surface">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
              {sent7?.dimensions && (
                <div>
                  <p className="mb-2 text-sm text-text-secondary">分项得分（0–100）</p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {Object.entries(sent7.dimensions).map(([k, v]) => (
                      <div key={k} className="flex justify-between rounded bg-surface-container-high/30 px-3 py-2 text-sm">
                        <span className="text-text-secondary">{DIM_LABELS[k] ?? k}</span>
                        <span className="font-mono text-primary-fixed">{Number(v).toFixed(1)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {sent7?.data_source && (
                <p className="text-xs text-outline-variant">数据源: {sent7.data_source}</p>
              )}
            </>
          )}
        </div>
      )}

      {tab === 'list' && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-card-border text-text-secondary">
                <th className="py-2 pr-4">{t('market.code')}</th>
                <th className="py-2 pr-4">{t('market.name')}</th>
                <th className="py-2">{t('market.action')}</th>
              </tr>
            </thead>
            <tbody>
              {displayList.slice(0, 300).map(({ symbol: s, name }) => (
                <tr key={s} className="border-b border-card-border/80 hover:bg-surface-container-high/30">
                  <td className="py-2 pr-4 font-mono text-text-primary">{s}</td>
                  <td className="py-2 pr-4 text-text-primary">{name || '—'}</td>
                  <td className="py-2">
                    <button
                      type="button"
                      onClick={() => { setSymbol(s); setTab('chart'); }}
                      className="text-primary-fixed hover:underline"
                    >
                      {t('market.viewChart')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-text-dim">{displayList.length} {t('market.onlyFirst')}</p>
        </div>
      )}

      <p className="text-sm text-text-dim">
        {symbolList.length ? t('market.dataFrom') : t('market.stub')}
      </p>
    </div>
  );
}
