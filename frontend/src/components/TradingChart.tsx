/**
 * 同花顺风格：K 线 + MA5/10/20/30/60 + 成交量 + 买卖点 + 现价/均线图例 + KDJ/MACD 副图
 */
import { useEffect, useRef, useMemo } from 'react';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import type { KlineBar } from '../types';

export interface MaPoint {
  time: string;
  value: number;
}

function last<T>(arr: T[]): T | undefined {
  return arr.length ? arr[arr.length - 1] : undefined;
}

function computeKDJ(bars: KlineBar[], n = 9, m1 = 3, m2 = 3): { time: string; k: number; d: number; j: number }[] {
  const out: { time: string; k: number; d: number; j: number }[] = [];
  const high = bars.map((b) => b.high);
  const low = bars.map((b) => b.low);
  const close = bars.map((b) => b.close);
  const times = bars.map((b) => (b.time || '').toString().slice(0, 10));
  let k = 50, d = 50, j = 50;
  for (let i = n - 1; i < close.length; i++) {
    const lowN = Math.min(...low.slice(i - n + 1, i + 1));
    const highN = Math.max(...high.slice(i - n + 1, i + 1));
    const rsv = highN > lowN ? ((close[i] - lowN) / (highN - lowN)) * 100 : 50;
    k = (k * (m1 - 1) + rsv) / m1;
    d = (d * (m2 - 1) + k) / m2;
    j = 3 * k - 2 * d;
    out.push({ time: times[i], k, d, j });
  }
  return out;
}

function ema(arr: number[], period: number): number[] {
  const alpha = 2 / (period + 1);
  const out: number[] = [];
  let prev = arr.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = 0; i < arr.length; i++) {
    if (i < period - 1) {
      out.push(NaN);
      continue;
    }
    if (i === period - 1) prev = arr.slice(0, period).reduce((a, b) => a + b, 0) / period;
    else prev = alpha * arr[i] + (1 - alpha) * prev;
    out.push(prev);
  }
  return out;
}

function computeMACD(bars: KlineBar[], fast = 12, slow = 26, signal = 9): { time: string; diff: number; dea: number; macd: number }[] {
  const close = bars.map((b) => b.close);
  const times = bars.map((b) => (b.time || '').toString().slice(0, 10));
  const emaFast = ema(close, fast);
  const emaSlow = ema(close, slow);
  const diff: number[] = [];
  for (let i = 0; i < close.length; i++) {
    diff.push(i >= slow - 1 && Number.isFinite(emaFast[i]) && Number.isFinite(emaSlow[i]) ? emaFast[i]! - emaSlow[i]! : NaN);
  }
  const deaArr = ema(diff.map((d) => (Number.isFinite(d) ? d : 0)), signal);
  const out: { time: string; diff: number; dea: number; macd: number }[] = [];
  for (let i = 0; i < close.length; i++) {
    const d = diff[i];
    const deaVal = deaArr[i];
    if (i >= slow - 1 + signal && Number.isFinite(d) && Number.isFinite(deaVal)) {
      out.push({ time: times[i], diff: d, dea: deaVal, macd: 2 * (d - deaVal) });
    }
  }
  return out;
}

export interface TradingChartProps {
  data: KlineBar[];
  signals?: { date: string; type: 'BUY' | 'SELL' | 'HOLD'; price: number }[];
  ma5?: MaPoint[];
  ma10?: MaPoint[];
  ma20?: MaPoint[];
  ma30?: MaPoint[];
  ma60?: MaPoint[];
  height?: number;
  /** 主图均线：basic 仅 MA5/10/20，full 含 MA30/60 */
  maSet?: 'basic' | 'full';
  /** 是否显示 KDJ 副图 */
  showKDJ?: boolean;
  /** 是否显示 MACD 副图 */
  showMACD?: boolean;
}

export default function TradingChart({
  data,
  signals = [],
  ma5 = [],
  ma10 = [],
  ma20 = [],
  ma30 = [],
  ma60 = [],
  height = 380,
  maSet = 'full',
  showKDJ = true,
  showMACD = true,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const kdjRef = useRef<HTMLDivElement>(null);
  const macdRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const kdjChartRef = useRef<IChartApi | null>(null);
  const macdChartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  const lastClose = last(data)?.close;
  const legend = useMemo(() => {
    const l5 = last(ma5)?.value;
    const l10 = last(ma10)?.value;
    const l20 = last(ma20)?.value;
    const l30 = last(ma30)?.value;
    const l60 = last(ma60)?.value;
    return {
      price: lastClose,
      ma5: l5,
      ma10: l10,
      ma20: l20,
      ma30: l30,
      ma60: l60,
    };
  }, [lastClose, ma5, ma10, ma20, ma30, ma60]);

  const kdjData = useMemo(() => computeKDJ(data), [data]);
  const macdData = useMemo(() => computeMACD(data), [data]);
  const lastKdj = last(kdjData);
  const lastMacd = last(macdData);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { color: '#111827' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: containerRef.current.offsetWidth,
      height,
      timeScale: { borderColor: '#1f2937', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.08, bottom: 0.25 } },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
    });
    candleRef.current = candleSeries;

    const tvData = data.map((b) => ({
      time: (b.time || '').toString().slice(0, 10) as string,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
    candleSeries.setData(tvData);

    const addMa = (arr: MaPoint[], color: string, title: string) => {
      if (arr.length) {
        const s = chart.addLineSeries({ color, lineWidth: 2, title });
        s.setData(arr.map((p) => ({ time: p.time.slice(0, 10) as string, value: p.value })));
      }
    };
    addMa(ma5, '#f59e0b', 'MA5');
    addMa(ma10, '#8b5cf6', 'MA10');
    addMa(ma20, '#3b82f6', 'MA20');
    if (maSet === 'full') {
      addMa(ma30, '#06b6d4', 'MA30');
      addMa(ma60, '#ec4899', 'MA60');
    }

    if (data.some((b) => b.volume != null)) {
      const volSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.75, bottom: 0 } });
      const volData = data
        .filter((b) => b.volume != null)
        .map((b) => ({
          time: (b.time || '').toString().slice(0, 10) as string,
          value: b.volume!,
          color: b.close >= b.open ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)',
        }));
      volSeries.setData(volData);
    }

    const markers = (signals || []).map((s) => {
      if (s.type === 'HOLD') {
        return { time: s.date.slice(0, 10) as string, position: 'aboveBar' as const, color: '#3b82f6', shape: 'circle' as const, text: 'HOLD' };
      }
      return {
        time: s.date.slice(0, 10) as string,
        position: (s.type === 'BUY' ? 'belowBar' : 'aboveBar') as 'belowBar' | 'aboveBar',
        color: s.type === 'BUY' ? '#10b981' : '#ef4444',
        shape: (s.type === 'BUY' ? 'arrowUp' : 'arrowDown') as 'arrowUp' | 'arrowDown',
        text: s.type,
      };
    });
    if (markers.length) candleSeries.setMarkers(markers);

    const handleResize = () => {
      if (containerRef.current && chartRef.current) chartRef.current.applyOptions({ width: containerRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
    };
  }, [data, signals, ma5, ma10, ma20, ma30, ma60, height, maSet]);

  useEffect(() => {
    if (!showKDJ || !kdjRef.current || kdjData.length === 0) return;
    const chart = createChart(kdjRef.current, {
      layout: { background: { color: '#0f172a' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: kdjRef.current.offsetWidth,
      height: 140,
      timeScale: { borderColor: '#1f2937', visible: true },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });
    kdjChartRef.current = chart;
    const kSeries = chart.addLineSeries({ color: '#f59e0b', lineWidth: 1, title: 'K' });
    const dSeries = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1, title: 'D' });
    const jSeries = chart.addLineSeries({ color: '#10b981', lineWidth: 1, title: 'J' });
    kSeries.setData(kdjData.map((p) => ({ time: p.time as string, value: p.k })));
    dSeries.setData(kdjData.map((p) => ({ time: p.time as string, value: p.d })));
    jSeries.setData(kdjData.map((p) => ({ time: p.time as string, value: p.j })));
    const handleResize = () => {
      if (kdjRef.current && kdjChartRef.current) kdjChartRef.current.applyOptions({ width: kdjRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      kdjChartRef.current = null;
    };
  }, [kdjData, showKDJ]);

  useEffect(() => {
    if (!showMACD || !macdRef.current || macdData.length === 0) return;
    const chart = createChart(macdRef.current, {
      layout: { background: { color: '#0f172a' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: macdRef.current.offsetWidth,
      height: 140,
      timeScale: { borderColor: '#1f2937', visible: true },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });
    macdChartRef.current = chart;
    const diffSeries = chart.addLineSeries({ color: '#8b5cf6', lineWidth: 1, title: 'DIFF' });
    const deaSeries = chart.addLineSeries({ color: '#06b6d4', lineWidth: 1, title: 'DEA' });
    const macdSeries = chart.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: '' });
    macdSeries.priceScale().applyOptions({ scaleMargins: { top: 0.6, bottom: 0 } });
    diffSeries.setData(macdData.map((p) => ({ time: p.time as string, value: p.diff })));
    deaSeries.setData(macdData.map((p) => ({ time: p.time as string, value: p.dea })));
    macdSeries.setData(
      macdData.map((p) => ({
        time: p.time as string,
        value: p.macd,
        color: p.macd >= 0 ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)',
      }))
    );
    const handleResize = () => {
      if (macdRef.current && macdChartRef.current) macdChartRef.current.applyOptions({ width: macdRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      macdChartRef.current = null;
    };
  }, [macdData, showMACD]);

  return (
    <div style={{ width: '100%' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px 20px',
          padding: '8px 0',
          marginBottom: 4,
          borderBottom: '1px solid #1f2937',
          fontSize: 12,
          color: '#9ca3af',
        }}
      >
        {legend.price != null && (
          <span style={{ color: '#f1f5f9', fontWeight: 600 }}>现价 {legend.price.toFixed(2)}</span>
        )}
        {legend.ma5 != null && <span style={{ color: '#f59e0b' }}>MA5 {legend.ma5.toFixed(2)}</span>}
        {legend.ma10 != null && <span style={{ color: '#8b5cf6' }}>MA10 {legend.ma10.toFixed(2)}</span>}
        {legend.ma20 != null && <span style={{ color: '#3b82f6' }}>MA20 {legend.ma20.toFixed(2)}</span>}
        {maSet === 'full' && legend.ma30 != null && <span style={{ color: '#06b6d4' }}>MA30 {legend.ma30.toFixed(2)}</span>}
        {maSet === 'full' && legend.ma60 != null && <span style={{ color: '#ec4899' }}>MA60 {legend.ma60.toFixed(2)}</span>}
        {showKDJ && lastKdj && (
          <span style={{ marginLeft: 8 }}>
            KDJ K:{lastKdj.k.toFixed(2)} D:{lastKdj.d.toFixed(2)} J:{lastKdj.j.toFixed(2)}
          </span>
        )}
        {showMACD && lastMacd && (
          <span>
            MACD {lastMacd.macd.toFixed(3)} DIFF:{lastMacd.diff.toFixed(3)} DEA:{lastMacd.dea.toFixed(3)}
          </span>
        )}
      </div>
      <div ref={containerRef} style={{ width: '100%' }} />
      {showKDJ && kdjData.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>KDJ</div>
          <div ref={kdjRef} style={{ width: '100%' }} />
        </div>
      )}
      {showMACD && macdData.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>MACD</div>
          <div ref={macdRef} style={{ width: '100%' }} />
        </div>
      )}
    </div>
  );
}
