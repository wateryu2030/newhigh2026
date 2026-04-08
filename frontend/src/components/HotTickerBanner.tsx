'use client';

import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { useLang } from '@/context/LangContext';

/** 全站顶部：东财热榜 + 快讯滚动播报 */
export function HotTickerBanner() {
  const { t } = useLang();
  const [banner, setBanner] = useState('');
  const [updated, setUpdated] = useState<string | null>(null);
  const [hidden, setHidden] = useState(false);

  const load = () => {
    api
      .hotTicker()
      .then((r) => {
        setBanner(r.banner || '');
        setUpdated(r.updated_at || null);
      })
      .catch(() => {
        setBanner('');
      });
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  if (hidden) {
    return (
      <button
        type="button"
        onClick={() => setHidden(false)}
        className="w-full bg-surface-container-low py-1 text-center text-xs text-on-surface-variant"
      >
        {t('hotTicker.show')}
      </button>
    );
  }

  if (!banner) {
    return null;
  }

  return (
    <div className="relative z-40 bg-[color:var(--color-hot-ticker-bar)] backdrop-blur-sm">
      <div className="flex items-stretch">
        <div className="flex shrink-0 items-center gap-1.5 bg-surface-container-high px-2 py-1.5 sm:px-3">
          <span className="font-label whitespace-nowrap text-xs font-bold uppercase tracking-wider text-primary-fixed">
            {t('hotTicker.label')}
          </span>
        </div>
        <div className="hot-ticker-mask min-w-0 flex-1 overflow-hidden py-1.5">
          <div className="hot-ticker-track flex w-max items-center gap-16">
            <span className="whitespace-nowrap text-sm tabular-nums text-on-surface">
              {banner}
              <span className="ml-8 text-xs text-on-surface-variant">{t('hotTicker.hint')}</span>
            </span>
            <span className="whitespace-nowrap text-sm tabular-nums text-on-surface" aria-hidden>
              {banner}
              <span className="ml-8 text-xs text-on-surface-variant">{t('hotTicker.hint')}</span>
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setHidden(true)}
          className="shrink-0 px-2 text-xs text-on-surface-variant"
          aria-label="close"
        >
          ×
        </button>
      </div>
      {updated && (
        <p className="pointer-events-none absolute right-10 bottom-0 hidden text-[10px] text-on-surface-variant sm:block">
          {updated}
        </p>
      )}
    </div>
  );
}
