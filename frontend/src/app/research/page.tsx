'use client';

import { useState } from 'react';
import { useLang } from '@/context/LangContext';
import { getApiBase } from '@/api/client';

type NewsItem = {
  title?: string;
  content?: string;
  publish_time?: string;
  source?: string;
  url?: string;
};

export default function ResearchPage() {
  const { t } = useLang();
  const [symbol, setSymbol] = useState('000001');
  const [focus, setFocus] = useState('');
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsSource, setNewsSource] = useState<string | null>(null);
  const [summary, setSummary] = useState('');
  const [model, setModel] = useState<string | null>(null);
  const [loadingNews, setLoadingNews] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const pullNews = async () => {
    setErr(null);
    setLoadingNews(true);
    try {
      const code = symbol.trim().split('.')[0] || '000001';
      const res = await fetch(
        `${getApiBase()}/api/news?symbol=${encodeURIComponent(code)}&limit=35`,
        { cache: 'no-store' }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setNews(data.news || []);
      setNewsSource(data.source || null);
    } catch (e) {
      setErr(String(e));
      setNews([]);
    } finally {
      setLoadingNews(false);
    }
  };

  const generateSummary = async () => {
    setErr(null);
    setLoadingSummary(true);
    setSummary('');
    setModel(null);
    try {
      const code = symbol.trim().split('.')[0] || '000001';
      const res = await fetch(`${getApiBase()}/api/research/news-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: code,
          limit: 30,
          focus: focus.trim() || undefined,
        }),
        cache: 'no-store',
      });
      const data = await res.json();
      if (!data.ok) {
        setErr(
          data.error === 'no_llm_key'
            ? t('research.noLlmKey')
            : data.error === 'no_news'
              ? t('research.noNews')
              : data.error || t('research.summaryFail')
        );
        return;
      }
      setSummary(data.summary || '');
      setModel(data.model || null);
      if (!news.length && data.news_count) {
        pullNews();
      }
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-on-surface">{t('research.title')}</h1>
        <p className="mt-1 text-sm text-text-secondary">{t('research.subtitle')}</p>
      </div>

      <div className="card flex flex-wrap items-end gap-4">
        <div>
          <label className="mb-1 block text-xs text-text-dim">{t('research.symbol')}</label>
          <input
            className="w-36 rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="000001"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="mb-1 block text-xs text-text-dim">{t('research.focus')}</label>
          <input
            className="w-full max-w-xl rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-on-surface"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            placeholder={t('research.focusPh')}
          />
        </div>
        <button
          type="button"
          onClick={pullNews}
          disabled={loadingNews}
          className="rounded-lg bg-surface-container-highest px-4 py-2 text-sm text-on-surface hover:opacity-90 disabled:opacity-50"
        >
          {loadingNews ? t('common.loading') : t('research.pullNews')}
        </button>
        <button
          type="button"
          onClick={generateSummary}
          disabled={loadingSummary}
          className="rounded-lg bg-primary-fixed px-4 py-2 text-sm text-on-warm-fill hover:opacity-90 disabled:opacity-50"
        >
          {loadingSummary ? t('research.generating') : t('research.genSummary')}
        </button>
      </div>

      {err && (
        <div className="rounded-lg border border-[color:var(--color-warning-banner-border)] bg-[color:var(--color-warning-banner-bg)] px-4 py-3 text-sm text-[color:var(--color-badge-amber-text)]">
          {err}
        </div>
      )}

      {summary && (
        <div className="card">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold text-on-surface">{t('research.aiSummary')}</h2>
            {model && <span className="text-xs text-text-dim">model: {model}</span>}
          </div>
          <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap leading-relaxed text-on-surface">
            {summary}
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="mb-2 text-lg font-semibold text-on-surface">
          {t('research.newsList')}{' '}
          {newsSource && <span className="text-sm font-normal text-text-dim">({newsSource})</span>}
        </h2>
        {!news.length && !loadingNews ? (
          <p className="text-sm text-text-dim">{t('research.pullHint')}</p>
        ) : (
          <ul className="space-y-3 max-h-[480px] overflow-y-auto text-sm">
            {news.map((n, i) => (
              <li
                key={n.url || `${n.title ?? ''}-${n.publish_time ?? ''}-${i}`}
                className="border-b border-card-border/80 pb-3"
              >
                <p className="font-medium text-on-surface">
                  {n.url && /^https?:\/\//i.test(n.url.trim()) ? (
                    <a
                      href={n.url.trim()}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-fixed hover:underline"
                    >
                      {n.title || '—'}
                    </a>
                  ) : (
                    n.title || '—'
                  )}
                </p>
                <p className="mt-1 text-xs text-text-dim">
                  {n.publish_time} {n.source ? `· ${n.source}` : ''}
                </p>
                {n.content ? (
                  <p className="mt-1 line-clamp-3 text-text-secondary">{n.content}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="mt-4 max-w-2xl text-xs text-text-dim">
        当前新闻源为站内东财链（与{' '}
        <a
          href="https://github.com/minsight-ai-info/AI-Search-Hub"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-fixed hover:underline"
        >
          AI-Search-Hub
        </a>{' '}
        所倡导的「多平台原生搜索」互补：抖音/公众号/X 等需扩展见{' '}
        <code className="text-text-secondary">GET /api/news/coverage</code> 与仓库{' '}
        <code className="text-text-secondary">docs/NEWS_SEARCH_AI_SEARCH_HUB.md</code>。
      </p>
      <p className="text-xs text-outline-variant">{t('research.disclaimer')}</p>
    </div>
  );
}
