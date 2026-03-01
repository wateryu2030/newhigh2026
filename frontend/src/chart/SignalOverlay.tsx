/**
 * 买卖点、策略信号叠加到 K 线系列。
 */
import type { ISeriesApi } from 'lightweight-charts';

export interface SignalPoint {
  date: string;
  type: 'BUY' | 'SELL' | 'HOLD';
  price?: number;
}

export function setSignalMarkers(
  series: ISeriesApi<'Candlestick'>,
  signals: SignalPoint[]
): void {
  const markers = signals.map((s) => {
    const time = s.date.slice(0, 10);
    if (s.type === 'HOLD') {
      return { time, position: 'aboveBar' as const, color: '#3b82f6', shape: 'circle' as const, text: 'HOLD' };
    }
    return {
      time,
      position: (s.type === 'BUY' ? 'belowBar' : 'aboveBar') as 'belowBar' | 'aboveBar',
      color: s.type === 'BUY' ? '#10b981' : '#ef4444',
      shape: (s.type === 'BUY' ? 'arrowUp' : 'arrowDown') as 'arrowUp' | 'arrowDown',
      text: s.type,
    };
  });
  if (markers.length) series.setMarkers(markers);
}
