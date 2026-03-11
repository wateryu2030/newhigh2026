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
    <div className="card" style={{ minHeight: height }}>
      <p className="mb-2 text-sm font-medium text-slate-400">{label}</p>
      <ResponsiveContainer width="100%" height={height - 40}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="t"
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            tickFormatter={isDateAxis ? (v) => (typeof v === 'string' ? v.slice(0, 10) : String(v)) : undefined}
          />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={yFormatter} />
          <Tooltip
            formatter={(v: number) => [v != null ? (isDateAxis ? `¥${(v as number).toFixed(2)}` : `¥${(v as number).toFixed(2)}M`) : '—', 'Equity']}
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
            labelFormatter={isDateAxis ? (v) => v : undefined}
          />
          <Line type="monotone" dataKey="equity" stroke="#10B981" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
