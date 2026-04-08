'use client';

import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { ChangeRecord, Holding } from '@/data/mockShareholder';
import type { CoShareholderItem } from '@/api/client';
import { IndustryRadarChart, type IndustryRadarPoint } from './IndustryRadarChart';
import { rechartsTooltipContent, rechartsTickSecondary, rechartsCursorStroke } from '@/lib/chartTheme';

interface BubblePoint {
  value: [number, number, number];
  name: string;
  code: string;
}

interface ShareholderSidebarRightProps {
  radarData: IndustryRadarPoint[];
  bubbleData: BubblePoint[];
  holdings: Holding[];
  changes: ChangeRecord[];
  coShareholders: CoShareholderItem[];
  timeQuarter: string;
  highlightStock: string | null;
  onStockHover: (code: string | null) => void;
  onPanoramaStockClick?: (h: Holding) => void;
  onCoShareholderClick?: (name: string) => void;
}

/** 流动性视角气泡：X=最新收(元)，Y=log10(成交额·亿+ε)，点大小参考持仓估算市值(亿) */
function BubbleChart({ data }: { data: BubblePoint[] }) {
  const chartData = data.map((d) => ({
    x: d.value[0],
    y: d.value[1],
    z: Math.max(24, Math.min(120, 20 + (d.value[2] || 0) * 8)),
    name: d.name,
    code: d.code,
  }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ left: 20, right: 20, top: 20, bottom: 20 }}>
        <XAxis
          type="number"
          dataKey="x"
          name="收盘"
          tick={rechartsTickSecondary}
          label={{ value: '最新收(元)', position: 'bottom', fill: 'var(--color-text-dim)' }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="log成交额"
          tick={rechartsTickSecondary}
          label={{
            value: 'log10(日成交额·亿+0.01)',
            angle: -90,
            position: 'insideLeft',
            fill: 'var(--color-text-dim)',
          }}
        />
        <ZAxis type="number" dataKey="z" range={[50, 400]} />
        <Tooltip
          cursor={rechartsCursorStroke}
          contentStyle={rechartsTooltipContent}
          content={({ active, payload }) => {
            if (!active || !payload?.[0]?.payload) return null;
            const p = payload[0].payload as { x: number; y: number; z: number; name: string; code: string };
            return (
              <div className="rounded-lg border border-card-border bg-card-bg px-3 py-2 text-sm">
                <div className="font-medium text-on-surface">
                  {p.name} <span className="font-mono text-text-secondary">{p.code}</span>
                </div>
                <div className="text-text-secondary">
                  收: {p.x > 0 ? p.x.toFixed(3) : '—'} · Y: {p.y.toFixed(2)}
                </div>
              </div>
            );
          }}
        />
        <Scatter data={chartData} fill="var(--color-primary)" fillOpacity={0.8} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function ShareholderSidebarRight({
  radarData,
  bubbleData,
  holdings,
  changes,
  coShareholders,
  timeQuarter,
  highlightStock,
  onStockHover,
  onPanoramaStockClick,
  onCoShareholderClick,
}: ShareholderSidebarRightProps) {
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

  const hasBubbleSeries =
    bubbleData.length > 0 && bubbleData.some((b) => b.value[0] > 0 || b.value[1] > 0);

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="mb-2 text-sm font-semibold text-on-surface">行业分布（持仓市值 + 频次）</h3>
        <p className="mb-2 text-xs text-text-dim">基于当前报告期切片内持仓，与申万一级示例行业轴对齐（数据来自 Gateway，非演示脚本）。</p>
        <IndustryRadarChart data={radarData} height={280} />
      </div>

      <div className="card">
        <h3 className="mb-2 text-sm font-semibold text-on-surface">价格 · 成交额（气泡）</h3>
        <p className="mb-2 text-xs text-text-dim">
          X/Y 取自 a_stock_daily 最新一根 K 线（收盘价、成交额）；若库中无日线则点会叠在原点附近。
        </p>
        {hasBubbleSeries ? (
          <BubbleChart data={bubbleData} />
        ) : (
          <div className="flex h-[200px] items-center justify-center text-sm text-text-dim">
            暂无有效日线数据，无法绘制气泡图（请先回填 a_stock_daily）。
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card">
          <div className="text-xs text-text-secondary">持仓集中度</div>
          <div className="mt-1 text-xl font-bold text-on-surface">{concentration}%</div>
          <div className="mt-1 text-xs text-text-dim">前三大重仓（按估算市值）</div>
        </div>
        <div className="card">
          <div className="text-xs text-text-secondary">变动流水</div>
          <div className="mt-1 text-xl font-bold text-on-surface">{changes.length}</div>
          <div className="mt-1 text-xs text-text-dim">条（新进/增减持/退出，接口片段）</div>
        </div>
        <div className="card sm:col-span-1">
          <div className="text-xs text-text-secondary">协同股东（同榜 Top10）</div>
          <p className="mt-1 text-[11px] leading-snug text-outline-variant">
            与被查询股东出现在同一 <span className="text-text-dim">股票代码 + 报告日</span> 的前十股东榜中的其他股东，按共现次数排序。
          </p>
          {coShareholders.length === 0 ? (
            <div className="mt-2 text-sm text-text-dim">暂无或仅自身上榜</div>
          ) : (
            <ul className="mt-2 max-h-[140px] space-y-1.5 overflow-y-auto text-sm">
              {coShareholders.map((c) => (
                <li
                  key={c.name}
                  className="flex flex-wrap items-baseline gap-x-2 border-b border-card-border/40 pb-1.5 last:border-0"
                >
                  <button
                    type="button"
                    className="max-w-[11rem] truncate text-left font-medium text-[color:var(--color-data-cyan)] hover:underline"
                    title={c.name}
                    onClick={() => onCoShareholderClick?.(c.name)}
                  >
                    {c.name}
                  </button>
                  <span className="text-xs text-text-dim">{c.shareholder_type || '—'}</span>
                  <span className="ml-auto shrink-0 font-mono text-xs text-text-secondary">
                    同榜×{c.co_slot_count} · {c.co_stock_count}只
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="mb-1 text-sm font-semibold text-on-surface">持股全景</h3>
        <p className="mb-3 text-xs text-text-dim">点击标签查看 K 线与快讯（与行情 API 一致）</p>
        <div className="flex flex-wrap gap-2">
          {holdings.map((h) => {
            const isCurrent = h.status === 'current';
            const isHighlight = highlightStock === h.stockCode;
            const trail =
              h.exitQuarter
                ? `${h.firstEntry}建仓→${h.exitQuarter}清仓`
                : `${h.firstEntry}建仓→持有`;
            return (
              <button
                key={h.stockCode}
                type="button"
                className={`cursor-pointer rounded-lg px-3 py-2 text-left text-sm transition ${
                  isCurrent
                    ? 'bg-accent-red/20 text-on-surface'
                    : 'bg-surface-container-high/50 text-text-secondary'
                } ${isHighlight ? 'ring-2 ring-fund-indigo' : ''}`}
                onMouseEnter={() => onStockHover(h.stockCode)}
                onMouseLeave={() => onStockHover(null)}
                onClick={() => {
                  onStockHover(h.stockCode);
                  onPanoramaStockClick?.(h);
                }}
                title={trail}
              >
                <span className="font-medium text-on-surface/95">{h.stockName}</span>
                <span className="mt-0.5 block font-mono text-xs text-text-secondary">{h.stockCode}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
