'use client';

/**
 * AI 交易页面 - 使用全局 Layout（根 layout.tsx 已包裹）
 * 仅渲染核心内容，不包含侧边栏/系统状态重复模块
 */
import { useState, useEffect } from 'react';
import { api, type MarketEmotionResponse, type HotmoneySeatItem, type MainThemeItem, type TradeSignalItem, type SniperCandidateItem, type AiDecisionResponse, type SystemDataOverviewResponse } from '@/api/client';
import { SystemDataOverview } from '@/components/SystemDataOverview';
import { TradeSignalsTable } from '@/components/TradeSignalsTable';
import { SniperCandidatesTable } from '@/components/SniperCandidatesTable';
import { useLang } from '@/context/LangContext';

/** 统一卡片样式：与 shareholder-strategy 一致 */
const CARD_CLASS =
  'rounded-card bg-card-bg border border-card-border p-4 transition-all duration-200';

/** 板块/题材为占位：空或「未分类」视为无效展示 */
function isSectorPlaceholder(sector?: string | null) {
  const v = (sector ?? '').trim();
  return v === '' || v === '未分类';
}

function isThemePlaceholder(theme?: string | null) {
  const v = (theme ?? '').trim();
  return v === '' || v === '未分类';
}

export default function AITradingPage() {
  const { t } = useLang();
  const [emotion, setEmotion] = useState<MarketEmotionResponse | null>(null);
  const [hotmoney, setHotmoney] = useState<HotmoneySeatItem[]>([]);
  const [themes, setThemes] = useState<MainThemeItem[]>([]);
  const [signals, setSignals] = useState<TradeSignalItem[]>([]);
  const [sniper, setSniper] = useState<SniperCandidateItem[]>([]);
  const [decision, setDecision] = useState<AiDecisionResponse | null>(null);
  const [dataOverview, setDataOverview] = useState<SystemDataOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.systemDataOverview().catch(() => null).then((r) => { if (r?.ok) setDataOverview(r); return null; }),
      api.marketEmotion().catch((e) => { setError(e instanceof Error ? e.message : 'API 404'); return null; }),
      api.marketHotmoney(50).catch(() => []),
      api.marketMainThemes(10).catch(() => []),
      api.strategySignals(50).catch(() => []),
      api.sniperCandidates(50).catch(() => []),
      api.aiDecision().catch(() => null),
    ])
      .then(([, e, h, th, s, sn, dec]) => {
        if (e) setEmotion(e);
        setHotmoney(Array.isArray(h) ? h : []);
        setThemes(Array.isArray(th) ? th : []);
        setSignals(Array.isArray(s) ? s : []);
        // 游资狙击按 code 去重，保留同代码下分数最高的一条，避免重复展示
        const sniperList = Array.isArray(sn) ? sn : [];
        const byCode = new Map<string, SniperCandidateItem>();
        for (const row of sniperList) {
          const code = String(row?.code ?? '').trim();
          if (!code) continue;
          const cur = byCode.get(code);
          const score = Number(row?.sniper_score ?? 0);
          if (!cur || Number(cur.sniper_score ?? 0) < score) byCode.set(code, row);
        }
        setSniper(Array.from(byCode.values()));
        if (dec && typeof dec === 'object' && 'signal' in dec) setDecision(dec as AiDecisionResponse);
      })
      .finally(() => setLoading(false));
  }, []);

  /** 至少有一条真实板块名才展示主线题材表（否则为聚合占位，易误读） */
  const mainThemesEffective =
    themes.length > 0 && themes.some((r) => !isSectorPlaceholder(r.sector));
  /** 全部为未分类且 Sniper 分数完全一致 → 视为占位，不展示表格（仅展示真实数据） */
  const sniperScoresDistinct =
    sniper.length > 0 ? new Set(sniper.map((x) => Number(x.sniper_score).toFixed(4))).size : 0;
  const sniperAllPlaceholderTheme = sniper.length > 0 && sniper.every((r) => isThemePlaceholder(r.theme));
  const sniperEffective =
    sniper.length > 0 && !(sniperAllPlaceholderTheme && sniperScoresDistinct <= 1);

  /** 融合信号：全部同信号且同分数视为占位，不展示（仅展示真实数据） */
  const signalScoreDistinct =
    signals.length > 0 ? new Set(signals.map((x) => Number(x.signal_score ?? 0).toFixed(4))).size : 0;
  const signalTypeDistinct =
    signals.length > 0 ? new Set(signals.map((x) => String(x.signal ?? '').trim())).size : 0;
  const signalsEffective =
    signals.length > 0 &&
    (signalScoreDistinct >= 2 || signalTypeDistinct >= 2 || signals.some((s) => (s.strategy_id ?? '').trim() !== ''));

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-text-primary">{t('aiTrading.title')}</h1>
        <p className="text-text-secondary">{t('common.loading')}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen space-y-8 pb-24 md:pb-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">{t('aiTrading.title')}</h1>
        <p className="mt-1 text-sm text-text-secondary">{t('aiTrading.hint')}</p>
      </div>

      {/* 系统数据概览 - 核心 KPI 卡片 */}
      <SystemDataOverview />

      {error && (
        <div className="rounded-card border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
          <p className="font-medium">API 请求失败（404）</p>
          <p className="mt-1 text-text-secondary">请先启动 Gateway：在项目根目录执行</p>
          <code className="mt-2 block rounded bg-surface-container px-3 py-2 text-xs text-text-primary">uvicorn gateway.app:app --reload --host 0.0.0.0 --port 8000</code>
          <p className="mt-2 text-text-secondary">或安装依赖后：cd gateway && uv run uvicorn gateway.app:app --reload --port 8000</p>
        </div>
      )}

      {/* AI 决策解释 */}
      <section className={CARD_CLASS}>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">{t('aiTrading.decisionTitle')}</h2>
        {decision ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-text-secondary">{t('aiTrading.decisionSignal')}</span>
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
              <span className="mb-1 block text-sm text-text-secondary">{t('aiTrading.decisionReason')}</span>
              <p className="text-sm leading-relaxed text-text-secondary">{decision.reason}</p>
            </div>
            {decision.factors?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="mr-2 text-sm text-text-secondary">{t('aiTrading.decisionFactors')}</span>
                {decision.factors.map((f) => (
                  <span key={f} className="rounded bg-card-border px-2 py-0.5 text-xs text-text-secondary">
                    {f}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-text-secondary">{t('aiTrading.noData')} {t('aiTrading.noDataRunHint')}</p>
        )}
      </section>

      {/* 情绪周期 */}
      <section className={CARD_CLASS}>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">{t('aiTrading.emotion')}</h2>
        {emotion ? (
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <span className="text-text-secondary">{t('aiTrading.emotionState')}</span>
              <p className="font-medium text-text-primary">{emotion.stage ?? emotion.state ?? '—'}</p>
            </div>
            <div>
              <span className="text-text-secondary">{t('aiTrading.limitUpCount')}</span>
              <p className="font-medium text-text-primary">{emotion.limit_up_count ?? 0}</p>
            </div>
            <div>
              <span className="text-text-secondary">{t('aiTrading.maxHeight')}</span>
              <p className="font-medium text-text-primary">{(emotion as { max_height?: number }).max_height ?? 0}</p>
            </div>
            <div>
              <span className="text-text-secondary">{t('aiTrading.marketVolume')}</span>
              <p className="font-medium text-text-primary">
                {typeof (emotion as { market_volume?: number }).market_volume === 'number'
                  ? Number((emotion as { market_volume?: number }).market_volume).toLocaleString()
                  : '—'}
              </p>
            </div>
            {emotion.trade_date && (
              <div>
                <span className="text-text-secondary">{t('aiTrading.tradeDate')}</span>
                <p className="font-medium text-text-primary">{emotion.trade_date}</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-text-secondary">{t('aiTrading.noData')} {t('aiTrading.noDataRunHint')}</p>
        )}
      </section>

      {/* 游资席位 */}
      <section className={CARD_CLASS}>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">{t('aiTrading.hotmoney')}</h2>
        {hotmoney.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-card-border text-text-secondary">
                  <th className="py-2 pr-4">{t('aiTrading.seat')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.tradeCount')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.winRate')}</th>
                  <th className="py-2">{t('aiTrading.avgReturn')}</th>
                </tr>
              </thead>
              <tbody>
                {hotmoney.map((row, i) => (
                  <tr key={i} className="border-b border-card-border/50 hover:bg-card-border/30">
                    <td className="py-2 pr-4 font-mono text-text-secondary">{row.seat_name ?? '—'}</td>
                    <td className="py-2 pr-4 text-text-secondary">{row.trade_count ?? 0}</td>
                    <td className="py-2 pr-4 text-text-secondary">{typeof row.win_rate === 'number' ? (row.win_rate * 100).toFixed(1) + '%' : '—'}</td>
                    <td className="py-2 text-text-secondary">{typeof row.avg_return === 'number' ? (row.avg_return * 100).toFixed(2) + '%' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-text-secondary">{t('aiTrading.noData')} {t('aiTrading.noDataRunHint')}</p>
        )}
      </section>

      {/* 主线题材 */}
      <section className={CARD_CLASS}>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">{t('aiTrading.mainThemes')}</h2>
        {mainThemesEffective ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-card-border text-text-secondary">
                  <th className="py-2 pr-4">{t('aiTrading.rank')}</th>
                  <th className="py-2 pr-4">{t('aiTrading.sector')}</th>
                  <th className="py-2">{t('aiTrading.volume')}</th>
                </tr>
              </thead>
              <tbody>
                {themes
                  .filter((row) => !isSectorPlaceholder(row.sector))
                  .map((row, i) => (
                    <tr key={`${row.sector}-${row.rank ?? i}`} className="border-b border-card-border/50 hover:bg-card-border/30">
                      <td className="py-2 pr-4 text-text-secondary">{row.rank ?? i + 1}</td>
                      <td className="py-2 pr-4 font-medium text-text-primary">{row.sector ?? '—'}</td>
                      <td className="py-2 text-text-secondary">{typeof row.total_volume === 'number' ? row.total_volume.toLocaleString() : '—'}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : themes.length > 0 ? (
          <div className="space-y-2 text-sm text-text-secondary">
            <p className="text-amber-200/90 font-medium">{t('aiTrading.noEffectiveData')}</p>
            <p>{t('aiTrading.placeholderHiddenHint')}</p>
            <p>{t('aiTrading.dataIncompleteHint')}</p>
          </div>
        ) : (
          <p className="text-text-secondary">{t('aiTrading.noData')} {t('aiTrading.noDataRunHint')}</p>
        )}
      </section>

      {/* 游资狙击候选 */}
      <section className={CARD_CLASS}>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">{t('aiTrading.sniper')}</h2>
        {sniperEffective ? (
          <SniperCandidatesTable rows={sniper} />
        ) : sniper.length > 0 ? (
          <div className="space-y-2 text-sm text-text-secondary">
            <p className="text-amber-200/90 font-medium">{t('aiTrading.noEffectiveData')}</p>
            <p>{t('aiTrading.placeholderHiddenHint')}</p>
            <p>{t('aiTrading.sniperIncompleteHint')}</p>
            <p>{t('aiTrading.sniperNoDataHint')}</p>
          </div>
        ) : (
          <p className="text-text-secondary">{t('aiTrading.noData')} {t('aiTrading.sniperNoDataHint')}</p>
        )}
      </section>

      {/* 融合信号（仅展示真实数据：来自 trade_signals 表，无 stub） */}
      <section className={CARD_CLASS}>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">{t('aiTrading.signals')}</h2>
        {signalsEffective ? (
          <TradeSignalsTable rows={signals} />
        ) : signals.length > 0 ? (
          <div className="space-y-2 text-sm text-text-secondary">
            <p className="text-amber-200/90 font-medium">{t('aiTrading.noEffectiveData')}</p>
            <p>{t('aiTrading.placeholderHiddenHint')}</p>
            <p>{t('aiTrading.signalsNoDataHint')}</p>
          </div>
        ) : (
          <p className="text-text-secondary">{t('aiTrading.noData')} {t('aiTrading.signalsNoDataHint')}</p>
        )}
      </section>
    </div>
  );
}
