'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { api, type StockItem } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';

const LOAD_TIMEOUT_MS = 8000;

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    p,
    new Promise<T>((_, rej) => setTimeout(() => rej(new Error('加载超时')), ms)),
  ]);
}

export default function StocksPage() {
  const { t } = useLang();
  const [stocks, setStocks] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeoutHit, setTimeoutHit] = useState(false);
  const [emptyHint, setEmptyHint] = useState<string | null>(null);

  const fetchStocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    setEmptyHint(null);
    setTimeoutHit(false);

    const timer = setTimeout(() => {
      setTimeoutHit(true);
      setError('加载超时，请确认 Gateway 已启动（http://127.0.0.1:8000）');
      setLoading(false);
      setStocks([]);
    }, LOAD_TIMEOUT_MS);

    try {
      let list: StockItem[] = [];
      try {
        list = await withTimeout(api.stocks(500), LOAD_TIMEOUT_MS);
      } catch {
        list = [];
      }

      if (list.length === 0) {
        try {
          const res = await withTimeout(api.ashareStocks(), LOAD_TIMEOUT_MS);
          const arr = res?.stocks ?? [];
          list = arr.map((s: { symbol: string; name: string }) => ({
            ts_code: s.symbol,
            name: s.name ?? '',
            industry: '',
          }));
        } catch {
          list = [];
        }
      }

      if (list.length === 0) {
        try {
          const ensure = await api.ensureStocks();
          if (ensure?.ok && ensure?.rows > 0) {
            list = await withTimeout(api.stocks(500), LOAD_TIMEOUT_MS);
          }
        } catch {
          // ignore
        }
      }

      clearTimeout(timer);
      setStocks(list);
      if (list.length === 0) {
        setEmptyHint('暂无股票列表。请运行 scripts/run_automated.sh 或 python scripts/ensure_market_data.py 拉取股票池后刷新。');
      }
    } catch (e) {
      clearTimeout(timer);
      setError(e instanceof Error ? e.message : '请求失败');
      setStocks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  if (loading && !timeoutHit) {
    return (
      <div className="space-y-6 min-h-screen pb-24 md:pb-6">
        <h1 className="text-2xl font-bold text-white">{t('stocks.title')}</h1>
        <div className="flex items-center gap-3 text-slate-400">
          <LoadingSpinner />
          <span>加载股票列表…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 min-h-screen pb-24 md:pb-6">
        <h1 className="text-2xl font-bold text-white">{t('stocks.title')}</h1>
        <ErrorMessage message={error} onRetry={fetchStocks} />
      </div>
    );
  }

  return (
    <div className="space-y-6 min-h-screen pb-24 md:pb-6">
      <h1 className="text-2xl font-bold text-white">{t('stocks.title')}</h1>
      <p className="text-slate-400 text-sm">{t('stocks.hint')}</p>

      {emptyHint && stocks.length === 0 ? (
        <div className="card text-slate-400">
          <p>{emptyHint}</p>
          <button
            type="button"
            onClick={fetchStocks}
            className="mt-3 px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded text-white text-sm"
          >
            重新加载
          </button>
        </div>
      ) : (
        <>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-slate-400 border-b border-slate-600">
                  <th className="py-2 pr-4">{t('stocks.code')}</th>
                  <th className="py-2 pr-4">{t('stocks.name')}</th>
                  <th className="py-2 pr-4">{t('stocks.industry')}</th>
                  <th className="py-2">{t('stocks.action')}</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((s) => (
                  <tr key={s.ts_code} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 font-mono text-slate-300">{s.ts_code}</td>
                    <td className="py-2 pr-4 text-slate-300">{s.name || '—'}</td>
                    <td className="py-2 pr-4 text-slate-400">{s.industry || '—'}</td>
                    <td className="py-2">
                      <Link href={`/market?symbol=${encodeURIComponent(s.ts_code)}`} className="text-indigo-400 hover:underline">
                        {t('stocks.viewChart')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-slate-500 text-xs">{stocks.length} {t('stocks.rows')}</p>
          </div>
          <p className="text-sm text-slate-500">{t('stocks.dataFrom')}</p>
        </>
      )}
    </div>
  );
}
