'use client';

import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  sparklineData?: number[];
  positive?: boolean;
  sub?: string;
  className?: string;
}

export function KPICard({ title, value, change, sparklineData, positive, sub, className = '' }: KPICardProps) {
  const valueColor =
    positive === true ? '#FF3B30' : positive === false ? '#FF7439' : '#ECEDF6';
  const changeColor = change != null ? (change >= 0 ? '#22C55E' : '#FF3B30') : undefined;
  const chartData = (sparklineData ?? []).map((v, i) => ({ v, i }));

  return (
    <div
      className={`rounded-2xl p-5 transition-all duration-200 hover:scale-[1.02] ${className}`}
      style={{
        backgroundColor: '#14171C',
        border: '1px solid #2A2E36',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <p
        className="mb-1 text-xs font-medium uppercase tracking-wider"
        style={{ color: '#94A3B8', fontFamily: 'Space Grotesk' }}
      >
        {title}
      </p>
      <div className="flex items-baseline justify-between gap-2">
        <span
          className="text-2xl font-bold md:text-3xl"
          style={{ color: valueColor, fontFamily: 'Space Grotesk' }}
        >
          {value ?? '—'}
        </span>
        {change != null && (
          <span className="text-sm font-semibold" style={{ color: changeColor }}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
          </span>
        )}
      </div>
      {sub != null && (
        <p className="mt-1 text-xs" style={{ color: '#94A3B8' }}>
          {sub}
        </p>
      )}
      {chartData.length > 1 && (
        <div className="mt-3 h-8 w-full">
          <ResponsiveContainer width="100%" height={30}>
            <LineChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <Line
                type="monotone"
                dataKey="v"
                stroke="#FF3B30"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive
                animationDuration={500}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
