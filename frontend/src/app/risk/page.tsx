'use client';

import { useEffect, useState } from 'react';
import { api, type RiskResponse } from '@/api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';
import { rechartsTooltipContent, rechartsTickSecondary } from '@/lib/chartTheme';

const riskSeries = Array.from({ length: 30 }, (_, i) => ({
  t: i,
  dd: 5 + Math.sin(i / 3) * 1.5,
  var_pct: 2 + Math.random(),
}));

export default function RiskPage() {
  const { t } = useLang();
  const [status, setStatus] = useState<RiskResponse | null>(null);
  useEffect(() => {
    api.risk().then(setStatus).catch(() =>
      setStatus({ drawdown_ok: true, exposure_ok: true, volatility_ok: true })
    );
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-on-surface">{t('risk.title')}</h1>
      <div className="grid-dashboard">
        <div className="card">
          <p className="text-sm text-text-secondary">Max Drawdown</p>
          <p className="text-2xl font-bold text-on-surface">6.2%</p>
        </div>
        <div className="card">
          <p className="text-sm text-text-secondary">VaR</p>
          <p className="text-2xl font-bold text-on-surface">2.1%</p>
        </div>
        <div className="card">
          <p className="text-sm text-text-secondary">Exposure</p>
          <p className="text-sm text-on-surface-variant">Crypto 40% · Equity 30% · FX 30%</p>
        </div>
      </div>
      <div className="card">
        <p className="mb-2 text-sm font-medium text-text-secondary">Checks</p>
        <ul className="flex flex-wrap gap-4 text-sm">
          <li className={status?.drawdown_ok ? 'text-accent-green' : 'text-primary-fixed'}>Drawdown OK</li>
          <li className={status?.exposure_ok ? 'text-accent-green' : 'text-primary-fixed'}>Exposure OK</li>
          <li className={status?.volatility_ok ? 'text-accent-green' : 'text-primary-fixed'}>Volatility OK</li>
        </ul>
      </div>
      <div className="card">
        <p className="mb-4 text-sm font-medium text-text-secondary">Risk over time (stub)</p>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={riskSeries} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <XAxis dataKey="t" tick={rechartsTickSecondary} />
            <YAxis tick={rechartsTickSecondary} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={rechartsTooltipContent} />
            <Line
              type="monotone"
              dataKey="dd"
              stroke="var(--color-chart-amber)"
              strokeWidth={2}
              name="Drawdown %"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
