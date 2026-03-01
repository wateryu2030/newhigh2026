/**
 * 成交/持仓叠加：在图表上标出持仓成本线或成交点。
 */
import type { ISeriesApi } from 'lightweight-charts';

export interface TradePoint {
  time: string;
  price: number;
  side: 'BUY' | 'SELL';
  qty?: number;
}

export function setTradeMarkers(
  series: ISeriesApi<'Candlestick'>,
  trades: TradePoint[]
): void {
  const markers = trades.map((t) => ({
    time: t.time.slice(0, 10),
    position: (t.side === 'BUY' ? 'belowBar' : 'aboveBar') as 'belowBar' | 'aboveBar',
    color: t.side === 'BUY' ? '#10b981' : '#ef4444',
    shape: (t.side === 'BUY' ? 'arrowUp' : 'arrowDown') as 'arrowUp' | 'arrowDown',
    text: `${t.side} ${t.qty ?? ''}`,
  }));
  if (markers.length) series.setMarkers(markers);
}
