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
import { INDUSTRIES } from '@/data/mockShareholder';
import { rechartsTickSecondary, rechartsTickDim } from '@/lib/chartTheme';

export type IndustryRadarPoint = { name: string; value: number[] };

interface IndustryRadarChartProps {
  /** `getIndustryRadarData` 输出：value[0]=持仓市值占比(0–100)，value[1]=出现频次折算分 */
  data: IndustryRadarPoint[];
  height?: number;
}

/** 申万一级示例行业上的持仓分布雷达（与 mockShareholder.getIndustryRadarData 对齐） */
export function IndustryRadarChart({ data, height = 280 }: IndustryRadarChartProps) {
  const dataMap = new Map(data.map((d) => [d.name, d]));
  const chartData = INDUSTRIES.map((subject) => {
    const pt = dataMap.get(subject);
    const v0 = pt?.value[0] ?? 0;
    const v1 = pt?.value[1] ?? 0;
    const blended = (v0 + v1) / 2;
    return { subject, value: blended, fullMark: 100, valuePct: v0, freqScore: v1 };
  });

  const hasAny = chartData.some((d) => d.value > 0.5);

  if (!hasAny) {
    return (
      <div className="flex h-[200px] items-center justify-center text-sm text-text-dim">
        该报告期无持仓或行业数据为空，暂无行业分布雷达。
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsRadar data={chartData}>
        <PolarGrid stroke="var(--color-border)" />
        <PolarAngleAxis dataKey="subject" tick={rechartsTickSecondary} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={rechartsTickDim} />
        <Radar
          name="行业分布"
          dataKey="value"
          stroke="var(--color-primary)"
          fill="var(--color-primary)"
          fillOpacity={0.28}
          strokeWidth={2}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.[0]) return null;
            const p = payload[0].payload as { subject: string; valuePct: number; freqScore: number; value: number };
            return (
              <div className="rounded-lg border border-card-border bg-card-bg px-3 py-2 text-sm">
                <div className="font-medium text-text-primary">{p.subject}</div>
                <div className="text-text-secondary">市值占比 {p.valuePct.toFixed(1)}%</div>
                <div className="text-text-dim">
                  频次分 {p.freqScore.toFixed(0)} · 综合 {p.value.toFixed(1)}
                </div>
              </div>
            );
          }}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  );
}
