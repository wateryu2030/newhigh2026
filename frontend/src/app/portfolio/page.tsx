'use client';

import { useEffect, useState } from 'react';
import { api, type PortfolioResponse } from '@/api/client';
import { useLang } from '@/context/LangContext';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { EquityCurve } from '@/components/EquityCurve';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { EmptyState } from '@/components/EmptyState';
import { portfolioPieFills, rechartsTooltipContent } from '@/lib/chartTheme';

const ALLOC = [
  { name: 'Crypto', value: 40 },
  { name: 'Stocks', value: 35 },
  { name: 'FX', value: 25 },
];

export default function PortfolioPage() {
  const { t } = useLang();
  const [data, setData] = useState<PortfolioResponse | null>(null);
  const [equityCurve, setEquityCurve] = useState<{ date: string; value: number }[]>([]);
  const [equityLoading, setEquityLoading] = useState(true);
  useEffect(() => {
    api.portfolio().then(setData).catch(() => setData({ weights: {}, capital: 12_340_000 }));
  }, []);
  useEffect(() => {
    setEquityLoading(true);
    api
      .executionEquityCurve(200)
      .then((r) => setEquityCurve(r.equity_curve || []))
      .catch(() => setEquityCurve([]))
      .finally(() => setEquityLoading(false));
  }, []);

  const capital = data?.capital ?? 12_340_000;
  const formatMoney = (n: number) => (n >= 1e6 ? `¥${(n / 1e6).toFixed(1)}M` : `¥${n.toLocaleString()}`);

  return (
    <div className="min-h-screen space-y-6 pb-24 md:pb-6">
      <div className="card">
        <p className="text-sm text-text-secondary">{t('portfolio.totalAum')}</p>
        <p className="text-3xl font-bold text-on-surface">{formatMoney(capital)}</p>
      </div>
      <div className="card">
        <h2 className="mb-2 text-sm font-medium text-text-secondary">{t('dashboard.equityCurve')}（执行层）</h2>
        {equityLoading ? (
          <LoadingSpinner />
        ) : equityCurve.length > 0 ? (
          <EquityCurve dataPoints={equityCurve} height={260} title="" />
        ) : (
          <EmptyState title={t('portfolio.noEquityData') || '暂无资金曲线'} />
        )}
      </div>
      <div className="card">
        <p className="mb-4 text-sm font-medium text-text-secondary">{t('portfolio.allocation')}</p>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={ALLOC}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={90}
              label={({ name, value }) => `${name} ${value}%`}
            >
              {ALLOC.map((_, i) => (
                <Cell key={i} fill={portfolioPieFills[i]} />
              ))}
            </Pie>
            <Tooltip contentStyle={rechartsTooltipContent} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="card md:max-w-2xl">
        <h2 className="mb-2 text-sm font-medium text-text-secondary">{t('portfolio.positions')}</h2>
        <ul className="space-y-2 text-sm">
          <li className="flex justify-between">
            <span className="text-text-secondary">BTC</span>
            <span className="text-on-surface">—</span>
          </li>
          <li className="flex justify-between">
            <span className="text-text-secondary">ETH</span>
            <span className="text-on-surface">—</span>
          </li>
          <li className="flex justify-between">
            <span className="text-text-secondary">SPY</span>
            <span className="text-on-surface">—</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
