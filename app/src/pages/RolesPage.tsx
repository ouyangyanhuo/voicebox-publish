import { Plus } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { useI18n } from '../shared/i18n';

export function RolesPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t('rolesTitle')} subtitle={t('rolesSubtitle')} />
      <div className="workspace">
        <Panel
          title={t('rolesTitle')}
          actions={
            <button className="toolbar-button">
              <Plus size={16} />
              {t('createRole')}
            </button>
          }
        >
          <div className="card-grid">
            <div className="empty-card">{t('emptyState')}</div>
          </div>
        </Panel>
      </div>
    </>
  );
}
