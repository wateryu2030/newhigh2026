'use client';

import { useState, useEffect } from 'react';
import { api, type MarketEmotionResponse, type HotmoneySeatItem, type MainThemeItem, type TradeSignalItem, type SniperCandidateItem, type AiDecisionResponse } from '@/api/client';
import { useLang } from '@/context/LangContext';

export default function AITradingPage() {
  const { t } = useLang();
  const [emotion, setEmotion] = useState<MarketEmotionResponse | null>(null);
  const [hotmoney, setHotmoney] = useState<HotmoneySeatItem[]>([]);
  const [themes, setThemes] = useState<MainThemeItem[]>([]);
  const [signals, setSignals] = useState<TradeSignalItem[]>([]);
  const [sniper, setSniper] = useState<SniperCandidateItem[]>([]);
  const [decision, setDecision] = useState<AiDecisionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.marketEmotion().catch((e) => { setError(e instanceof Error ? e.message : 'API 404'); return null; }),
      api.marketHotmoney(50).catch(() => []),
      api.marketMainThemes(10).catch(() => []),
      api.strategySignals(50).catch(() => []),
      api.sniperCandidates(50).catch(() => []),
      api.aiDecision().catch(() => null),
    ])
      .then(([e, h, th, s, sn, dec]) => {
        if (e) setEmotion(e);
        setHotmoney(Array.isArray(h) ? h : []);
        setThemes(Array.isArray(th) ? th : []);
        setSignals(Array.isArray(s) ? s : []);
        setSniper(Array.isArray(sn) ? sn : []);
        if (dec && typeof dec === 'object' && 'signal' in dec) setDecision(dec as AiDecisionResponse);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">{t('aiTrading.title')}</h1>
        <p className="text-slate-500">{t('common.loading')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 min-h-screen pb-24 md:pb-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{t('aiTrading.title')}</h1>
        <p className="text-slate-400 text-sm mt-1">{t('aiTrading.hint')}</p>
      </div>
      {error && (
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm p-4">
          <p className="font-medium">API 请求失败（404）</p>
          <p className="mt-1 text-slate-400">请先启动 Gateway：在项目根目录执行</p>
          <code className="mt-2 block bg-slate-800 px-3 py-2 rounded text-xs">uvicorn gateway.app:app --reload --host 0.0.0.0 --port 8000</code>
          <p className="mt-2 text-slate-500">或安装依赖后：cd gateway && uv run uvicorn gateway.app:app --reload --port 8000</p>
        </div>
      )}

      {/* AI 决策解释 */}
      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-4">{t('aiTrading.decisionTitle')}</h2>
        {decision ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-slate-500 text-sm">{t('aiTrading.decisionSignal')}</span>
              <span
                className={`rounded px-3 py-1 text-sm font-medium ${
                  decision.signal === 'BUY'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : decision.signal === 'SELL'
                    ? 'bg-rose-500/20 text-rose-400'
                    : 'bg-slate-500/20 text-slate-300'
                }`}
              >
                {decision.signal}
              </span>
            </div>
            <div>
              <span className="text-slate-500 text-sm block mb-1">{t('aiTrading.decisionReason')}</span>
              <p className="text-slate-200 text-sm leading-relaxed">{decision.reason}</p>
            </div>
            {decision.factors?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-slate-500 text-sm mr-2">{t('aiTrading.decisionFactors')}</span>
                {decision.factors.map((f) => (
                  <span key={f} className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                    {f}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-slate-500">{t('aiTrading.noData')}</p>
        )}
      </section>

      {/* 情绪周期 */}
      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-4">{t('aiTrading.emotion')}</h2>
        {emotion ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-500">{t('aiTrading.emotionState')}</span>
              <p className="text-white font-medium">{emotion.stage ?? emotion.state ?? '—'}</p>
            </div>
            <div>
              <span className="text-slate-500">{t('aiTrading.limitUpCount')}</span>
              <p className="text-white font-medium">{emotion.limit_up_count ?? 0}</p>
            </div>
            <div>
              <span className="text-slate-500">{t('aiTrading.maxHeight')}</span>
              <p className="text-white font-medium">{(emotion as { max_height?: number }).max_height ?? 0}</p>
            </div>
            <div>
              <span className="text-slate-500">{t('aiTrading.marketVolume')}</span>
              <p className="text-white font-medium">
                {typeof (emotion as { market_volume?: number }).market_volume === 'number'
                  ? Number((emotion as { market_volume?: number }).market_volume).toLocaleString()
                  : '—'}
              </p>
            </div>
            {emotion.trade_date && (
              <div>
                <span className="text-slate-500">{t('aiTrading.tradeDate')}</span>
                <p className="text-white font-medium">{emotion.trade_date}</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-slate-500">{t('aiTrading.noData')}</p>
        )}
      </section>

      {/* 游资席位 */}
      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-4">{t('aiTrading.hotmoney')}</h2>
        {hotmoney.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-slate-400 border-b border-slate-600">
                  <th className="py-2 pr-4">{t('aiTrading.seat')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.tradeCount')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.winRate')}</th>
                  <th className="py-2">{t('aiTrading.avgReturn')}</th>
                </tr>
              </thead>
              <tbody>
                {hotmoney.map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 font-mono text-slate-300">{row.seat_name ?? '—'}</td>
                    <td className="py-2 pr-4 text-slate-300">{row.trade_count ?? 0}</td>
                    <td className="py-2 pr-4 text-slate-300">{typeof row.win_rate === 'number' ? (row.win_rate * 100).toFixed(1) + '%' : '—'}</td>
                    <td className="py-2 text-slate-300">{typeof row.avg_return === 'number' ? (row.avg_return * 100).toFixed(2) + '%' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500">{t('aiTrading.noData')}</p>
        )}
      </section>

      {/* 主线题材 */}
      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-4">{t('aiTrading.mainThemes')}</h2>
        {themes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-slate-400 border-b border-slate-600">
                  <th className="py-2 pr-4">{t('aiTrading.rank')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.sector')}</th>
                  <th className="py-2">{t('aiTrading.volume')}</th>
                </tr>
              </thead>
              <tbody>
                {themes.map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 text-slate-300">{row.rank ?? i + 1}</td>
                    <td className="py-2 pr-4 text-white font-medium">{row.sector ?? '—'}</td>
                    <td className="py-2 text-slate-300">{typeof row.total_volume === 'number' ? row.total_volume.toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500">{t('aiTrading.noData')}</p>
        )}
      </section>

      {/* 游资狙击候选 */}
      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-4">{t('aiTrading.sniper')}</h2>
        {sniper.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-slate-400 border-b border-slate-600">
                  <th className="py-2 pr-4">{t('market.code')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.theme')}</th>
                  <th className="py-2 pr-4">Sniper Score</th>
                  <th className="py-2">{t('aiTrading.confidence')}</th>
                </tr>
              </thead>
              <tbody>
                {sniper.map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 font-mono text-slate-300">{row.code}</td>
                    <td className="py-2 pr-4 text-white font-medium">{row.theme ?? '—'}</td>
                    <td className="py-2 pr-4 text-amber-400 font-medium">{row.sniper_score != null ? (Number(row.sniper_score) * 100).toFixed(1) + '%' : '—'}</td>
                    <td className="py-2 text-slate-300">{row.confidence != null ? (Number(row.confidence) * 100).toFixed(1) + '%' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500">{t('aiTrading.noData')}</p>
        )}
      </section>

      {/* 融合信号 */}
      <section className="card">
        <h2 className="text-lg font-semibold text-white mb-4">{t('aiTrading.signals')}</h2>
        {signals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-slate-400 border-b border-slate-600">
                  <th className="py-2 pr-4">{t('market.code')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.signalScore')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.confidence')}</th>
                  <th className="py-2 pr-4">Signal</th>
                  <th className="py-2">Strategy</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 font-mono text-slate-300">{row.code}</td>
                    <td className="py-2 pr-4 text-white font-medium">{row.signal_score != null ? (Number(row.signal_score) * 100).toFixed(1) + '%' : '—'}</td>
                    <td className="py-2 pr-4 text-slate-300">{row.confidence != null ? (Number(row.confidence) * 100).toFixed(1) + '%' : '—'}</td>
                    <td className="py-2 pr-4 text-slate-300">{row.signal ?? 'BUY'}</td>
                    <td className="py-2 text-slate-500">{row.strategy_id ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500">{t('aiTrading.noData')}</p>
        )}
      </section>
    </div>
  );
}
