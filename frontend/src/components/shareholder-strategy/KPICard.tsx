'use client';

import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  sparklineData?: number[];
  className?: string;
}

/** 现代量化终端风格 KPI 卡片（与 dashboard/KPICard、DESIGN.md token 对齐） */
export function KPICard({ title, value, change, sparklineData, className = '' }: KPICardProps) {
  const changeTone =
    change != null ? (change >= 0 ? 'text-accent-green' : 'text-accent-red') : '';
  const chartData = (sparklineData ?? []).map((v, i) => ({ v, i }));

  return (
    <div
      className={`rounded-2xl border border-card-border bg-card-bg p-5 shadow-card transition-all duration-200 hover:shadow-lg hover:shadow-black/20 ${className}`}
    >
      <div className="mb-1 font-label text-xs font-medium uppercase tracking-wider text-text-secondary">
        {title}
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold text-text-primary md:text-3xl">{value}</span>
        {change != null && (
          <span className={`text-sm font-semibold ${changeTone}`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
          </span>
        )}
      </div>
      {chartData.length > 1 && (
        <div className="mt-3 h-8 w-full">
          <ResponsiveContainer width="100%" height={30}>
            <LineChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <Line
                type="monotone"
                dataKey="v"
                stroke="var(--color-primary)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={true}
                animationDuration={500}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
