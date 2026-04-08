'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/api/client';
import type { NewsItem } from '@/api/client';
import { useLang } from '@/context/LangContext';

type Panel = 'market' | 'collector';

function NewsList({
  news,
  emptyHint,
  goDataHref,
}: {
  news: NewsItem[];
  emptyHint: string;
  goDataHref?: boolean;
}) {
  const { t } = useLang();
  if (!news.length) {
    return (
      <div className="card border-[color:var(--color-warning-banner-border)] bg-card-bg/80">
        <p className="text-text-primary">{t('news.noNews')}</p>
        <p className="mt-2 text-sm text-text-dim">{emptyHint}</p>
        {goDataHref && (
          <>
            <ul className="mt-2 list-inside list-disc text-sm text-text-dim">
              <li>{t('news.hintCopyScript')}</li>
              <li>{t('news.hintDataPage')}</li>
            </ul>
            <a href="/data" className="mt-3 inline-block text-primary-fixed hover:underline">
              {t('news.goDataPage')} →
            </a>
          </>
        )}
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {news.map((item, i) => (
        <li key={item.url || `${item.title ?? ''}-${item.publish_time ?? ''}-${i}`} className="card list-none">
          {item.title && (
            <h3 className="font-medium text-on-surface">
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-fixed hover:underline"
                >
                  {item.title}
                </a>
              ) : (
                item.title
              )}
            </h3>
          )}
          <div className="mt-1 flex flex-wrap gap-2 text-sm text-text-secondary">
            {item.source && <span>{item.source}</span>}
            {item.publish_time && <span>{item.publish_time}</span>}
            {item.symbol && <span>{item.symbol}</span>}
            {item.sentiment_label && (
              <span
                className={
                  item.sentiment_score != null && item.sentiment_score < 0 ? 'text-accent-red' : 'text-text-secondary'
                }
              >
                {item.sentiment_label}
              </span>
            )}
          </div>
          {(item.keyword || item.tag) && (
            <div className="mt-1 flex flex-wrap gap-1 text-xs text-text-dim">
              {item.keyword && (
                <span className="rounded bg-surface-container-high px-1.5 py-0.5">{item.keyword}</span>
              )}
              {item.tag && (
                <span className="rounded bg-surface-container-highest px-1.5 py-0.5">{item.tag}</span>
              )}
            </div>
          )}
          {item.content && !/^[\d.\s\-]+$/.test((item.content || '').trim()) && (
            <p className="mt-2 line-clamp-4 text-sm text-text-secondary">{item.content}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function NewsPage() {
  const { t } = useLang();
  const [panel, setPanel] = useState<Panel>('market');
  const [query, setQuery] = useState('');
  const [news, setNews] = useState<NewsItem[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [sentiment, setSentiment] = useState<{ count: number; avg_score?: number; positive_ratio?: number } | null>(
    null
  );
  const [collectorDetail, setCollectorDetail] = useState<string | null>(null);
  const [newsDbTotal, setNewsDbTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  /** 避免 Tab 切换或重复请求时，晚返回的旧请求覆盖当前界面（例如政策 Tab 仍显示市场快讯）。 */
  const fetchSeq = useRef(0);

  const loadMarket = useCallback((symbol?: string) => {
    const seq = ++fetchSeq.current;
    setLoading(true);
    setCollectorDetail(null);
    api
      .news(symbol?.trim() || undefined, 100)
      .then((r) => {
        if (seq !== fetchSeq.current) return;
        setNews(r.news || []);
        setSource(r.source || null);
        setSentiment(r.sentiment ?? null);
        setNewsDbTotal(r.news_items_total ?? null);
      })
      .catch(() => {
        if (seq !== fetchSeq.current) return;
        setNews([]);
        setSource(null);
        setSentiment(null);
        setNewsDbTotal(null);
      })
      .finally(() => {
        if (seq === fetchSeq.current) setLoading(false);
      });
  }, []);

  const loadCollector = useCallback(() => {
    const seq = ++fetchSeq.current;
    setLoading(true);
    api
      .newsCollector(100)
      .then((r) => {
        if (seq !== fetchSeq.current) return;
        setNews(r.news || []);
        setSource(r.source || null);
        setSentiment(r.sentiment ?? null);
        setCollectorDetail(r.detail ?? null);
      })
      .catch(() => {
        if (seq !== fetchSeq.current) return;
        setNews([]);
        setSource(null);
        setSentiment(null);
        setCollectorDetail(null);
      })
      .finally(() => {
        if (seq === fetchSeq.current) setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (panel === 'market') loadMarket();
    else loadCollector();
  }, [panel, loadMarket, loadCollector]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-on-surface">{t('news.title')}</h1>

      <div className="flex flex-wrap gap-2 border-b border-card-border pb-3">
        <button
          type="button"
          onClick={() => setPanel('market')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            panel === 'market'
              ? 'bg-primary-fixed text-on-warm-fill'
              : 'bg-surface-container-high text-text-primary hover:bg-surface-container-highest'
          }`}
        >
          {t('news.tabMarket')}
        </button>
        <button
          type="button"
          onClick={() => setPanel('collector')}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            panel === 'collector'
              ? 'bg-primary-fixed text-on-warm-fill'
              : 'bg-surface-container-high text-text-primary hover:bg-surface-container-highest'
          }`}
        >
          {t('news.tabCollector')}
        </button>
      </div>

      {panel === 'collector' && <p className="max-w-3xl text-sm text-text-secondary">{t('news.collectorHint')}</p>}

      {panel === 'market' && <p className="text-sm text-text-secondary">{t('news.hint')}</p>}

      {panel === 'market' && (
        <div className="card max-w-2xl">
          <div className="flex flex-wrap gap-2 items-center">
            <input
              type="text"
              placeholder={t('news.placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadMarket(query)}
              className="w-56 rounded-lg border border-card-border bg-surface-container-high px-3 py-2 text-sm text-on-surface placeholder:text-text-dim"
            />
            <button
              type="button"
              onClick={() => loadMarket(query)}
              disabled={loading}
              className="rounded-lg bg-primary-fixed px-4 py-2 text-sm font-medium text-on-warm-fill hover:opacity-90 disabled:opacity-50"
            >
              {loading ? t('common.loading') : t('news.query')}
            </button>
            {sentiment != null && panel === 'market' && (
              <span className="ml-2 text-sm text-text-secondary">
                {t('news.count')} {sentiment.count}
                {t('news.unit')}
                {sentiment.avg_score != null && ` · ${t('news.sentimentAvg')} ${sentiment.avg_score}`}
                {sentiment.positive_ratio != null &&
                  ` · ${t('news.positivePct')} ${Math.round(sentiment.positive_ratio * 100)}%`}
              </span>
            )}
          </div>
        </div>
      )}

      {panel === 'collector' && sentiment != null && news.length > 0 && (
        <p className="text-sm text-text-dim">
          {t('news.count')} {sentiment.count}
          {t('news.unit')}
          {source && ` · ${t('news.dataSource')}：${source}`}
        </p>
      )}

      {panel === 'market' && source && (
        <p className="text-sm text-text-dim">
          {t('news.dataSource')}：{source}
          {newsDbTotal != null &&
            ` · ${t('news.dbTotalLine').replace(/\{n\}/g, newsDbTotal.toLocaleString())}`}
          {source === 'duckdb' && '（列表已按标题+时间去重，本页最多 100 条）'}
          {source === 'akshare' && `（${t('news.akshareHint')}）`}
        </p>
      )}

      {loading ? (
        <p className="text-text-dim">{t('common.loading')}</p>
      ) : panel === 'market' ? (
        <NewsList news={news} emptyHint={t('news.dataIncompleteHint')} goDataHref />
      ) : (
        <NewsList
          news={news}
          emptyHint={
            collectorDetail === 'policy_news_read_error'
              ? t('news.collectorReadError')
              : t('news.collectorEmpty')
          }
          goDataHref={false}
        />
      )}
    </div>
  );
}
