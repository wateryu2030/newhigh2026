'use client';

import {
  RadarChart as RechartsRadar,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { Holding } from '@/data/mockShareholder';
import { INDUSTRIES } from '@/data/mockShareholder';

interface RadarPoint {
  name: string;
  value: number[];
}

interface BubblePoint {
  value: [number, number, number];
  name: string;
}

interface ShareholderSidebarRightProps {
  radarData: RadarPoint[];
  bubbleData: BubblePoint[];
  holdings: Holding[];
  timeQuarter: string;
  highlightStock: string | null;
  onStockHover: (code: string | null) => void;
}

/** 行业偏好雷达图 */
function RadarChart({ data }: { data: RadarPoint[] }) {
  const indicators = INDUSTRIES.slice(0, 6);
  const dataMap = new Map(data.map((d) => [d.name, (d.value[0] + d.value[1]) / 2 || 0]));
  const chartData = indicators.map((subject) => ({
    subject,
    value: dataMap.get(subject) ?? 0,
    fullMark: 100,
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <RechartsRadar data={chartData}>
        <PolarGrid stroke="#475569" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b' }} />
        <Radar
          name="持仓市值占比+出现频次"
          dataKey="value"
          stroke="#FF3B30"
          fill="#FF3B30"
          fillOpacity={0.3}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
          labelStyle={{ color: '#94a3b8' }}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  );
}

/** 市值-估值气泡图 */
function BubbleChart({ data }: { data: BubblePoint[] }) {
  const chartData = data.map((d) => ({
    x: d.value[0],
    y: d.value[1],
    z: Math.max(20, Math.min(80, d.value[2] * 2)),
    name: d.name,
  }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ left: 20, right: 20, top: 20, bottom: 20 }}>
        <XAxis
          type="number"
          dataKey="x"
          name="PE"
          tick={{ fill: '#94a3b8', fontSize: 10 }}
          label={{ value: '市盈率(PE)', position: 'bottom', fill: '#64748b' }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="log(市值)"
          tick={{ fill: '#94a3b8', fontSize: 10 }}
          label={{ value: 'log(市值)', angle: -90, position: 'insideLeft', fill: '#64748b' }}
        />
        <ZAxis type="number" dataKey="z" range={[50, 400]} />
        <Tooltip
          cursor={{ strokeDasharray: '3 3', stroke: '#475569' }}
          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: 8 }}
          content={({ active, payload }) => {
            if (!active || !payload?.[0]?.payload) return null;
            const p = payload[0].payload as { x: number; y: number; z: number; name: string };
            return (
              <div className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm">
                <div className="font-medium text-white">{p.name}</div>
                <div className="text-slate-400">PE: {p.x} · log(市值): {p.y.toFixed(1)}</div>
              </div>
            );
          }}
        />
        <Scatter data={chartData} fill="#FF3B30" fillOpacity={0.8} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function ShareholderSidebarRight({
  radarData,
  bubbleData,
  holdings,
  timeQuarter,
  highlightStock,
  onStockHover,
}: ShareholderSidebarRightProps) {
  /** 持仓集中度：前三大占比 */
  const top3 = holdings
    .filter((h) => {
      const exit = h.exitQuarter ?? '9999Q4';
      return h.firstEntry <= timeQuarter && exit >= timeQuarter;
    })
    .sort((a, b) => b.holdValue - a.holdValue)
    .slice(0, 3);
  const totalValue = holdings
    .filter((h) => {
      const exit = h.exitQuarter ?? '9999Q4';
      return h.firstEntry <= timeQuarter && exit >= timeQuarter;
    })
    .reduce((s, h) => s + h.holdValue, 0);
  const concentration =
    totalValue > 0
      ? ((top3.reduce((s, h) => s + h.holdValue, 0) / totalValue) * 100).toFixed(1)
      : '0';

  return (
    <div className="space-y-4">
      {/* 行业偏好雷达图 */}
      <div className="card">
        <h3 className="mb-2 text-sm font-semibold text-white">行业偏好</h3>
        <RadarChart data={radarData} />
      </div>

      {/* 市值-估值气泡图 */}
      <div className="card">
        <h3 className="mb-2 text-sm font-semibold text-white">市值-估值分布</h3>
        <BubbleChart data={bubbleData} />
      </div>

      {/* 操作风格卡片 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card">
          <div className="text-xs text-slate-400">持仓集中度</div>
          <div className="mt-1 text-xl font-bold text-white">{concentration}%</div>
          <div className="mt-1 text-xs text-slate-500">前三大重仓</div>
        </div>
        <div className="card">
          <div className="text-xs text-slate-400">调仓频率</div>
          <div className="mt-1 text-xl font-bold text-white">32%</div>
          <div className="mt-1 text-xs text-slate-500">近一年季度调仓占比</div>
        </div>
        <div className="card">
          <div className="text-xs text-slate-400">常见协同股东</div>
          <div className="mt-1 text-sm text-white">香港中央结算、社保一一三</div>
        </div>
      </div>

      {/* 持股全景网格 */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold text-white">持股全景</h3>
        <div className="flex flex-wrap gap-2">
          {holdings.map((h) => {
            const isCurrent = h.status === 'current';
            const isHighlight = highlightStock === h.stockCode;
            const trail =
              h.exitQuarter
                ? `${h.firstEntry}建仓→${h.exitQuarter}清仓`
                : `${h.firstEntry}建仓→持有`;
            return (
              <div
                key={h.stockCode}
                className={`cursor-pointer rounded-lg px-3 py-2 text-sm transition ${
                  isCurrent
                    ? 'bg-red-500/30 text-red-200'
                    : 'bg-slate-600/50 text-slate-400'
                } ${isHighlight ? 'ring-2 ring-fund-indigo' : ''}`}
                onMouseEnter={() => onStockHover(h.stockCode)}
                onMouseLeave={() => onStockHover(null)}
                title={trail}
              >
                {h.stockName}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
