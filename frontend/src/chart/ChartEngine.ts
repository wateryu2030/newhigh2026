/**
 * TradingView 级图表引擎：基于 lightweight-charts 创建 K 线与系列。
 */
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';

export interface ChartOptions {
  width?: number;
  height?: number;
  layout?: { background?: string; textColor?: string };
}

export function createChartEngine(
  container: HTMLElement,
  options: ChartOptions = {}
): IChartApi {
  const chart = createChart(container, {
    layout: {
      background: { color: options.layout?.background ?? '#111827' },
      textColor: options.layout?.textColor ?? '#9ca3af',
    },
    grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
    width: options.width ?? container.offsetWidth,
    height: options.height ?? 400,
    timeScale: { borderColor: '#1f2937', timeVisible: true, secondsVisible: false },
    rightPriceScale: { borderColor: '#1f2937', scaleMargins: { top: 0.08, bottom: 0.2 } },
    crosshair: { mode: 1 },
  });
  return chart;
}

export function addCandlestickSeries(chart: IChartApi): ISeriesApi<'Candlestick'> {
  return chart.addCandlestickSeries({
    upColor: '#10b981',
    downColor: '#ef4444',
    borderVisible: false,
  });
}

export function addLineSeries(
  chart: IChartApi,
  options?: { color?: string; title?: string }
): ISeriesApi<'Line'> {
  return chart.addLineSeries({
    color: options?.color ?? '#3b82f6',
    title: options?.title,
  });
}

export type { IChartApi, ISeriesApi };
