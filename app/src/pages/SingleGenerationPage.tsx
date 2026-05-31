import { useState } from 'react';
import { EmotionVectorEditor } from '../components/EmotionVectorEditor';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { useI18n } from '../shared/i18n';
import type { EmotionVector } from '../shared/types';

export function SingleGenerationPage() {
  const { t } = useI18n();
  const [vector, setVector] = useState<EmotionVector>([0, 0, 0, 0, 0, 0, 0, 0]);

  return (
    <>
      <PageHeader title={t('singleTitle')} subtitle={t('singleSubtitle')} />
      <div className="workspace two-column">
        <Panel title={t('singleTitle')}>
          <label className="field">
            <span>{t('role')}</span>
            <select>
              <option>{t('emptyState')}</option>
            </select>
          </label>
          <label className="field">
            <span>{t('text')}</span>
            <textarea rows={8} placeholder={t('textPlaceholder')} />
          </label>
          <button className="primary-button">{t('generate')}</button>
          <p className="notice">{t('scaffoldNotice')}</p>
        </Panel>

        <Panel title={t('emotionControl')}>
          <label className="field">
            <span>{t('emotionAlpha')}</span>
            <input type="range" min="0" max="1" step="0.05" defaultValue="1" />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" />
            <span>{t('randomEmotion')}</span>
          </label>
          <EmotionVectorEditor value={vector} onChange={setVector} />
        </Panel>
      </div>
    </>
  );
}
