'use client';

import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface MiniChartProps {
  data: number[];
  color?: string;
  height?: number;
  /** 无数据时显示提示 */
  emptyLabel?: string;
}

/**
 * 迷你 sparkline 折线图，用于 KPI 卡片等
 * 若无真实数据可标注「示例数据，待接入」
 */
export function MiniChart({
  data,
  color = '#FF3B30',
  height = 30,
  emptyLabel,
}: MiniChartProps) {
  const chartData = data.map((v, i) => ({ v, i }));

  if (chartData.length < 2) {
    return (
      <div
        className="flex items-center justify-center rounded text-[10px]"
        style={{ height, backgroundColor: '#0A0C10', color: '#64748B' }}
      >
        {emptyLabel ?? '—'}
      </div>
    );
  }

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
