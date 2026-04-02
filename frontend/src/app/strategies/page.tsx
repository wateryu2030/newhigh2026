'use client';

import { useEffect, useState, useMemo } from 'react';
import { api, type StrategyMarketItem, type BacktestResultResponse } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { EquityCurve } from '@/components/EquityCurve';
import { AsyncState } from '@/components/AsyncState';

function formatPct(v: number | null): string {
  if (v == null) return '—';
  return `${Number(v).toFixed(1)}%`;
}
function formatNum(v: number | null): string {
  if (v == null) return '—';
  return Number(v).toFixed(2);
}

function defaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(start.getFullYear() - 1);
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10),
  };
}

export default function StrategiesPage() {
  const { t } = useLang();
  const [items, setItems] = useState<StrategyMarketItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'return_pct' | 'sharpe_ratio' | 'max_drawdown' | null>(null);
  const [sortDesc, setSortDesc] = useState(true);
  const [backtestSymbol, setBacktestSymbol] = useState('000001.SZ');
  const [backtestStart, setBacktestStart] = useState(defaultDateRange().start_date);
  const [backtestEnd, setBacktestEnd] = useState(defaultDateRange().end_date);
  const [backtestResult, setBacktestResult] = useState<BacktestResultResponse | null>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);

  const fetchMarket = () => {
    setLoading(true);
    setLoadError(null);
    api
      .strategiesMarket(50)
      .then((r) => setItems(r.items || []))
      .catch(() => {
        setItems([]);
        setLoadError('加载策略市场失败，请检查网络或稍后重试');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchMarket();
  }, []);

  const sorted = useMemo(() => {
    if (!sortBy) return items;
    return [...items].sort((a, b) => {
      const va = a[sortBy] ?? -1e9;
      const vb = b[sortBy] ?? -1e9;
      if (sortBy === 'max_drawdown') return sortDesc ? vb - va : va - vb;
      return sortDesc ? (vb as number) - (va as number) : (va as number) - (vb as number);
    });
  }, [items, sortBy, sortDesc]);

  const toggleSort = (key: 'return_pct' | 'sharpe_ratio' | 'max_drawdown') => {
    if (sortBy === key) setSortDesc((d) => !d);
    else setSortBy(key);
  };

  const runBacktest = () => {
    setBacktestLoading(true);
    setBacktestResult(null);
    api
      .backtestResult({ symbol: backtestSymbol, start_date: backtestStart, end_date: backtestEnd })
      .then(setBacktestResult)
      .catch(() => setBacktestResult(null))
      .finally(() => setBacktestLoading(false));
  };

  return (
    <div className="space-y-6 min-h-screen pb-24 md:pb-6">
      <h1 className="text-2xl font-bold text-white">{t('strategies.title')}</h1>
      <p className="text-slate-400 text-sm">{t('strategies.marketHint')}</p>

      <AsyncState<StrategyMarketItem[]>
        loading={loading}
        error={loadError}
        data={loading || loadError ? undefined : sorted}
        isEmpty={(rows) => rows.length === 0}
        emptyTitle={t('strategies.noData')}
        emptyDescription={t('strategies.marketHint')}
        loadingMessage={t('common.loading')}
        onRetry={fetchMarket}
      >
        {(rows) => (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-600 text-slate-400">
                  <th className="p-3 font-medium">{t('strategies.id')}</th>
                  <th className="p-3 font-medium">{t('strategies.name')}</th>
                  <th
                    className="p-3 font-medium cursor-pointer hover:text-white"
                    onClick={() => toggleSort('return_pct')}
                  >
                    {t('strategies.returnPct')} {sortBy === 'return_pct' && (sortDesc ? '↓' : '↑')}
                  </th>
                  <th
                    className="p-3 font-medium cursor-pointer hover:text-white"
                    onClick={() => toggleSort('sharpe_ratio')}
                  >
                    {t('strategies.sharpe')} {sortBy === 'sharpe_ratio' && (sortDesc ? '↓' : '↑')}
                  </th>
                  <th
                    className="p-3 font-medium cursor-pointer hover:text-white"
                    onClick={() => toggleSort('max_drawdown')}
                  >
                    {t('strategies.drawdown')} {sortBy === 'max_drawdown' && (sortDesc ? '↓' : '↑')}
                  </th>
                  <th className="p-3 font-medium">{t('strategies.status')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.id} className="border-b border-slate-700/50 hover:bg-slate-800/50">
                    <td className="p-3 font-mono text-white">{s.id}</td>
                    <td className="p-3 text-slate-200">{s.name}</td>
                    <td className="p-3 text-emerald-400">{formatPct(s.return_pct)}</td>
                    <td className="p-3 text-slate-300">{formatNum(s.sharpe_ratio)}</td>
                    <td className="p-3 text-slate-300">
                      {s.max_drawdown != null ? `${s.max_drawdown}%` : '—'}
                    </td>
                    <td className="p-3">
                      <span
                        className={
                          s.status === 'live' || s.status === 'active'
                            ? 'text-emerald-400'
                            : 'text-amber-400'
                        }
                      >
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncState>

      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-2">{t('strategies.backtestTitle')}</h2>
        <p className="text-slate-400 text-sm mb-4">{t('strategies.backtestHint')}</p>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <label className="flex flex-col gap-1">
            <span className="text-slate-500 text-xs">{t('strategies.symbol')}</span>
            <input
              type="text"
              value={backtestSymbol}
              onChange={(e) => setBacktestSymbol(e.target.value)}
              className="rounded bg-slate-800 border border-slate-600 px-3 py-2 text-white text-sm w-32"
              placeholder="000001.SZ"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-500 text-xs">{t('strategies.startDate')}</span>
            <input
              type="date"
              value={backtestStart}
              onChange={(e) => setBacktestStart(e.target.value)}
              className="rounded bg-slate-800 border border-slate-600 px-3 py-2 text-white text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-500 text-xs">{t('strategies.endDate')}</span>
            <input
              type="date"
              value={backtestEnd}
              onChange={(e) => setBacktestEnd(e.target.value)}
              className="rounded bg-slate-800 border border-slate-600 px-3 py-2 text-white text-sm"
            />
          </label>
          <button
            type="button"
            onClick={runBacktest}
            disabled={backtestLoading}
            className="rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-4 py-2 text-white text-sm font-medium"
          >
            {backtestLoading ? t('common.loading') : t('strategies.runBacktest')}
          </button>
        </div>
        {backtestResult && (
          <>
            {backtestResult.error && (
              <p className="text-amber-400 text-sm mb-2">{backtestResult.error}</p>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mb-4">
              <div>
                <span className="text-slate-500">Sharpe</span>
                <p className="text-white font-medium">{formatNum(backtestResult.sharpe_ratio)}</p>
              </div>
              <div>
                <span className="text-slate-500">{t('strategies.drawdown')}</span>
                <p className="text-white font-medium">
                  {backtestResult.max_drawdown != null ? `${backtestResult.max_drawdown}%` : '—'}
                </p>
              </div>
              <div>
                <span className="text-slate-500">{t('strategies.returnPct')}</span>
                <p className="text-white font-medium">{formatPct(backtestResult.total_return)}</p>
              </div>
              <div>
                <span className="text-slate-500">Trades</span>
                <p className="text-white font-medium">{backtestResult.trade_count ?? '—'}</p>
              </div>
            </div>
            {backtestResult.equity_curve?.length > 0 && (
              <EquityCurve
                dataPoints={backtestResult.equity_curve}
                height={300}
                title={t('dashboard.equityCurve')}
              />
            )}
            {backtestResult.equity_curve?.length === 0 && !backtestResult.error && (
              <p className="text-slate-500 text-sm">无资金曲线数据（可能无日 K 或信号）</p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
