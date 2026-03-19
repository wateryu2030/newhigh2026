'use client';

import { useState, useEffect } from 'react';
import { api, type MarketSentiment7dResponse } from '@/api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';

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
      .catch(() => setSent7({ error: 'API 不可用', score: 0 }))
      .finally(() => setSent7Loading(false));
  }, [tab]);

  useEffect(() => {
    if (!symbol) return;
    const interval = isAshare(symbol) ? '1d' : '1h';
    api.market(symbol, interval).then((r) => {
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
    }).catch(() => setPrices([]));
  }, [symbol]);

  const displayList = symbolList.length ? symbolList : FALLBACK_SYMBOLS.map((s) => ({ symbol: s, name: s }));
  const current = symbol || displayList[0]?.symbol;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('market.title')}</h1>
      <p className="text-slate-400 text-sm">{t('market.hint')}</p>

      <div className="flex gap-2 border-b border-slate-700 pb-2">
        <button
          type="button"
          onClick={() => setTab('chart')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${tab === 'chart' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
        >
          {t('market.quotes')}
        </button>
        <button
          type="button"
          onClick={() => setTab('list')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${tab === 'list' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
        >
          {t('market.list')} ({displayList.length})
        </button>
        <button
          type="button"
          onClick={() => setTab('sentiment')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${tab === 'sentiment' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
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
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${current === s ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                title={name}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="card">
            <p className="mb-2 text-sm text-slate-400">
              {current} — {t('market.kline')} {isAshare(current) ? '(A股日线 · DuckDB)' : '(stub)'}
            </p>
            {loading ? (
              <p className="text-slate-500">{t('common.loading')}</p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={prices} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                  <XAxis dataKey="t" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                    labelFormatter={(t) => t}
                    formatter={(value: number, _name: string, props: { payload?: { o?: number; h?: number; l?: number; p?: number } }) => {
                      const p = props?.payload;
                      if (p && (p.o != null || p.h != null || p.l != null)) {
                        return [`开 ${p.o ?? '—'} 高 ${p.h ?? '—'} 低 ${p.l ?? '—'} 收 ${value}`, '收'];
                      }
                      return [value, '收'];
                    }}
                  />
                  <Line type="monotone" dataKey="p" stroke="#6366F1" strokeWidth={2} dot={false} name="收" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </>
      )}

      {tab === 'sentiment' && (
        <div className="card space-y-4">
          <p className="text-slate-400 text-sm">
            全市场现货聚合评分（对齐 ClawHub「A Stock Monitor」思路，本仓库安全实现）。交易时段可先跑{' '}
            <code className="text-xs bg-slate-800 px-1 rounded">UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py</code>{' '}
            更新快照。
          </p>
          {sent7Loading ? (
            <p className="text-slate-500">{t('common.loading')}</p>
          ) : sent7?.error && !sent7.score ? (
            <div className="rounded-lg bg-amber-900/30 border border-amber-700/50 p-4 text-amber-200 text-sm">
              <p className="font-medium">暂无法计算</p>
              <p className="mt-1">{sent7.error}{sent7.detail ? ` — ${sent7.detail}` : ''}</p>
              <p className="mt-2 text-slate-400">请确认已写入 a_stock_realtime（实时采集）或本机可访问东财接口（akshare）。</p>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <p className="text-slate-500 text-sm">综合得分</p>
                  <p className="text-4xl font-bold text-white tabular-nums">{sent7?.score ?? '—'}</p>
                </div>
                <div>
                  <p className="text-slate-500 text-sm">情绪等级</p>
                  <p className="text-2xl">
                    {sent7?.emoji} {sent7?.level}
                  </p>
                </div>
                <p className="text-slate-500 text-sm flex-1 min-w-[200px]">{sent7?.description}</p>
              </div>
              {sent7?.stats && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                  {Object.entries(sent7.stats).map(([k, v]) => (
                    <div key={k} className="bg-slate-800/50 rounded-lg px-3 py-2">
                      <span className="text-slate-500 block text-xs">{k}</span>
                      <span className="text-slate-200 font-mono">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
              {sent7?.dimensions && (
                <div>
                  <p className="text-slate-400 text-sm mb-2">分项得分（0–100）</p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {Object.entries(sent7.dimensions).map(([k, v]) => (
                      <div key={k} className="flex justify-between bg-slate-800/30 rounded px-3 py-2 text-sm">
                        <span className="text-slate-400">{DIM_LABELS[k] ?? k}</span>
                        <span className="text-indigo-300 font-mono">{Number(v).toFixed(1)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {sent7?.data_source && (
                <p className="text-xs text-slate-600">数据源: {sent7.data_source}</p>
              )}
            </>
          )}
        </div>
      )}

      {tab === 'list' && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="text-slate-400 border-b border-slate-600">
                <th className="py-2 pr-4">{t('market.code')}</th>
                <th className="py-2 pr-4">{t('market.name')}</th>
                <th className="py-2">{t('market.action')}</th>
              </tr>
            </thead>
            <tbody>
              {displayList.slice(0, 300).map(({ symbol: s, name }) => (
                <tr key={s} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-2 pr-4 font-mono text-slate-300">{s}</td>
                  <td className="py-2 pr-4 text-slate-300">{name || '—'}</td>
                  <td className="py-2">
                    <button
                      type="button"
                      onClick={() => { setSymbol(s); setTab('chart'); }}
                      className="text-indigo-400 hover:underline"
                    >
                      {t('market.viewChart')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-slate-500 text-xs">{displayList.length} {t('market.onlyFirst')}</p>
        </div>
      )}

      <p className="text-sm text-slate-500">
        {symbolList.length ? t('market.dataFrom') : t('market.stub')}
      </p>
    </div>
  );
}
