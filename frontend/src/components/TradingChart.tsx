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

function computeRSI(bars: KlineBar[], period = 14): { time: string; value: number }[] {
  const close = bars.map((b) => b.close);
  const times = bars.map((b) => (b.time || '').toString().slice(0, 10));
  const out: { time: string; value: number }[] = [];
  let up = 0, down = 0;
  for (let i = 0; i < close.length; i++) {
    if (i < period) {
      out.push({ time: times[i], value: 50 });
      continue;
    }
    up = 0;
    down = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const ch = close[j]! - close[j - 1]!;
      if (ch > 0) up += ch;
      else down -= ch;
    }
    const rs = down === 0 ? 100 : up / down;
    const rsi = 100 - 100 / (1 + rs);
    out.push({ time: times[i], value: Number.isFinite(rsi) ? rsi : 50 });
  }
  return out;
}

function computeBOLL(bars: KlineBar[], period = 20, k = 2): { time: string; upper: number; mid: number; lower: number }[] {
  const close = bars.map((b) => b.close);
  const times = bars.map((b) => (b.time || '').toString().slice(0, 10));
  const out: { time: string; upper: number; mid: number; lower: number }[] = [];
  for (let i = 0; i < close.length; i++) {
    if (i < period - 1) {
      out.push({ time: times[i], upper: close[i]!, mid: close[i]!, lower: close[i]! });
      continue;
    }
    const slice = close.slice(i - period + 1, i + 1);
    const mid = slice.reduce((a, b) => a + b, 0) / period;
    const std = Math.sqrt(slice.reduce((s, v) => s + (v - mid) ** 2, 0) / period) || 0;
    out.push({ time: times[i], upper: mid + k * std, mid, lower: mid - k * std });
  }
  return out;
}

function computeCCI(bars: KlineBar[], period = 20): { time: string; value: number }[] {
  const high = bars.map((b) => b.high);
  const low = bars.map((b) => b.low);
  const close = bars.map((b) => b.close);
  const times = bars.map((b) => (b.time || '').toString().slice(0, 10));
  const tp = close.map((_, i) => (high[i]! + low[i]! + close[i]!) / 3);
  const out: { time: string; value: number }[] = [];
  for (let i = 0; i < close.length; i++) {
    if (i < period - 1) {
      out.push({ time: times[i], value: 0 });
      continue;
    }
    const slice = tp.slice(i - period + 1, i + 1);
    const ma = slice.reduce((a, b) => a + b, 0) / period;
    const md = Math.abs(slice.reduce((s, v) => s + (v - ma), 0)) / period || 0.0001;
    const cci = (tp[i]! - ma) / (0.015 * md);
    out.push({ time: times[i], value: Number.isFinite(cci) ? cci : 0 });
  }
  return out;
}

function computeOBV(bars: KlineBar[]): { time: string; value: number }[] {
  const times = bars.map((b) => (b.time || '').toString().slice(0, 10));
  const close = bars.map((b) => b.close);
  const volume = bars.map((b) => b.volume ?? 0);
  let obv = 0;
  return times.map((t, i) => {
    if (i > 0 && close[i]! > close[i - 1]!) obv += volume[i]!;
    else if (i > 0 && close[i]! < close[i - 1]!) obv -= volume[i]!;
    return { time: t, value: obv };
  });
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
  /** 是否显示 RSI 副图 */
  showRSI?: boolean;
  /** 是否显示 BOLL 副图 */
  showBOLL?: boolean;
  /** 是否显示 CCI 副图 */
  showCCI?: boolean;
  /** 是否显示 OBV 副图 */
  showOBV?: boolean;
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
  showRSI = false,
  showBOLL = false,
  showCCI = false,
  showOBV = false,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const kdjRef = useRef<HTMLDivElement>(null);
  const macdRef = useRef<HTMLDivElement>(null);
  const rsiRef = useRef<HTMLDivElement>(null);
  const bollRef = useRef<HTMLDivElement>(null);
  const cciRef = useRef<HTMLDivElement>(null);
  const obvRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const kdjChartRef = useRef<IChartApi | null>(null);
  const macdChartRef = useRef<IChartApi | null>(null);
  const rsiChartRef = useRef<IChartApi | null>(null);
  const bollChartRef = useRef<IChartApi | null>(null);
  const cciChartRef = useRef<IChartApi | null>(null);
  const obvChartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  /** 所有副图实例，用于与主图时间轴联动 */
  const subChartsRef = useRef<IChartApi[]>([]);
  const applyMainRange = (main: IChartApi, sub: IChartApi) => {
    try {
      const r = main.timeScale().getVisibleLogicalRange();
      if (r) sub.timeScale().setVisibleLogicalRange(r);
    } catch (_) {}
  };

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
  const rsiData = useMemo(() => computeRSI(data), [data]);
  const bollData = useMemo(() => computeBOLL(data), [data]);
  const cciData = useMemo(() => computeCCI(data), [data]);
  const obvData = useMemo(() => computeOBV(data), [data]);
  const lastKdj = last(kdjData);
  const lastMacd = last(macdData);
  const lastRsi = last(rsiData);
  const lastBoll = last(bollData);
  const lastCci = last(cciData);
  const lastObv = last(obvData);

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

    const onRangeChange = (range: { from: number; to: number } | null) => {
      if (!range) return;
      subChartsRef.current.forEach((c) => {
        try { c.timeScale().setVisibleLogicalRange(range); } catch (_) {}
      });
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRangeChange);

    const handleResize = () => {
      if (containerRef.current && chartRef.current) chartRef.current.applyOptions({ width: containerRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRangeChange); } catch (_) {}
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
    subChartsRef.current.push(chart);
    if (chartRef.current) applyMainRange(chartRef.current, chart);
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
      subChartsRef.current = subChartsRef.current.filter((c) => c !== chart);
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
    subChartsRef.current.push(chart);
    if (chartRef.current) applyMainRange(chartRef.current, chart);
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
      subChartsRef.current = subChartsRef.current.filter((c) => c !== chart);
      chart.remove();
      macdChartRef.current = null;
    };
  }, [macdData, showMACD]);

  useEffect(() => {
    if (!showRSI || !rsiRef.current || rsiData.length === 0) return;
    const chart = createChart(rsiRef.current, {
      layout: { background: { color: '#0f172a' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: rsiRef.current.offsetWidth,
      height: 120,
      timeScale: { borderColor: '#1f2937', visible: true },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });
    rsiChartRef.current = chart;
    subChartsRef.current.push(chart);
    if (chartRef.current) applyMainRange(chartRef.current, chart);
    const rsiSeries = chart.addLineSeries({ color: '#a855f7', lineWidth: 1, title: 'RSI' });
    rsiSeries.setData(rsiData.map((p) => ({ time: p.time as string, value: p.value })));
    const handleResize = () => {
      if (rsiRef.current && rsiChartRef.current) rsiChartRef.current.applyOptions({ width: rsiRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      subChartsRef.current = subChartsRef.current.filter((c) => c !== chart);
      chart.remove();
      rsiChartRef.current = null;
    };
  }, [rsiData, showRSI]);

  useEffect(() => {
    if (!showBOLL || !bollRef.current || bollData.length === 0) return;
    const chart = createChart(bollRef.current, {
      layout: { background: { color: '#0f172a' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: bollRef.current.offsetWidth,
      height: 120,
      timeScale: { borderColor: '#1f2937', visible: true },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });
    bollChartRef.current = chart;
    subChartsRef.current.push(chart);
    if (chartRef.current) applyMainRange(chartRef.current, chart);
    const upperSeries = chart.addLineSeries({ color: '#f59e0b', lineWidth: 1, title: '上轨' });
    const midSeries = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1, title: '中轨' });
    const lowerSeries = chart.addLineSeries({ color: '#10b981', lineWidth: 1, title: '下轨' });
    upperSeries.setData(bollData.map((p) => ({ time: p.time as string, value: p.upper })));
    midSeries.setData(bollData.map((p) => ({ time: p.time as string, value: p.mid })));
    lowerSeries.setData(bollData.map((p) => ({ time: p.time as string, value: p.lower })));
    const handleResize = () => {
      if (bollRef.current && bollChartRef.current) bollChartRef.current.applyOptions({ width: bollRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      subChartsRef.current = subChartsRef.current.filter((c) => c !== chart);
      chart.remove();
      bollChartRef.current = null;
    };
  }, [bollData, showBOLL]);

  useEffect(() => {
    if (!showCCI || !cciRef.current || cciData.length === 0) return;
    const chart = createChart(cciRef.current, {
      layout: { background: { color: '#0f172a' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: cciRef.current.offsetWidth,
      height: 120,
      timeScale: { borderColor: '#1f2937', visible: true },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });
    cciChartRef.current = chart;
    subChartsRef.current.push(chart);
    if (chartRef.current) applyMainRange(chartRef.current, chart);
    const cciSeries = chart.addLineSeries({ color: '#06b6d4', lineWidth: 1, title: 'CCI' });
    cciSeries.setData(cciData.map((p) => ({ time: p.time as string, value: p.value })));
    const handleResize = () => {
      if (cciRef.current && cciChartRef.current) cciChartRef.current.applyOptions({ width: cciRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      subChartsRef.current = subChartsRef.current.filter((c) => c !== chart);
      chart.remove();
      cciChartRef.current = null;
    };
  }, [cciData, showCCI]);

  useEffect(() => {
    if (!showOBV || !obvRef.current || obvData.length === 0) return;
    const chart = createChart(obvRef.current, {
      layout: { background: { color: '#0f172a' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: obvRef.current.offsetWidth,
      height: 120,
      timeScale: { borderColor: '#1f2937', visible: true },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.1 } },
    });
    obvChartRef.current = chart;
    subChartsRef.current.push(chart);
    if (chartRef.current) applyMainRange(chartRef.current, chart);
    const obvSeries = chart.addLineSeries({ color: '#ec4899', lineWidth: 1, title: 'OBV' });
    obvSeries.setData(obvData.map((p) => ({ time: p.time as string, value: p.value })));
    const handleResize = () => {
      if (obvRef.current && obvChartRef.current) obvChartRef.current.applyOptions({ width: obvRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      subChartsRef.current = subChartsRef.current.filter((c) => c !== chart);
      chart.remove();
      obvChartRef.current = null;
    };
  }, [obvData, showOBV]);

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
        {showRSI && lastRsi != null && (
          <span style={{ marginLeft: 8 }}>RSI {lastRsi.value.toFixed(1)}</span>
        )}
        {showBOLL && lastBoll != null && (
          <span>BOLL 上:{lastBoll.upper.toFixed(2)} 中:{lastBoll.mid.toFixed(2)} 下:{lastBoll.lower.toFixed(2)}</span>
        )}
        {showCCI && lastCci != null && (
          <span style={{ marginLeft: 8 }}>CCI {lastCci.value.toFixed(1)}</span>
        )}
        {showOBV && lastObv != null && (
          <span style={{ marginLeft: 8 }}>OBV {lastObv.value.toLocaleString()}</span>
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
      {showRSI && rsiData.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>RSI</div>
          <div ref={rsiRef} style={{ width: '100%' }} />
        </div>
      )}
      {showBOLL && bollData.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>BOLL</div>
          <div ref={bollRef} style={{ width: '100%' }} />
        </div>
      )}
      {showCCI && cciData.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>CCI</div>
          <div ref={cciRef} style={{ width: '100%' }} />
        </div>
      )}
      {showOBV && obvData.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 2 }}>OBV</div>
          <div ref={obvRef} style={{ width: '100%' }} />
        </div>
      )}
    </div>
  );
}
