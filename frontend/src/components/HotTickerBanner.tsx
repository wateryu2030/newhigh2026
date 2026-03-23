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
        className="w-full py-1 text-center text-xs"
        style={{ color: '#A9ABB3', backgroundColor: '#10131A' }}
      >
        {t('hotTicker.show')}
      </button>
    );
  }

  if (!banner) {
    return null;
  }

  return (
    <div className="relative z-40 backdrop-blur-sm" style={{ backgroundColor: 'rgba(16,19,26,0.95)' }}>
      <div className="flex items-stretch">
        <div className="flex shrink-0 items-center gap-1.5 px-2 py-1.5 sm:px-3" style={{ backgroundColor: '#1C2028' }}>
          <span className="whitespace-nowrap text-xs font-bold uppercase tracking-wider" style={{ color: '#FF3B30', fontFamily: 'Space Grotesk' }}>
            {t('hotTicker.label')}
          </span>
        </div>
        <div className="hot-ticker-mask min-w-0 flex-1 overflow-hidden py-1.5">
          <div className="hot-ticker-track flex w-max items-center gap-16">
            <span className="whitespace-nowrap text-sm tabular-nums" style={{ color: '#ECEDF6' }}>
              {banner}
              <span className="ml-8 text-xs" style={{ color: '#A9ABB3' }}>{t('hotTicker.hint')}</span>
            </span>
            <span className="whitespace-nowrap text-sm tabular-nums" style={{ color: '#ECEDF6' }} aria-hidden>
              {banner}
              <span className="ml-8 text-xs" style={{ color: '#A9ABB3' }}>{t('hotTicker.hint')}</span>
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setHidden(true)}
          className="shrink-0 px-2 text-xs"
          style={{ color: '#A9ABB3' }}
          aria-label="close"
        >
          ×
        </button>
      </div>
      {updated && (
        <p className="absolute right-10 bottom-0 hidden text-[10px] pointer-events-none sm:block" style={{ color: '#A9ABB3' }}>
          {updated}
        </p>
      )}
    </div>
  );
}
