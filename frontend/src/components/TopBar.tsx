'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useLang } from '@/context/LangContext';
import { api } from '@/api/client';

interface TopBarProps {
  onMobileMenuClick?: () => void;
}

/** 顶部栏：红山量化平台 + 内联新闻滚动 + 语言切换（合并为单行，节约垂直空间） */
export function TopBar({ onMobileMenuClick }: TopBarProps) {
  const { t, lang, setLang } = useLang();
  const [banner, setBanner] = useState('');
  const [tickerHidden, setTickerHidden] = useState(false);

  useEffect(() => {
    const load = () => {
      api
        .hotTicker()
        .then((r) => setBanner(r.banner || ''))
        .catch(() => setBanner(''));
    };
    load();
    const id = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      className="fixed left-0 right-0 top-0 z-50 flex h-16 items-center gap-3 overflow-hidden px-4 md:px-6"
      style={{
        backgroundColor: '#0A0C10',
        borderBottom: '1px solid #2A2E36',
        fontFamily: 'Manrope',
      }}
    >
      <div className="flex shrink-0 items-center gap-3">
        {onMobileMenuClick && (
          <button
            type="button"
            onClick={onMobileMenuClick}
            className="flex md:hidden rounded-lg p-2 transition-colors hover:bg-card-border/50"
            style={{ color: '#94A3B8' }}
            aria-label="打开菜单"
          >
            <span className="material-symbols-outlined text-2xl">menu</span>
          </button>
        )}
        <Link href="/" className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
            style={{ backgroundColor: '#FF3B30' }}
            aria-hidden
          />
          <span
            className="shrink-0 text-lg font-bold tracking-tight md:text-xl"
            style={{ color: '#F1F5F9' }}
          >
            红山量化平台
          </span>
        </Link>
      </div>

      {/* 新闻滚动：紧接栏目名称之后，内联单行 */}
      {banner && (
        <>
          {tickerHidden ? (
            <button
              type="button"
              onClick={() => setTickerHidden(false)}
              className="shrink-0 rounded px-2 py-0.5 text-xs"
              style={{ color: '#FF3B30', backgroundColor: 'rgba(255,59,48,0.15)' }}
            >
              {t('hotTicker.label')}
            </button>
          ) : (
            <>
              <div className="hot-ticker-mask flex min-w-0 flex-1 items-center overflow-hidden py-1">
                <div className="hot-ticker-track flex w-max items-center gap-12">
                  <span
                    className="whitespace-nowrap text-sm tabular-nums"
                    style={{ color: '#ECEDF6' }}
                  >
                    {banner}
                  </span>
                  <span
                    className="whitespace-nowrap text-sm tabular-nums"
                    style={{ color: '#ECEDF6' }}
                    aria-hidden
                  >
                    {banner}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setTickerHidden(true)}
                className="shrink-0 px-1 text-sm"
                style={{ color: '#94A3B8' }}
                aria-label="关闭热点"
              >
                ×
              </button>
            </>
          )}
        </>
      )}

      <div className="flex shrink-0 items-center gap-2 md:gap-4">
        <button
          type="button"
          onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
          className="rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-card-border/50"
          style={{ color: '#94A3B8' }}
          title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
        >
          {t('lang.switch')}
        </button>
      </div>
    </header>
  );
}
