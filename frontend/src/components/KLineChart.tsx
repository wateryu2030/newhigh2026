import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import type { KlineBar } from '../types';

interface KLineChartProps {
  data: KlineBar[];
  signals?: { date: string; type: 'BUY' | 'SELL' | 'HOLD'; price: number }[];
  height?: number;
}

export default function KLineChart({ data, signals = [], height = 400 }: KLineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: '#111827' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: containerRef.current.offsetWidth,
      height,
      timeScale: { borderColor: '#1f2937', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.1, bottom: 0.2 } },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
    });
    candleRef.current = candleSeries;

    const tvData = data.map((b) => ({
      time: (b.time || b).toString().slice(0, 10) as string,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
    candleSeries.setData(tvData);

    if (data.some((b) => b.volume != null)) {
      const volSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      const volData = data
        .filter((b) => b.volume != null)
        .map((b) => ({
          time: (b.time || b).toString().slice(0, 10) as string,
          value: b.volume!,
          color: b.close >= b.open ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)',
        }));
      volSeries.setData(volData);
    }

    const markers = signals.map((s) => {
      if (s.type === 'HOLD') {
        return {
          time: s.date.slice(0, 10) as string,
          position: 'aboveBar' as const,
          color: '#3b82f6',
          shape: 'circle' as const,
          text: 'HOLD',
        };
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
      if (containerRef.current && chartRef.current)
        chartRef.current.applyOptions({ width: containerRef.current.offsetWidth });
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
    };
  }, [data, signals, height]);

  return <div ref={containerRef} style={{ width: '100%' }} />;
}
