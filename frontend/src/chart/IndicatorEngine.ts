/**
 * 指标管线：MA、MACD 等，数据由后端 /api/kline?indicators=ma 提供，前端只渲染。
 */
export interface MaSeries {
  time: string;
  value: number;
}

export interface IndicatorResult {
  ma5?: MaSeries[];
  ma10?: MaSeries[];
  ma20?: MaSeries[];
}

export function normalizeTime(t: string): string {
  return String(t).slice(0, 10);
}

export function mapMaToLineData(ma: MaSeries[]): { time: string; value: number }[] {
  return ma.map((p) => ({ time: normalizeTime(p.time), value: p.value }));
}
