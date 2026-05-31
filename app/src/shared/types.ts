export type SectionId = 'single' | 'stories' | 'roles' | 'emotion' | 'presetVoices' | 'settings';

export type EmotionVector = [number, number, number, number, number, number, number, number];

export type PresetVoice = {
  id: string;
  name: string;
  description?: string | null;
  language?: string | null;
  gender?: string | null;
  style?: string | null;
  tags: string[];
  file: string;
  reference_text?: string | null;
  license?: string | null;
};

export type Role = {
  id: string;
  name: string;
  description?: string | null;
  language: 'zh' | 'en';
  sample_count: number;
};

export type UploadedGenerationAudio = {
  id: string;
  file_name: string;
  audio_url: string;
};

export type GenerationStatus = 'queued' | 'running' | 'completed' | 'failed' | 'not_implemented';

export type GenerationStatusResponse = {
  id: string;
  status: GenerationStatus;
  text: string;
  language: 'zh' | 'en';
  audio_url?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
};

export type ModelName = 'indextts2';

export type ModelSource = 'modelscope' | 'huggingface';

export type ModelStatus = {
  model_name: ModelName;
  display_name: string;
  model_source: ModelSource;
  model_id: string;
  model_dir: string;
  downloaded: boolean;
  downloading: boolean;
  loaded: boolean;
  total_files?: number | null;
  completed_files: number;
  remaining_files?: number | null;
  total_bytes?: number | null;
  downloaded_bytes: number;
  current_file?: string | null;
  current_file_bytes: number;
  current_file_total_bytes?: number | null;
  current_file_progress_percent?: number | null;
  progress_percent?: number | null;
  cancel_requested: boolean;
  error?: string | null;
  message?: string | null;
};

export type ModelListResponse = {
  items: ModelStatus[];
};

export type InstallStatus = {
  installing: boolean;
  package?: string | null;
  message?: string | null;
  log?: string | null;
  error?: string | null;
  done: boolean;
};

export type SettingsResponse = {
  model_source: ModelSource;
  github_mirror_enabled: boolean;
  gpu_mode: 'cpu' | 'cuda';
  use_fp16: boolean;
  use_cuda_kernel: boolean;
  use_deepspeed: boolean;
  cuda_available: boolean;
  deepspeed_available: boolean;
  install_status?: InstallStatus | null;
};
