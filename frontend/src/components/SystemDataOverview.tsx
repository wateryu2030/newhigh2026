'use client';

import { useEffect, useState } from 'react';
import { api, type SystemDataOverviewResponse } from '@/api/client';
import { useLang } from '@/context/LangContext';

interface DataCardProps {
  label: string;
  value: number | string;
  icon?: string;
  accent?: 'primary' | 'success' | 'warning' | 'danger';
}

function DataCard({ label, value, icon = '📊', accent = 'primary' }: DataCardProps) {
  const accentClasses = {
    primary: 'border-indigo-500/30 bg-indigo-500/10',
    success: 'border-emerald-500/30 bg-emerald-500/10',
    warning: 'border-amber-500/30 bg-amber-500/10',
    danger: 'border-rose-500/30 bg-rose-500/10',
  };

  return (
    <div className={`card border ${accentClasses[accent]} hover:border-${accent}-400/40 transition-colors`}>
      <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold text-white flex items-baseline gap-2">
        {icon && <span className="text-lg opacity-70">{icon}</span>}
        <span>{value}</span>
        <span className="text-xs text-slate-500">{String(value).length > 3 ? '条' : ''}</span>
      </p>
    </div>
  );
}

export function SystemDataOverview() {
  const { t } = useLang();
  const [data, setData] = useState<SystemDataOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.systemDataOverview()
      .then((res) => {
        if (res.ok) {
          setData(res);
        } else {
          setError(res.error || t('common.error'));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : t('common.error')))
      .finally(() => setLoading(false));
  }, [t]);

  if (loading) {
    return (
      <div className="card space-y-4">
        <h2 className="text-sm font-medium text-slate-400">📊 系统数据概览</h2>
        <div className="text-center text-slate-500 py-4">{t('common.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card border-rose-500/30 bg-rose-500/10">
        <h2 className="text-sm font-medium text-rose-400">📊 系统数据概览</h2>
        <p className="text-xs text-rose-200 mt-2">{t('common.error')}: {error}</p>
        <p className="text-xs text-rose-400/70 mt-1">
          {t('common.dataNotReady')}，请运行：
          <code className="block mt-2 bg-black/30 p-2 rounded text-[10px]">
            python scripts/ensure_market_data.py
          </code>
        </p>
      </div>
    );
  }

  const defaultCounts: SystemDataOverviewResponse['counts'] = {
    limitup_pool: 0, sniper_candidates: 0, trade_signals: 0, news_items: 0,
    stock_pool: 0, daily_bars: 0, longhubang: 0, fundflow: 0, emotion_state: null, hotmoney_seats: 0,
  };
  const counts = data?.counts ?? defaultCounts;

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-400">📊 系统数据概览</h2>
        <span className="text-xs text-slate-500 flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          最后更新: {new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <DataCard
          label={t('systemData.overview.limitupPool') || '涨停池'}
          value={counts.limitup_pool ?? 0}
          icon="🔥"
          accent="warning"
        />
        <DataCard
          label={t('systemData.overview.sniperCandidates') || '狙击候选'}
          value={counts.sniper_candidates ?? 0}
          icon="🎯"
          accent="primary"
        />
        <DataCard
          label={t('systemData.overview.tradeSignals') || '交易信号'}
          value={counts.trade_signals ?? 0}
          icon="📈"
          accent="success"
        />
        <DataCard
          label={t('systemData.overview.newsItems') || '新闻数据'}
          value={counts.news_items ?? 0}
          icon="📰"
          accent="primary"
        />
      </div>

      {/* Additional stats row */}
      {counts.stock_pool !== undefined && (
        <div className="border-t border-slate-700/50 pt-3 mt-2 grid grid-cols-3 sm:grid-cols-6 gap-3">
          <DataCard
            label="股票池"
            value={counts.stock_pool ?? 0}
            icon="(PHP)"
          />
          <DataCard
            label="日K线"
            value={counts.daily_bars ?? 0}
            icon="📅"
          />
          <DataCard
            label="龙虎榜"
            value={counts.longhubang ?? 0}
            icon="🏆"
          />
          <DataCard
            label="资金流"
            value={counts.fundflow ?? 0}
            icon="💧"
          />
          <DataCard
            label="游资席位"
            value={counts.hotmoney_seats ?? 0}
            icon="👨‍💼"
          />
          <DataCard
            label="情绪"
            value={counts.emotion_state || '—'}
            icon="📉"
          />
        </div>
      )}

      {/* Quick summary banner */}
      {counts.news_items !== undefined && counts.news_items > 15000 && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 mt-2">
          <p className="text-xs text-emerald-400 flex items-center gap-2">
            <span>✅</span>
            <span>
              📰 新闻数据充足（{counts.news_items.toLocaleString()} 条），
              ✅ 涨停池活跃（{counts.limitup_pool} 条），
              ✅ 狙击候选就绪（{counts.sniper_candidates} 条），
              ✅ 交易信号生成（{counts.trade_signals} 条）
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
