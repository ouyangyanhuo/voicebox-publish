import { useEffect, useMemo, useState } from 'react';
import { Square } from 'lucide-react';
import { useI18n } from '../shared/i18n';
import { useModelStatus } from '../shared/modelStatus';

const INACTIVE_TOAST_MS = 4500;

export function ModelDownloadToast() {
  const { t } = useI18n();
  const { modelStatus, modelError, stopDownload } = useModelStatus();
  const isActive = Boolean(modelStatus?.downloading);
  const toastKey = useMemo(
    () =>
      [
        modelStatus?.model_name,
        modelStatus?.message,
        modelError,
        modelStatus?.downloading,
        modelStatus?.downloaded,
        modelStatus?.cancel_requested,
      ].join('|'),
    [
      modelError,
      modelStatus?.cancel_requested,
      modelStatus?.downloaded,
      modelStatus?.downloading,
      modelStatus?.message,
      modelStatus?.model_name,
    ],
  );
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const hasContent = Boolean(modelStatus?.message || modelError || modelStatus?.downloading);
    if (!hasContent) {
      setVisible(false);
      return;
    }
    setVisible(true);
    if (isActive) return;

    const timer = window.setTimeout(() => {
      setVisible(false);
    }, INACTIVE_TOAST_MS);
    return () => window.clearTimeout(timer);
  }, [isActive, modelError, modelStatus?.downloading, modelStatus?.message, toastKey]);

  if (!visible || (!modelStatus?.message && !modelError && !modelStatus?.downloading)) return null;

  const statusText = modelStatus?.downloading
    ? t('modelDownloading')
    : modelStatus?.downloaded
      ? t('modelDownloaded')
      : t('modelMissing');
  const progress = Math.max(0, Math.min(modelStatus?.progress_percent ?? 0, 100));
  const fileProgress = Math.max(0, Math.min(modelStatus?.current_file_progress_percent ?? 0, 100));
  const hasFileProgress = typeof modelStatus?.total_files === 'number' && modelStatus.total_files > 0;
  const formatBytes = (value?: number | null) => {
    if (!value || value <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  };
  const progressText = hasFileProgress
    ? t('modelProgress')
        .replace('{completed}', String(modelStatus.completed_files ?? 0))
        .replace('{total}', String(modelStatus.total_files))
        .replace('{remaining}', String(modelStatus.remaining_files ?? 0))
        .replace('{downloadedBytes}', formatBytes(modelStatus.downloaded_bytes))
        .replace('{totalBytes}', formatBytes(modelStatus.total_bytes))
    : t('modelProgressPreparing');

  return (
    <div
      className={`toast ${
        modelError ? 'toast-failed' : modelStatus?.downloaded ? 'toast-completed' : 'toast-running'
      }`}
      role="status"
    >
      <strong>{statusText}</strong>
      <span>{modelError ?? modelStatus?.message ?? statusText}</span>
      {modelStatus?.current_file && <code className="toast-file">{modelStatus.current_file}</code>}
      {modelStatus?.downloading && (
        <>
          <button
            className="toast-stop-button"
            onClick={() => void stopDownload(modelStatus.model_name)}
            disabled={modelStatus.cancel_requested}
          >
            <Square size={14} />
            {t('modelStop')}
          </button>
          <div className="toast-progress-row">
            <span>{progressText}</span>
            <strong>{Math.round(progress)}%</strong>
          </div>
          <div className="toast-progress" aria-label={t('modelDownloading')}>
            <div className="toast-progress-bar" style={{ width: `${progress}%` }} />
          </div>
          {modelStatus.current_file && (
            <>
              <div className="toast-progress-row">
                <span>
                  {t('modelCurrentFileProgress')
                    .replace('{downloadedBytes}', formatBytes(modelStatus.current_file_bytes))
                    .replace('{totalBytes}', formatBytes(modelStatus.current_file_total_bytes))}
                </span>
                <strong>{Math.round(fileProgress)}%</strong>
              </div>
              <div className="toast-progress" aria-label={modelStatus.current_file}>
                <div className="toast-progress-bar" style={{ width: `${fileProgress}%` }} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
