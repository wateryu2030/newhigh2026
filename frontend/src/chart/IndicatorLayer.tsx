/**
 * 指标层：MA 等由后端 /api/kline?indicators=ma 提供，本层负责绑定到 ChartEngine。
 */
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { mapMaToLineData } from './IndicatorEngine';

export interface MaSeries {
  time: string;
  value: number;
}

export function attachMaLines(
  chart: IChartApi,
  ma5: MaSeries[],
  ma10: MaSeries[],
  ma20: MaSeries[]
): ISeriesApi<'Line'>[] {
  const out: ISeriesApi<'Line'>[] = [];
  if (ma5.length) {
    const s5 = chart.addLineSeries({ color: '#f59e0b', title: 'MA5' });
    s5.setData(mapMaToLineData(ma5));
    out.push(s5);
  }
  if (ma10.length) {
    const s10 = chart.addLineSeries({ color: '#8b5cf6', title: 'MA10' });
    s10.setData(mapMaToLineData(ma10));
    out.push(s10);
  }
  if (ma20.length) {
    const s20 = chart.addLineSeries({ color: '#3b82f6', title: 'MA20' });
    s20.setData(mapMaToLineData(ma20));
    out.push(s20);
  }
  return out;
}
