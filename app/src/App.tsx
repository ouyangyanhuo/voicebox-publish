import {
  AudioLines,
  BookOpen,
  Library,
  Moon,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Sun,
  Users,
} from 'lucide-react';
import { useState } from 'react';
import type { SectionId } from './shared/types';
import { useI18n } from './shared/i18n';
import { useTheme } from './shared/theme';
import { SingleGenerationPage } from './pages/SingleGenerationPage';
import { StoriesPage } from './pages/StoriesPage';
import { RolesPage } from './pages/RolesPage';
import { EmotionPage } from './pages/EmotionPage';
import { PresetVoicesPage } from './pages/PresetVoicesPage';
import { SettingsPage } from './pages/SettingsPage';
import { ModelDownloadToast } from './components/ModelDownloadToast';

const navItems = [
  { id: 'single', icon: AudioLines, labelKey: 'navSingle' },
  { id: 'stories', icon: BookOpen, labelKey: 'navStories' },
  { id: 'roles', icon: Users, labelKey: 'navRoles' },
  { id: 'emotion', icon: SlidersHorizontal, labelKey: 'navEmotion' },
  { id: 'presetVoices', icon: Library, labelKey: 'navPresetVoices' },
  { id: 'settings', icon: Settings, labelKey: 'navSettings' },
] as const;

export function App() {
  const [section, setSection] = useState<SectionId>('single');
  const { t, locale, setLocale } = useI18n();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={18} />
          </div>
          <div>
            <strong>{t('appName')}</strong>
            <span>IndexTTS2</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = item.id === section;
            return (
              <button
                key={item.id}
                className={active ? 'nav-item active' : 'nav-item'}
                onClick={() => setSection(item.id)}
              >
                <Icon size={18} />
                <span>{t(item.labelKey)}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            <span>{theme === 'dark' ? t('themeLight') : t('themeDark')}</span>
          </button>
          <label>{t('language')}</label>
          <div className="segmented">
            <button className={locale === 'zh' ? 'selected' : ''} onClick={() => setLocale('zh')}>
              中文
            </button>
            <button className={locale === 'en' ? 'selected' : ''} onClick={() => setLocale('en')}>
              EN
            </button>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        {section === 'single' && <SingleGenerationPage />}
        {section === 'stories' && <StoriesPage />}
        {section === 'roles' && <RolesPage />}
        {section === 'emotion' && <EmotionPage />}
        {section === 'presetVoices' && <PresetVoicesPage />}
        {section === 'settings' && <SettingsPage />}
      </main>
      <ModelDownloadToast />
    </div>
  );
}
