'use client';

import { useState, useEffect } from 'react';
import {
  RadarChart as RechartsRadar,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { Shareholder, Holding } from '@/data/mockShareholder';
import { getIndustryRadarData } from '@/data/mockShareholder';
import { INDUSTRIES } from '@/data/mockShareholder';
import { api } from '@/api/client';
import { rechartsTooltipContent, rechartsTooltipLabel, rechartsTickSecondary11, rechartsTickDim } from '@/lib/chartTheme';

interface CompareModalProps {
  open: boolean;
  onClose: () => void;
  shareholderA: Shareholder | null;
  shareholders: Shareholder[];
  holdingsA?: Holding[];
}

export function CompareModal({
  open,
  onClose,
  shareholderA,
  shareholders,
  holdingsA = [],
}: CompareModalProps) {
  const [queryB, setQueryB] = useState('');
  const [selectedB, setSelectedB] = useState<Shareholder | null>(null);
  const [holdingsB, setHoldingsB] = useState<Holding[]>([]);
  const [loadingB, setLoadingB] = useState(false);

  const matchesB = queryB.trim()
    ? shareholders.filter((s) =>
        s.name.toLowerCase().includes(queryB.trim().toLowerCase())
      )
    : [];

  useEffect(() => {
    if (!selectedB) {
      setHoldingsB([]);
      return;
    }
    setLoadingB(true);
    api
      .shareholderStrategy(selectedB.name)
      .then((res) => {
        if (res.ok && res.holdings) setHoldingsB(res.holdings);
        else setHoldingsB([]);
      })
      .catch(() => setHoldingsB([]))
      .finally(() => setLoadingB(false));
  }, [selectedB]);

  if (!open) return null;

  const radarA = getIndustryRadarData(holdingsA.length > 0 ? holdingsA : [], '2024Q1');
  const radarB = getIndustryRadarData(holdingsB, '2024Q1');
  const indicators = INDUSTRIES.slice(0, 6);
  const dataMapA = new Map(radarA.map((d) => [d.name, (d.value[0] + d.value[1]) / 2 || 0]));
  const dataMapB = new Map(radarB.map((d) => [d.name, (d.value[0] + d.value[1]) / 2 || 0]));
  const chartData = indicators.map((subject) => ({
    subject,
    A: dataMapA.get(subject) ?? 0,
    B: dataMapB.get(subject) ?? 0,
    fullMark: 100,
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[color:var(--color-overlay-scrim)] p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-xl border border-card-border bg-card-bg p-6 shadow-modal">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-on-surface">股东对比分析</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-2 text-text-secondary hover:bg-white/10 hover:text-on-surface"
          >
            ✕
          </button>
        </div>
        <div className="mb-4">
          <label className="mb-2 block text-sm text-text-secondary">
            输入第二个股东名称（从下方列表选择）
          </label>
          <input
            type="text"
            placeholder="如：高瓴投资"
            className="w-full rounded-lg border border-card-border bg-terminal-bg px-4 py-2 text-on-surface"
            value={queryB}
            onChange={(e) => setQueryB(e.target.value)}
          />
          {matchesB.length > 0 && (
            <ul className="mt-1 rounded border border-card-border bg-terminal-bg">
              {matchesB.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className="w-full px-4 py-2 text-left text-sm text-on-surface hover:bg-white/10"
                    onClick={() => {
                      setSelectedB(s);
                      setQueryB(s.name);
                    }}
                  >
                    {s.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <RechartsRadar data={chartData}>
              <PolarGrid stroke="var(--color-outline-variant)" />
              <PolarAngleAxis dataKey="subject" tick={rechartsTickSecondary11} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={rechartsTickDim} />
              <Radar
                name={shareholderA?.name ?? 'A'}
                dataKey="A"
                stroke="var(--color-primary)"
                fill="var(--color-primary)"
                fillOpacity={0.2}
                strokeWidth={2}
              />
              {selectedB && (
                <Radar
                  name={selectedB.name}
                  dataKey="B"
                  stroke="var(--color-chart-emerald)"
                  fill="var(--color-chart-emerald)"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              )}
              <Legend />
              <Tooltip contentStyle={rechartsTooltipContent} labelStyle={rechartsTooltipLabel} />
            </RechartsRadar>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
