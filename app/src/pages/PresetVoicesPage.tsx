import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { useI18n } from '../shared/i18n';

export function PresetVoicesPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t('presetTitle')} subtitle={t('presetSubtitle')} />
      <div className="workspace">
        <Panel title={t('presetManifest')}>
          <code className="path-chip">preset-voices/manifest.json</code>
          <div className="empty-state">{t('emptyState')}</div>
        </Panel>
      </div>
    </>
  );
}
