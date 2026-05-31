import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { useI18n } from '../shared/i18n';

export function StoriesPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t('storyTitle')} subtitle={t('storySubtitle')} />
      <div className="workspace two-column wide-left">
        <Panel title={t('storyTitle')}>
          <div className="empty-state">{t('emptyState')}</div>
        </Panel>
        <Panel title={t('comingSoon')}>
          <div className="story-lines">
            <div className="line-placeholder" />
            <div className="line-placeholder short" />
            <div className="line-placeholder" />
          </div>
        </Panel>
      </div>
    </>
  );
}
