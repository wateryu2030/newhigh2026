'use client';

import {
  RadarChart as RechartsRadar,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

const STRATEGY_DIMS = ['成长', '价值', '动量', '高频', '保守'];

interface StrategyRadarChartProps {
  /** 各维度得分 0-100，顺序：成长、价值、动量、高频、保守 */
  scores?: Record<string, number>;
  height?: number;
}

/** 股东策略风格雷达图：成长/价值/动量/高频/保守 */
export function StrategyRadarChart({ scores = {}, height = 280 }: StrategyRadarChartProps) {
  const data = STRATEGY_DIMS.map((name) => ({
    subject: name,
    value: scores[name] ?? 0,
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsRadar data={data}>
        <PolarGrid stroke="#2A2E36" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: '#94A3B8', fontSize: 11 }}
        />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748B' }} />
        <Radar
          name="策略得分"
          dataKey="value"
          stroke="#FF3B30"
          fill="#FF3B30"
          fillOpacity={0.3}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#14171C',
            border: '1px solid #2A2E36',
            borderRadius: 8,
          }}
          labelStyle={{ color: '#94A3B8' }}
          formatter={(value: number) => [value, '得分']}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  );
}
