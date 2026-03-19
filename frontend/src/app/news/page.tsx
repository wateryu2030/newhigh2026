'use client';

import { useState, useEffect } from 'react';
import { api } from '@/api/client';
import type { NewsItem } from '@/api/client';
import { useLang } from '@/context/LangContext';

export default function NewsPage() {
  const { t } = useLang();
  const [query, setQuery] = useState('');
  const [news, setNews] = useState<NewsItem[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [sentiment, setSentiment] = useState<{ count: number; avg_score?: number; positive_ratio?: number } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = (symbol?: string) => {
    setLoading(true);
    api.news(symbol?.trim() || undefined, 100)
      .then((r) => {
        setNews(r.news || []);
        setSource(r.source || null);
        setSentiment(r.sentiment ?? null);
      })
      .catch(() => {
        setNews([]);
        setSource(null);
        setSentiment(null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">{t('news.title')}</h1>
      <p className="text-slate-400 text-sm">{t('news.hint')}</p>

      <div className="card max-w-2xl">
        <div className="flex flex-wrap gap-2 items-center">
          <input
            type="text"
            placeholder={t('news.placeholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && load(query)}
            className="rounded-lg bg-slate-700 border border-slate-600 px-3 py-2 text-sm text-white placeholder-slate-500 w-56"
          />
          <button
            type="button"
            onClick={() => load(query)}
            disabled={loading}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? t('common.loading') : t('news.query')}
          </button>
          {sentiment != null && (
            <span className="text-slate-400 text-sm ml-2">
              {t('news.count')} {sentiment.count}{t('news.unit')}
              {sentiment.avg_score != null && ` · ${t('news.sentimentAvg')} ${sentiment.avg_score}`}
              {sentiment.positive_ratio != null && ` · ${t('news.positivePct')} ${Math.round(sentiment.positive_ratio * 100)}%`}
            </span>
          )}
        </div>
      </div>

      {source && (
        <p className="text-slate-500 text-sm">
          {t('news.dataSource')}：{source}
          {source === 'duckdb' && '（列表已按标题+时间去重，仅展示最近 100 条；库内总条数见上方系统数据概览）'}
        </p>
      )}

      {loading ? (
        <p className="text-slate-500">{t('common.loading')}</p>
      ) : (
        <ul className="space-y-3">
          {news.map((item, i) => (
            <li key={item.url || `${item.title ?? ''}-${item.publish_time ?? ''}-${i}`} className="card list-none">
              {item.title && (
                <h3 className="font-medium text-white">
                  {item.url ? (
                    <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:underline text-indigo-300">
                      {item.title}
                    </a>
                  ) : (
                    item.title
                  )}
                </h3>
              )}
              <div className="mt-1 flex flex-wrap gap-2 text-sm text-slate-400">
                {item.source && <span>{item.source}</span>}
                {item.publish_time && <span>{item.publish_time}</span>}
                {item.symbol && <span>{item.symbol}</span>}
                {item.sentiment_label && (
                  <span className={item.sentiment_score != null && item.sentiment_score < 0 ? 'text-red-400' : 'text-slate-400'}>
                    {item.sentiment_label}
                  </span>
                )}
              </div>
                  {(item.keyword || item.tag) && (
                <div className="mt-1 flex flex-wrap gap-1 text-xs text-slate-500">
                  {item.keyword && <span className="rounded bg-slate-700 px-1.5 py-0.5">{item.keyword}</span>}
                  {item.tag && <span className="rounded bg-slate-600 px-1.5 py-0.5">{item.tag}</span>}
                </div>
              )}
              {item.content && !/^[\d.\s\-]+$/.test((item.content || '').trim()) && (
                <p className="mt-2 text-sm text-slate-400 line-clamp-4">{item.content}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {!loading && !news.length && (
        <div className="card border-amber-500/20 bg-slate-800/80">
          <p className="text-slate-300">{t('news.noNews')}</p>
          <p className="mt-2 text-sm text-slate-500">{t('news.dataIncompleteHint')}</p>
          <ul className="mt-2 list-inside list-disc text-sm text-slate-500">
            <li>{t('news.hintCopyScript')}</li>
            <li>{t('news.hintDataPage')}</li>
          </ul>
          <a href="/data" className="mt-3 inline-block text-indigo-400 hover:underline">{t('news.goDataPage')} →</a>
        </div>
      )}
    </div>
  );
}
