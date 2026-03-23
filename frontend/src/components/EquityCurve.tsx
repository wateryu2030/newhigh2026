'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';

/** 按日权益点（回测/实盘） */
export interface EquityPoint {
  date: string;
  value: number;
}

interface EquityCurveProps {
  /** 权益序列（按索引，Dashboard 用） */
  data?: number[];
  /** 按日权益点（回测结果用，优先于 data） */
  dataPoints?: EquityPoint[];
  height?: number;
  title?: string;
}

export function EquityCurve({ data, dataPoints, height = 280, title }: EquityCurveProps) {
  const { t } = useLang();
  const label = title ?? t('dashboard.equityCurve');

  const chartData = dataPoints?.length
    ? dataPoints.map((d) => ({ t: d.date, equity: d.value }))
    : (data ?? []).map((v, i) => ({ t: i, equity: v / 1e6 }));

  const isDateAxis = Boolean(dataPoints?.length);
  const yFormatter = isDateAxis
    ? (v: number) => `¥${v.toFixed(0)}`
    : (v: number) => `¥${v}M`;

  return (
    <div
      className="rounded-2xl p-5"
      style={{
        minHeight: height,
        backgroundColor: '#14171C',
        border: '1px solid #2A2E36',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <p className="mb-2 text-sm font-medium" style={{ color: '#A9ABB3', fontFamily: 'Space Grotesk' }}>{label}</p>
      <ResponsiveContainer width="100%" height={height - 40}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#45484F" />
          <XAxis
            dataKey="t"
            tick={{ fill: '#A9ABB3', fontSize: 10 }}
            tickFormatter={isDateAxis ? (v) => (typeof v === 'string' ? v.slice(0, 10) : String(v)) : undefined}
          />
          <YAxis tick={{ fill: '#A9ABB3', fontSize: 10 }} tickFormatter={yFormatter} />
          <Tooltip
            formatter={(v: number) => [v != null ? (isDateAxis ? `¥${(v as number).toFixed(2)}` : `¥${(v as number).toFixed(2)}M`) : '—', 'Equity']}
            contentStyle={{ backgroundColor: '#1C2028', border: 'none' }}
            labelFormatter={isDateAxis ? (v) => v : undefined}
          />
          <Line type="monotone" dataKey="equity" stroke="#FF3B30" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
