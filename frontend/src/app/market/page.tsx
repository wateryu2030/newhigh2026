'use client';

import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';

const FALLBACK_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SP500', 'NASDAQ', 'GOLD'];

function isAshare(s: string) {
  const code = s.split('.')[0];
  return code.length === 6 && /^\d+$/.test(code);
}

type TabKey = 'chart' | 'list';

export default function MarketPage() {
  const { t } = useLang();
  const [symbolList, setSymbolList] = useState<{ symbol: string; name: string }[]>([]);
  const [symbol, setSymbol] = useState('');
  const [prices, setPrices] = useState<{ t: string; p: number; o?: number; h?: number; l?: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabKey>('chart');

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
