'use client';

import { useEffect, useState } from 'react';
import { useLang } from '@/context/LangContext';
import { API_BASE_STORAGE_KEY, getApiBase } from '@/api/client';

export default function SettingsPage() {
  const { t } = useLang();
  const [input, setInput] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem(API_BASE_STORAGE_KEY);
      setInput(v || '');
    } catch {
      setInput('');
    }
  }, []);

  const current = typeof window !== 'undefined' ? getApiBase() : '';

  const handleSave = () => {
    const v = input.trim();
    try {
      if (!v) {
        localStorage.removeItem(API_BASE_STORAGE_KEY);
      } else if (v.startsWith('http://') || v.startsWith('https://')) {
        localStorage.setItem(API_BASE_STORAGE_KEY, v.replace(/\/$/, ''));
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      window.location.reload();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-on-surface">{t('settings.title')}</h1>

      <div className="card max-w-2xl space-y-4">
        <div>
          <label className="block text-sm font-medium text-text-primary">{t('settings.apiGateway')}</label>
          <p className="mt-1 text-sm leading-relaxed text-text-dim">{t('settings.apiGatewayHint')}</p>
          <input
            className="mt-2 w-full rounded-lg border border-card-border bg-surface-container-high px-3 py-2 font-mono text-sm text-on-surface"
            placeholder="http://192.168.1.5:8000"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <p className="mt-1 text-xs text-outline-variant">
            {t('settings.currentEffective')}: <span className="text-text-secondary">{current}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleSave}
            className="rounded-lg bg-primary-fixed px-4 py-2 text-sm text-on-warm-fill hover:opacity-90"
          >
            {t('settings.saveApi')}
          </button>
          <button
            type="button"
            onClick={() => {
              setInput('');
              try {
                localStorage.removeItem(API_BASE_STORAGE_KEY);
                window.location.reload();
              } catch {
                /* ignore */
              }
            }}
            className="rounded-lg bg-surface-container-highest px-4 py-2 text-sm text-on-surface hover:opacity-90"
          >
            {t('settings.clearApi')}
          </button>
        </div>
        {saved && <p className="text-sm text-accent-green">{t('settings.savedReload')}</p>}

        <div className="space-y-2 border-t border-card-border pt-4 text-sm text-text-dim">
          <p className="font-medium text-text-secondary">{t('settings.lanSteps')}</p>
          <ol className="list-inside list-decimal space-y-1 text-text-secondary">
            <li>{t('settings.lanStep1')}</li>
            <li>{t('settings.lanStep2')}</li>
            <li>{t('settings.lanStep3')}</li>
          </ol>
        </div>
      </div>

      <div className="card max-w-xl">
        <label className="block text-sm font-medium text-text-secondary">Theme</label>
        <p className="mt-1 text-text-primary">Dark (default)</p>
      </div>
    </div>
  );
}
