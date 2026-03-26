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
        <h1 className="text-2xl font-bold text-white">{t('research.title')}</h1>
        <p className="mt-1 text-slate-400 text-sm">{t('research.subtitle')}</p>
      </div>

      <div className="card flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">{t('research.symbol')}</label>
          <input
            className="rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-white w-36"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="000001"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-slate-500 mb-1">{t('research.focus')}</label>
          <input
            className="rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-white w-full max-w-xl"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            placeholder={t('research.focusPh')}
          />
        </div>
        <button
          type="button"
          onClick={pullNews}
          disabled={loadingNews}
          className="rounded-lg bg-slate-600 hover:bg-slate-500 px-4 py-2 text-white text-sm disabled:opacity-50"
        >
          {loadingNews ? t('common.loading') : t('research.pullNews')}
        </button>
        <button
          type="button"
          onClick={generateSummary}
          disabled={loadingSummary}
          className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-white text-sm disabled:opacity-50"
        >
          {loadingSummary ? t('research.generating') : t('research.genSummary')}
        </button>
      </div>

      {err && (
        <div className="rounded-lg border border-amber-700/50 bg-amber-900/20 px-4 py-3 text-amber-200 text-sm">
          {err}
        </div>
      )}

      {summary && (
        <div className="card">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold text-white">{t('research.aiSummary')}</h2>
            {model && <span className="text-xs text-slate-500">model: {model}</span>}
          </div>
          <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap text-slate-200 leading-relaxed">
            {summary}
          </div>
        </div>
      )}

      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-2">
          {t('research.newsList')} {newsSource && <span className="text-slate-500 text-sm font-normal">({newsSource})</span>}
        </h2>
        {!news.length && !loadingNews ? (
          <p className="text-slate-500 text-sm">{t('research.pullHint')}</p>
        ) : (
          <ul className="space-y-3 max-h-[480px] overflow-y-auto text-sm">
            {news.map((n, i) => (
              <li key={n.url || `${n.title ?? ''}-${n.publish_time ?? ''}-${i}`} className="border-b border-slate-700/50 pb-3">
                <p className="text-white font-medium">
                  {n.url && /^https?:\/\//i.test(n.url.trim()) ? (
                    <a
                      href={n.url.trim()}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline text-indigo-300"
                    >
                      {n.title || '—'}
                    </a>
                  ) : (
                    n.title || '—'
                  )}
                </p>
                <p className="text-slate-500 text-xs mt-1">
                  {n.publish_time} {n.source ? `· ${n.source}` : ''}
                </p>
                {n.content ? (
                  <p className="text-slate-400 mt-1 line-clamp-3">{n.content}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="mt-4 text-xs text-slate-500 max-w-2xl">
        当前新闻源为站内东财链（与{' '}
        <a
          href="https://github.com/minsight-ai-info/AI-Search-Hub"
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-400 hover:underline"
        >
          AI-Search-Hub
        </a>{' '}
        所倡导的「多平台原生搜索」互补：抖音/公众号/X 等需扩展见{' '}
        <code className="text-slate-400">GET /api/news/coverage</code> 与仓库{' '}
        <code className="text-slate-400">docs/NEWS_SEARCH_AI_SEARCH_HUB.md</code>。
      </p>
      <p className="text-xs text-slate-600">{t('research.disclaimer')}</p>
    </div>
  );
}
