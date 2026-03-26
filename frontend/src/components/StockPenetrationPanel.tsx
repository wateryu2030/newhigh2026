'use client';

import { useEffect, useRef, useState } from 'react';
import { api, type MarketResponse, type NewsItem } from '@/api/client';
import { eastMoneyIndividualUrl, toAshareKlineSymbol } from '@/lib/ashareSymbol';
import { useLang } from '@/context/LangContext';
import { chgClass, fmtPct, fmtPrice } from '@/lib/marketFormat';

export type StockPenetrationRow = {
  code: string;
  stock_name?: string | null;
  last_price?: number | null;
  change_pct?: number | null;
};

function candleTime(iso: string): string {
  return iso.slice(0, 10);
}

export function StockPenetrationPanel({
  row,
  onBack,
}: {
  row: StockPenetrationRow;
  onBack: () => void;
}) {
  const { t } = useLang();
  const symbol = toAshareKlineSymbol(row.code);
  const chartRef = useRef<HTMLDivElement>(null);
  const chartApiRef = useRef<{ remove: () => void } | null>(null);
  const [klines, setKlines] = useState<MarketResponse | null>(null);
  const [kError, setKError] = useState<string | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    setKError(null);
    setKlines(null);
    api
      .market(symbol, '1d', 160)
      .then((r) => {
        if (!cancelled) setKlines(r);
      })
      .catch((e) => {
        if (!cancelled) setKError(e instanceof Error ? e.message : 'error');
      });
    api
      .news(symbol.split('.')[0], 8)
      .then((r) => {
        if (!cancelled) setNews(r.news || []);
      })
      .catch(() => {
        if (!cancelled) setNews([]);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  useEffect(() => {
    const el = chartRef.current;
    if (!el || !klines?.data?.length) {
      if (chartApiRef.current) {
        chartApiRef.current.remove();
        chartApiRef.current = null;
      }
      return;
    }

    let disposed = false;
    (async () => {
      const { createChart, ColorType, CrosshairMode } = await import('lightweight-charts');
      if (disposed || !chartRef.current) return;
      chartApiRef.current?.remove();
      chartApiRef.current = null;

      const chart = createChart(chartRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: '#14171C' },
          textColor: '#94A3B8',
        },
        grid: {
          vertLines: { color: '#2A2E36' },
          horzLines: { color: '#2A2E36' },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: '#2A2E36' },
        timeScale: { borderColor: '#2A2E36', timeVisible: true, secondsVisible: false },
        width: chartRef.current.clientWidth,
        height: 320,
      });

      const candle = chart.addCandlestickSeries({
        upColor: '#22C55E',
        downColor: '#EF4444',
        borderVisible: false,
        wickUpColor: '#22C55E',
        wickDownColor: '#EF4444',
      });
      const vol = chart.addHistogramSeries({
        color: '#6366F1',
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
      });
      chart.priceScale('vol').applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });
      chart.priceScale('right').applyOptions({
        scaleMargins: { top: 0.08, bottom: 0.2 },
      });

      const candles = klines.data.map((d) => ({
        time: candleTime(d.t) as import('lightweight-charts').Time,
        open: d.o,
        high: d.h,
        low: d.l,
        close: d.c,
      }));
      const vols = klines.data.map((d) => ({
        time: candleTime(d.t) as import('lightweight-charts').Time,
        value: d.v,
        color: d.c >= d.o ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.35)',
      }));
      candle.setData(candles);
      vol.setData(vols);
      chart.timeScale().fitContent();

      const ro = new ResizeObserver(() => {
        if (chartRef.current && chart) {
          chart.applyOptions({ width: chartRef.current.clientWidth });
        }
      });
      ro.observe(chartRef.current);
      chartApiRef.current = {
        remove: () => {
          ro.disconnect();
          chart.remove();
        },
      };
    })();

    return () => {
      disposed = true;
      chartApiRef.current?.remove();
      chartApiRef.current = null;
    };
  }, [klines]);

  const emUrl = eastMoneyIndividualUrl(row.code);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg border border-card-border px-3 py-1.5 text-sm text-text-secondary hover:bg-white/5"
        >
          ← {t('drill.penetrationBack')}
        </button>
        <span className="font-mono text-lg font-semibold text-text-primary">{symbol}</span>
        <span className="text-text-secondary">{row.stock_name?.trim() || '—'}</span>
        {row.last_price != null && (
          <span className="font-mono text-text-primary">{fmtPrice(row.last_price)}</span>
        )}
        {row.change_pct != null && (
          <span className={`font-mono ${chgClass(row.change_pct)}`}>{fmtPct(row.change_pct)}</span>
        )}
        <a
          href={emUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-sm text-indigo-400 hover:underline"
        >
          {t('drill.penetrationEastmoney')} ↗
        </a>
      </div>

      <p className="text-[11px] text-text-secondary">{t('drill.penetrationKlineHint')}</p>

      {kError && <p className="text-sm text-accent-red">{kError}</p>}
      {!kError && klines && (!klines.data || klines.data.length === 0) && (
        <p className="text-sm text-amber-200/90">{t('drill.penetrationNoBars')}</p>
      )}

      <div ref={chartRef} className="h-[320px] w-full min-h-[280px] rounded-lg border border-card-border bg-[#0f1218]" />

      <div>
        <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-text-secondary">
          {t('drill.penetrationNews')}
        </h4>
        <ul className="max-h-[200px] space-y-2 overflow-y-auto text-sm">
          {news.length === 0 ? (
            <li className="text-text-secondary">{t('drill.penetrationNoNews')}</li>
          ) : (
            news.map((n, i) => (
              <li key={n.url || `${i}-${n.title}`} className="border-b border-card-border/40 pb-2">
                {n.url && /^https?:\/\//i.test(n.url.trim()) ? (
                  <a
                    href={n.url.trim()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-400 hover:underline"
                  >
                    {n.title || '—'}
                  </a>
                ) : (
                  <span className="text-text-primary">{n.title || '—'}</span>
                )}
                <span className="ml-2 text-xs text-text-secondary">
                  {n.publish_time} {n.source ? `· ${n.source}` : ''}
                </span>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
