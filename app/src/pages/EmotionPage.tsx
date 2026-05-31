import { useState } from 'react';
import { EmotionVectorEditor } from '../components/EmotionVectorEditor';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { useI18n } from '../shared/i18n';
import type { EmotionVector } from '../shared/types';

export function EmotionPage() {
  const { t } = useI18n();
  const [vector, setVector] = useState<EmotionVector>([0, 0, 0, 0, 0, 0, 0, 0]);
  return (
    <>
      <PageHeader title={t('emotionTitle')} subtitle={t('emotionSubtitle')} />
      <div className="workspace">
        <Panel title={t('emotionControl')}>
          <EmotionVectorEditor value={vector} onChange={setVector} />
        </Panel>
      </div>
    </>
  );
}
