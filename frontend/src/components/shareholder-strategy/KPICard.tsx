'use client';

import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  sparklineData?: number[];
  className?: string;
}

/** 现代量化终端风格 KPI 卡片：标题、大号数值、涨跌色、迷你折线图 */
export function KPICard({ title, value, change, sparklineData, className = '' }: KPICardProps) {
  const changeColor = change == null ? undefined : change >= 0 ? '#22C55E' : '#FF3B30';
  const chartData = (sparklineData ?? []).map((v, i) => ({ v, i }));

  return (
    <div
      className={`rounded-2xl p-5 transition-all duration-200 hover:shadow-lg hover:shadow-black/20 ${className}`}
      style={{
        backgroundColor: '#14171C',
        border: '1px solid #2A2E36',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <div className="mb-1 text-xs font-medium uppercase tracking-wider" style={{ color: '#94A3B8' }}>
        {title}
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold md:text-3xl" style={{ color: '#F1F5F9' }}>
          {value}
        </span>
        {change != null && (
          <span className="text-sm font-semibold" style={{ color: changeColor }}>
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
                stroke="#FF3B30"
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
