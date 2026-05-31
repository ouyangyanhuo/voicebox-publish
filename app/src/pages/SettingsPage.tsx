import { Download, FolderOpen, HardDrive, RefreshCw, Square, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { Select } from '../components/Select';
import { apiGet, apiPost, apiPut } from '../shared/api';
import { useI18n } from '../shared/i18n';
import { useModelStatus } from '../shared/modelStatus';
import type { ModelSource, SettingsResponse } from '../shared/types';

export function SettingsPage() {
  const { t } = useI18n();
  const { models, refreshModelStatus, startDownload, stopDownload, deleteModel } = useModelStatus();
  const [selectedSource, setSelectedSource] = useState<ModelSource>('modelscope');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);

  const model = models[0] ?? null;

  const refreshSettings = useCallback(async () => {
    try {
      const data = await apiGet<SettingsResponse>('/settings');
      setSettings(data);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    void refreshSettings();
  }, [refreshSettings]);

  const updateGpuMode = useCallback(async (mode: 'cpu' | 'cuda') => {
    try {
      const data = await apiPut<SettingsResponse>('/settings', { gpu_mode: mode });
      setSettings(data);
    } catch {
      // ignore
    }
  }, []);

  const formatBytes = (value?: number | null) => {
    if (!value || value <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  };

  const sourceLabel = (src: ModelSource) =>
    src === 'huggingface' ? t('modelHuggingFace') : t('modelScope');

  const progress = Math.max(0, Math.min(model?.progress_percent ?? 0, 100));
  const fileProgress = Math.max(0, Math.min(model?.current_file_progress_percent ?? 0, 100));

  const cudaAvailable = settings?.cuda_available ?? false;
  const deepspeedAvailable = settings?.deepspeed_available ?? false;
  const installStatus = settings?.install_status ?? null;
  const installing = installStatus?.installing ?? false;

  // Poll settings during installation
  useEffect(() => {
    if (!installing) return;
    const timer = window.setInterval(() => {
      void refreshSettings();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [installing, refreshSettings]);

  return (
    <>
      <PageHeader title={t('settingsTitle')} subtitle={t('settingsSubtitle')} />
      <div className="workspace">
        {/* ── Model Management ── */}
        <Panel title={t('modelManagement')}>
          {/* Status bar */}
          <div className="settings-status-bar">
            <div className="settings-status-icon">
              <HardDrive size={20} />
            </div>
            <div className="settings-status-info">
              <strong>{model?.display_name ?? 'IndexTTS2'}</strong>
              <span className="settings-status-text">
                {model?.downloading
                  ? t('modelDownloading')
                  : model?.downloaded
                    ? t('modelDownloaded')
                    : t('modelMissing')}
              </span>
            </div>
            {model?.downloaded && model.model_source && (
              <span className="settings-source-chip">{sourceLabel(model.model_source as ModelSource)}</span>
            )}
            <button
              className="toolbar-button settings-refresh"
              onClick={() => void refreshModelStatus()}
              title={t('modelRefresh')}
            >
              <RefreshCw size={14} />
            </button>
          </div>

          {/* Model directory */}
          {model && (
            <div className="settings-dir">
              <FolderOpen size={14} />
              <code>{model.model_dir}</code>
            </div>
          )}

          {/* Source selector + action */}
          <div className="setting-row">
            <span>{t('modelSource')}</span>
            <div className="settings-source-actions">
              <Select
                value={selectedSource}
                onChange={(v) => setSelectedSource(v as ModelSource)}
                disabled={model?.downloading}
                width={180}
                options={[
                  { value: 'modelscope', label: t('modelScope') },
                  { value: 'huggingface', label: t('modelHuggingFace') },
                ]}
              />
              {model?.downloading ? (
                <button
                  className="toolbar-button settings-action-btn"
                  onClick={() => setShowStopConfirm(true)}
                  disabled={model.cancel_requested}
                >
                  <Square size={14} />
                  {t('modelStop')}
                </button>
              ) : model?.downloaded ? (
                <button
                  className="danger-button settings-action-btn"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  <Trash2 size={14} />
                  {t('modelDelete')}
                </button>
              ) : (
                <button
                  className="primary-button settings-action-btn"
                  onClick={() => void startDownload(model?.model_name ?? 'indextts2', selectedSource)}
                >
                  <Download size={14} />
                  {t('modelDownload')}
                </button>
              )}
            </div>
          </div>

          {/* Download progress */}
          {model?.downloading && (
            <div className="settings-progress">
              <div className="settings-progress-header">
                <span>
                  {typeof model.total_files === 'number' && typeof model.total_bytes === 'number'
                    ? t('modelProgress')
                        .replace('{completed}', String(model.completed_files ?? 0))
                        .replace('{total}', String(model.total_files))
                        .replace('{remaining}', String(model.remaining_files ?? 0))
                        .replace('{downloadedBytes}', formatBytes(model.downloaded_bytes))
                        .replace('{totalBytes}', formatBytes(model.total_bytes))
                    : t('modelProgressPreparing')}
                </span>
                <strong>{Math.round(progress)}%</strong>
              </div>
              <div className="settings-progress-bar">
                <div className="settings-progress-fill" style={{ width: `${progress}%` }} />
              </div>
              {model.current_file && (
                <>
                  <div className="settings-progress-header settings-progress-sub">
                    <span className="settings-progress-file">{model.current_file}</span>
                    <strong>{Math.round(fileProgress)}%</strong>
                  </div>
                  <div className="settings-progress-bar">
                    <div className="settings-progress-fill" style={{ width: `${fileProgress}%` }} />
                  </div>
                </>
              )}
            </div>
          )}

          {/* Error / message */}
          {model?.error && !model?.downloading && (
            <div className="settings-error">{model.error}</div>
          )}

          <p className="notice">{t('installLocal')}</p>
        </Panel>

        {/* ── GPU & Options ── */}
        <Panel title={t('gpuMode')}>
          <label className="field">
            <span>{t('gpuMode')}</span>
            <Select
              value={settings?.gpu_mode ?? 'cpu'}
              onChange={(v) => void updateGpuMode(v as 'cpu' | 'cuda')}
              disabled={!cudaAvailable}
              options={[
                { value: 'cpu', label: t('cpuMode') },
                { value: 'cuda', label: t('cudaMode') },
              ]}
            />
            {!cudaAvailable && (
              <div className="settings-hint-row">
                <span className="settings-hint">{t('cudaUnavailable')}</span>
                <button
                  className="toolbar-button settings-install-btn"
                  onClick={() => { void apiPost('/settings/install-cuda-torch', {}).then(() => refreshSettings()); }}
                  disabled={installing}
                >
                  {installing ? t('installing') : t('installCudaTorch')}
                </button>
              </div>
            )}
          </label>

          {!deepspeedAvailable && (
            <div className="field">
              <span>{t('deepspeedLabel')}</span>
              <div className="settings-hint-row">
                <span className="settings-hint">{t('deepspeedUnavailable')}</span>
                <button
                  className="toolbar-button settings-install-btn"
                  onClick={() => { void apiPost('/settings/install-deepspeed', {}).then(() => refreshSettings()); }}
                  disabled={installing}
                >
                  {installing ? t('installing') : t('installDeepSpeed')}
                </button>
              </div>
            </div>
          )}

          {/* Install progress */}
          {installStatus && (
            <div className={`settings-install-status${installStatus.error ? ' error' : installStatus.done ? ' done' : ''}`}>
              <span>{installStatus.message}</span>
              {installStatus.log && (
                <pre className="settings-install-log">{installStatus.log}</pre>
              )}
            </div>
          )}

          <label className="setting-row">
            <span>{t('githubMirror')}</span>
            <input type="checkbox" />
          </label>
        </Panel>
      </div>
      <ConfirmDialog
        open={showDeleteConfirm}
        message={t('modelDeleteConfirm').replace('{name}', model?.display_name ?? '')}
        confirmLabel={t('modelDelete')}
        cancelLabel={t('cancel')}
        danger
        onConfirm={() => {
          if (model) void deleteModel(model.model_name);
          setShowDeleteConfirm(false);
        }}
        onCancel={() => setShowDeleteConfirm(false)}
      />
      <ConfirmDialog
        open={showStopConfirm}
        message={t('modelStopConfirm')}
        confirmLabel={t('modelStop')}
        cancelLabel={t('cancel')}
        danger
        onConfirm={() => {
          if (model) void stopDownload(model.model_name);
          setShowStopConfirm(false);
        }}
        onCancel={() => setShowStopConfirm(false)}
      />
    </>
  );
}
