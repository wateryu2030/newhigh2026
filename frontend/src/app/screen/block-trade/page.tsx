'use client';

import { useCallback, useState } from 'react';
import { api, type BlockTradeSidewaysItem, type BlockTradeSidewaysResponse } from '@/api/client';
import { ErrorMessage } from '@/components/ErrorMessage';
import { useLang } from '@/context/LangContext';

const DEFAULTS = {
  block_days: 30,
  lookback_days: 60,
  range_ratio_max: 0.32,
  trend_abs_max: 0.12,
  ret_std_max: 0.035,
  min_amount_wan: 0,
  max_codes: 400,
};

export default function BlockTradeSidewaysPage() {
  const { t } = useLang();
  const [params, setParams] = useState(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [data, setData] = useState<BlockTradeSidewaysResponse | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await api.screenBlockTradeSideways({
        block_days: params.block_days,
        lookback_days: params.lookback_days,
        range_ratio_max: params.range_ratio_max,
        trend_abs_max: params.trend_abs_max,
        ret_std_max: params.ret_std_max,
        min_amount_wan: params.min_amount_wan,
        max_codes: params.max_codes,
      });
      setData(r);
    } catch (e: unknown) {
      setData(null);
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [params]);

  const items: BlockTradeSidewaysItem[] = data?.items ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-on-surface">{t('blockTradeScreen.title')}</h1>
        <p className="text-sm text-text-secondary">{t('blockTradeScreen.subtitle')}</p>
        <p className="text-xs text-text-dim">{t('blockTradeScreen.disclaimer')}</p>
      </header>

      <div className="card space-y-4 border border-card-border p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.blockDays')}</span>
            <input
              type="number"
              min={5}
              max={120}
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.block_days}
              onChange={(e) =>
                setParams((p) => ({ ...p, block_days: Number(e.target.value) || DEFAULTS.block_days }))
              }
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.lookback')}</span>
            <input
              type="number"
              min={15}
              max={250}
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.lookback_days}
              onChange={(e) =>
                setParams((p) => ({ ...p, lookback_days: Number(e.target.value) || DEFAULTS.lookback_days }))
              }
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.rangeMax')}</span>
            <input
              type="number"
              step="0.01"
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.range_ratio_max}
              onChange={(e) =>
                setParams((p) => ({ ...p, range_ratio_max: Number(e.target.value) || DEFAULTS.range_ratio_max }))
              }
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.trendMax')}</span>
            <input
              type="number"
              step="0.01"
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.trend_abs_max}
              onChange={(e) =>
                setParams((p) => ({ ...p, trend_abs_max: Number(e.target.value) || DEFAULTS.trend_abs_max }))
              }
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.retStdMax')}</span>
            <input
              type="number"
              step="0.001"
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.ret_std_max}
              onChange={(e) =>
                setParams((p) => ({ ...p, ret_std_max: Number(e.target.value) || DEFAULTS.ret_std_max }))
              }
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.minAmount')}</span>
            <input
              type="number"
              min={0}
              step="10"
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.min_amount_wan}
              onChange={(e) =>
                setParams((p) => ({ ...p, min_amount_wan: Number(e.target.value) || 0 }))
              }
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">{t('blockTradeScreen.maxCodes')}</span>
            <input
              type="number"
              min={50}
              max={2000}
              step="50"
              className="rounded-lg border border-card-border bg-surface-container px-3 py-2 text-on-surface"
              value={params.max_codes}
              onChange={(e) =>
                setParams((p) => ({ ...p, max_codes: Number(e.target.value) || DEFAULTS.max_codes }))
              }
            />
          </label>
        </div>
        <button
          type="button"
          disabled={loading}
          onClick={() => void run()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:opacity-90 disabled:opacity-50"
        >
          {loading ? t('blockTradeScreen.loading') : t('blockTradeScreen.run')}
        </button>
      </div>

      {err ? <ErrorMessage message={err} onRetry={() => void run()} /> : null}

      {data?.note ? (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-on-surface">
          {t('blockTradeScreen.note')}: {data.note}
        </p>
      ) : null}

      {data?.block_range ? (
        <p className="text-sm text-text-secondary">
          {t('blockTradeScreen.blockRange')}: {data.block_range.start} — {data.block_range.end}
          {data.params ? (
            <span className="ml-2 text-text-dim">
              · {t('blockTradeScreen.params')}: {JSON.stringify(data.params)}
            </span>
          ) : null}
        </p>
      ) : null}

      {!loading && data && items.length === 0 && !data.note ? (
        <p className="text-sm text-text-secondary">{t('blockTradeScreen.empty')}</p>
      ) : null}

      {items.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-card-border">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead className="bg-surface-container-high text-text-secondary">
              <tr>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.code')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.name')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.blockWan')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.blockN')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.range')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.trend')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.vol')}</th>
                <th className="px-3 py-2 font-medium">{t('blockTradeScreen.col.last')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.code} className="border-t border-card-border hover:bg-surface-container/50">
                  <td className="px-3 py-2 font-mono text-on-surface">{row.code}</td>
                  <td className="px-3 py-2 text-on-surface">{row.name || '—'}</td>
                  <td className="px-3 py-2">{row.block_amount_wan.toFixed(2)}</td>
                  <td className="px-3 py-2">{row.block_n}</td>
                  <td className="px-3 py-2">{row.range_ratio.toFixed(4)}</td>
                  <td className="px-3 py-2">{(row.trend_ret * 100).toFixed(2)}%</td>
                  <td className="px-3 py-2">{row.ret_std.toFixed(4)}</td>
                  <td className="px-3 py-2">{row.last_close.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
