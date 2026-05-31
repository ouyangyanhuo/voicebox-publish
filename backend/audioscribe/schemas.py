from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DirectoryStatus(BaseModel):
    path: str
    exists: bool
    writable: bool
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    app_name: Literal["AudioScribe"] = "AudioScribe"
    version: str
    install_dir: str
    model_engine: Literal["indextts2"] = "indextts2"


class FilesystemHealthResponse(BaseModel):
    healthy: bool
    directories: list[DirectoryStatus]


class RuntimePathSummary(BaseModel):
    install_dir: str
    data_dir: str
    cache_dir: str
    model_dir: str
    logs_dir: str
    database_path: str
    generated_audio_dir: str
    role_samples_dir: str
    preset_voice_dir: str
    temp_dir: str


class UploadedGenerationAudioResponse(BaseModel):
    id: str
    file_name: str
    audio_url: str


class InstallStatus(BaseModel):
    installing: bool = False
    package: str | None = None
    message: str | None = None
    log: str | None = None
    error: str | None = None
    done: bool = False


class SettingsResponse(BaseModel):
    model_source: Literal["modelscope", "huggingface"] = "modelscope"
    github_mirror_enabled: bool = False
    gpu_mode: Literal["cpu", "cuda"] = "cpu"
    use_fp16: bool = False
    use_cuda_kernel: bool = False
    use_deepspeed: bool = False
    paths: RuntimePathSummary | None = None
    cuda_available: bool = False
    deepspeed_available: bool = False
    install_status: InstallStatus | None = None


class SettingsUpdate(BaseModel):
    github_mirror_enabled: bool | None = None
    gpu_mode: Literal["cpu", "cuda"] | None = None
    use_fp16: bool | None = None
    use_cuda_kernel: bool | None = None
    use_deepspeed: bool | None = None


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    language: str = Field(default="zh", pattern="^(zh|en)$")
    default_emo_alpha: float = Field(default=1.0, ge=0.0, le=1.0)
    default_emo_vector: list[float] = Field(default_factory=lambda: [0.0] * 8, min_length=8, max_length=8)
    default_emo_text: str | None = Field(default=None, max_length=1000)


class RoleResponse(RoleCreate):
    id: str
    sample_count: int = 0
    updated_at: str | None = None


class GenerationRequest(BaseModel):
    role_id: str | None = None
    audio_source: Literal["preset", "upload", "record", "role"] = "role"
    preset_voice_id: str | None = None
    uploaded_audio_id: str | None = None
    recorded_audio_id: str | None = None
    text: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(default="zh", pattern="^(zh|en)$")
    emo_alpha: float = Field(default=1.0, ge=0.0, le=1.0)
    emo_vector: list[float] | None = Field(default=None, min_length=8, max_length=8)
    emo_audio_id: str | None = None
    emo_text: str | None = Field(default=None, max_length=1000)
    use_emo_text: bool = False
    use_random: bool = False
    interval_silence: int = Field(default=200, ge=0, le=5000)
    max_text_tokens_per_segment: int = Field(default=120, ge=20, le=500)


class GenerationResponse(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed", "not_implemented"]
    message: str


class GenerationStatusResponse(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed", "not_implemented"]
    text: str
    language: str
    audio_url: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class StoryResponse(StoryCreate):
    id: str
    line_count: int = 0


class EmotionPresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    emo_alpha: float = Field(default=1.0, ge=0.0, le=1.0)
    emo_vector: list[float] = Field(default_factory=lambda: [0.0] * 8, min_length=8, max_length=8)
    emo_text: str | None = Field(default=None, max_length=1000)


class EmotionPresetResponse(EmotionPresetCreate):
    id: str


class PresetVoiceItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    language: str | None = None
    gender: str | None = None
    style: str | None = None
    tags: list[str] = Field(default_factory=list)
    file: str
    reference_text: str | None = None
    license: str | None = None


class PresetVoiceListResponse(BaseModel):
    items: list[PresetVoiceItem]


class ModelStatusResponse(BaseModel):
    model_name: Literal["indextts2"] = "indextts2"
    display_name: str = "IndexTTS2"
    model_source: Literal["modelscope", "huggingface"] = "modelscope"
    model_id: str = "IndexTeam/IndexTTS-2"
    model_dir: str
    downloaded: bool
    downloading: bool = False
    loaded: bool = False
    total_files: int | None = None
    completed_files: int = 0
    remaining_files: int | None = None
    total_bytes: int | None = None
    downloaded_bytes: int = 0
    current_file: str | None = None
    current_file_bytes: int = 0
    current_file_total_bytes: int | None = None
    current_file_progress_percent: float | None = None
    progress_percent: float | None = None
    cancel_requested: bool = False
    error: str | None = None
    message: str | None = None


class ModelListResponse(BaseModel):
    items: list[ModelStatusResponse]
