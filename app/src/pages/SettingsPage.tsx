import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { useI18n } from '../shared/i18n';

export function SettingsPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t('settingsTitle')} subtitle={t('settingsSubtitle')} />
      <div className="workspace two-column">
        <Panel title={t('modelSource')}>
          <div className="setting-row">
            <span>{t('modelSource')}</span>
            <strong>{t('modelScopeOnly')}</strong>
          </div>
          <label className="setting-row">
            <span>{t('githubMirror')}</span>
            <input type="checkbox" />
          </label>
          <p className="notice">{t('installLocal')}</p>
        </Panel>
        <Panel title={t('gpuMode')}>
          <label className="field">
            <span>{t('gpuMode')}</span>
            <select defaultValue="cpu">
              <option value="cpu">{t('cpuMode')}</option>
              <option value="cuda">{t('cudaMode')}</option>
            </select>
          </label>
        </Panel>
      </div>
    </>
  );
}
