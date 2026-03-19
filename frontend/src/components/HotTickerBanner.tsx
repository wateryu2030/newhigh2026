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
        className="w-full py-1 text-center text-xs text-slate-500 hover:text-slate-400 border-b border-slate-800"
      >
        {t('hotTicker.show')}
      </button>
    );
  }

  if (!banner) {
    return null;
  }

  return (
    <div className="relative z-40 border-b border-amber-900/40 bg-gradient-to-r from-slate-950 via-amber-950/30 to-slate-950 shadow-lg shadow-amber-950/10">
      <div className="flex items-stretch">
        <div className="shrink-0 flex items-center gap-1.5 border-r border-amber-800/30 bg-amber-950/50 px-2 py-1.5 sm:px-3">
          <span className="text-amber-400 text-xs font-bold uppercase tracking-wider whitespace-nowrap">
            {t('hotTicker.label')}
          </span>
        </div>
        <div className="hot-ticker-mask min-w-0 flex-1 overflow-hidden py-1.5">
          <div className="hot-ticker-track flex w-max gap-16 items-center">
            <span className="whitespace-nowrap text-sm text-amber-100/95 tabular-nums">
              {banner}
              <span className="ml-8 text-slate-500 text-xs">{t('hotTicker.hint')}</span>
            </span>
            <span className="whitespace-nowrap text-sm text-amber-100/95 tabular-nums" aria-hidden>
              {banner}
              <span className="ml-8 text-slate-500 text-xs">{t('hotTicker.hint')}</span>
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setHidden(true)}
          className="shrink-0 px-2 text-slate-500 hover:text-slate-300 text-xs"
          aria-label="close"
        >
          ×
        </button>
      </div>
      {updated && (
        <p className="absolute right-10 bottom-0 text-[10px] text-slate-600 pointer-events-none hidden sm:block">
          {updated}
        </p>
      )}
    </div>
  );
}
