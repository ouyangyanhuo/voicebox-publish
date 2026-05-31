import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { apiDelete, apiGet, apiPost } from './api';
import type { ModelListResponse, ModelName, ModelSource, ModelStatus } from './types';

type ModelStatusContextValue = {
  models: ModelStatus[];
  modelStatus: ModelStatus | null;
  modelError: string | null;
  refreshModelStatus: () => Promise<void>;
  startDownload: (modelName?: ModelName, source?: ModelSource) => Promise<void>;
  stopDownload: (modelName: ModelName) => Promise<void>;
  deleteModel: (modelName: ModelName) => Promise<void>;
};

const ModelStatusContext = createContext<ModelStatusContextValue | null>(null);

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function ModelStatusProvider({ children }: { children: ReactNode }) {
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);

  const refreshModelStatus = useCallback(async () => {
    try {
      const response = await apiGet<ModelListResponse>('/models');
      const primary = response.items[0] ?? null;
      setModels(response.items);
      setModelStatus(primary);
      setModelError(primary?.error ?? null);
    } catch (error) {
      setModelError(errorMessage(error, 'Failed to load model status'));
    }
  }, []);

  useEffect(() => {
    void refreshModelStatus();
  }, [refreshModelStatus]);

  const hasDownloadingModel = models.some((model) => model.downloading);

  useEffect(() => {
    if (!hasDownloadingModel) return;
    const timer = window.setInterval(() => {
      void refreshModelStatus();
    }, 1000);
    return () => window.clearInterval(timer);
  }, [hasDownloadingModel, refreshModelStatus]);

  const startDownload = useCallback(async (modelName: ModelName = 'indextts2', source: ModelSource = 'modelscope') => {
    setModelError(null);
    try {
      const status = await apiPost<ModelStatus>(`/models/${modelName}/download?source=${source}`, {});
      setModels([status]);
      setModelStatus(status);
    } catch (error) {
      setModelError(errorMessage(error, 'Failed to start download'));
    }
  }, []);

  const stopDownload = useCallback(async (modelName: ModelName) => {
    setModelError(null);
    try {
      const status = await apiPost<ModelStatus>(`/models/${modelName}/stop`, {});
      setModels([status]);
      setModelStatus(status);
    } catch (error) {
      setModelError(errorMessage(error, 'Failed to stop download'));
    }
  }, []);

  const deleteModel = useCallback(async (modelName: ModelName) => {
    setModelError(null);
    try {
      const status = await apiDelete<ModelStatus>(`/models/${modelName}`);
      setModels([status]);
      setModelStatus(status);
    } catch (error) {
      setModelError(errorMessage(error, 'Failed to delete model'));
    }
  }, []);

  const value = useMemo(
    () => ({
      models,
      modelStatus,
      modelError,
      refreshModelStatus,
      startDownload,
      stopDownload,
      deleteModel,
    }),
    [deleteModel, modelError, modelStatus, models, refreshModelStatus, startDownload, stopDownload],
  );

  return <ModelStatusContext.Provider value={value}>{children}</ModelStatusContext.Provider>;
}

export function useModelStatus() {
  const context = useContext(ModelStatusContext);
  if (!context) {
    throw new Error('useModelStatus must be used inside ModelStatusProvider');
  }
  return context;
}
