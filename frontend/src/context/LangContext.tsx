'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getStoredLang, setStoredLang, type Lang } from '@/lib/i18n';
import { translations } from '@/lib/i18n';

type LangContextValue = {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string) => string;
};

const LangContext = createContext<LangContextValue | null>(null);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>('zh');
  useEffect(() => {
    setLangState(getStoredLang());
  }, []);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    setStoredLang(l);
  }, []);
  const t = useCallback(
    (key: string) => translations[lang][key] ?? key,
    [lang]
  );
  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error('useLang must be used within LangProvider');
  return ctx;
}
