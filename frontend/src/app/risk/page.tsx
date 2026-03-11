'use client';

import { useEffect, useState } from 'react';
import { api, type RiskResponse } from '@/api/client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';

const riskSeries = Array.from({ length: 30 }, (_, i) => ({ t: i, dd: 5 + Math.sin(i / 3) * 1.5, var_pct: 2 + Math.random() }));

export default function RiskPage() {
  const { t } = useLang();
  const [status, setStatus] = useState<RiskResponse | null>(null);
  useEffect(() => {
    api.risk().then(setStatus).catch(() => setStatus({ drawdown_ok: true, exposure_ok: true, volatility_ok: true }));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('risk.title')}</h1>
      <div className="grid-dashboard">
        <div className="card"><p className="text-sm text-slate-400">Max Drawdown</p><p className="text-2xl font-bold text-white">6.2%</p></div>
        <div className="card"><p className="text-sm text-slate-400">VaR</p><p className="text-2xl font-bold text-white">2.1%</p></div>
        <div className="card"><p className="text-sm text-slate-400">Exposure</p><p className="text-sm text-slate-300">Crypto 40% · Equity 30% · FX 30%</p></div>
      </div>
      <div className="card">
        <p className="mb-2 text-sm font-medium text-slate-400">Checks</p>
        <ul className="flex flex-wrap gap-4 text-sm">
          <li className={status?.drawdown_ok ? 'text-emerald-400' : 'text-red-400'}>Drawdown OK</li>
          <li className={status?.exposure_ok ? 'text-emerald-400' : 'text-red-400'}>Exposure OK</li>
          <li className={status?.volatility_ok ? 'text-emerald-400' : 'text-red-400'}>Volatility OK</li>
        </ul>
      </div>
      <div className="card">
        <p className="mb-4 text-sm font-medium text-slate-400">Risk over time (stub)</p>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={riskSeries} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <XAxis dataKey="t" tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
            <Line type="monotone" dataKey="dd" stroke="#f59e0b" strokeWidth={2} name="Drawdown %" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
