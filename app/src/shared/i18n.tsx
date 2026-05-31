import { createContext, useContext, useMemo, useState } from 'react';
import { en } from '../translations/en';
import { zh } from '../translations/zh';

export type Locale = 'zh' | 'en';

const resources = { zh, en };

type TranslationKey = keyof typeof zh;

type LanguageContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const saved = window.localStorage.getItem('voicebox.locale');
    return saved === 'en' ? 'en' : 'zh';
  });

  const value = useMemo<LanguageContextValue>(
    () => ({
      locale,
      setLocale: (next) => {
        window.localStorage.setItem('voicebox.locale', next);
        setLocale(next);
      },
      t: (key) => resources[locale][key] ?? resources.zh[key] ?? key,
    }),
    [locale],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useI18n() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useI18n must be used inside LanguageProvider');
  return context;
}
