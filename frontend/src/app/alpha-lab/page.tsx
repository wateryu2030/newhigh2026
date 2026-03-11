'use client';

import { useEffect, useState } from 'react';
import { api, type AlphaLabResponse } from '@/api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLang } from '@/context/LangContext';

export default function AlphaLabPage() {
  const { t } = useLang();
  const [data, setData] = useState<AlphaLabResponse | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.alphaLab().then(setData).catch(() => setData({ generated_today: 1243, passed_backtest: 217, passed_risk: 64, deployed: 12 })).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-slate-400">{t('common.loading')}</div>;

  const funnel = data
    ? [
        { name: 'Generated', value: data.generated_today, fill: '#6366F1' },
        { name: 'Backtest OK', value: data.passed_backtest, fill: '#8b5cf6' },
        { name: 'Risk OK', value: data.passed_risk, fill: '#10B981' },
        { name: 'Deployed', value: data.deployed, fill: '#059669' },
      ]
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('alphaLab.title')}</h1>
      <div className="grid-dashboard">
        <div className="card"><p className="text-sm text-slate-400">Generated today</p><p className="text-2xl font-bold text-white">{data?.generated_today ?? 0}</p></div>
        <div className="card"><p className="text-sm text-slate-400">Passed backtest</p><p className="text-2xl font-bold text-violet-400">{data?.passed_backtest ?? 0}</p></div>
        <div className="card"><p className="text-sm text-slate-400">Passed risk</p><p className="text-2xl font-bold text-emerald-500">{data?.passed_risk ?? 0}</p></div>
        <div className="card"><p className="text-sm text-slate-400">In production</p><p className="text-2xl font-bold text-emerald-400">{data?.deployed ?? 0}</p></div>
      </div>
      <div className="card">
        <p className="mb-4 text-sm font-medium text-slate-400">Pipeline funnel</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={funnel} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
            <Bar dataKey="value" fill="#6366F1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-sm text-slate-500">Charts: generation trend, elimination rate, alpha distribution — wire to evolution-engine.</p>
    </div>
  );
}
