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
    version: str
    install_dir: str
    model_engine: Literal["indextts2"] = "indextts2"


class FilesystemHealthResponse(BaseModel):
    healthy: bool
    directories: list[DirectoryStatus]


class SettingsResponse(BaseModel):
    model_source: Literal["modelscope"] = "modelscope"
    github_mirror_enabled: bool = False
    gpu_mode: Literal["cpu", "cuda"] = "cpu"
    use_fp16: bool = False
    use_cuda_kernel: bool = False
    use_deepspeed: bool = False


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


class RoleResponse(RoleCreate):
    id: str
    sample_count: int = 0


class GenerationRequest(BaseModel):
    role_id: str
    text: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(default="zh", pattern="^(zh|en)$")
    emo_alpha: float = Field(default=1.0, ge=0.0, le=1.0)
    emo_vector: list[float] | None = Field(default=None, min_length=8, max_length=8)
    emo_text: str | None = Field(default=None, max_length=1000)
    use_random: bool = False
    interval_silence: int = Field(default=200, ge=0, le=5000)
    max_text_tokens_per_segment: int = Field(default=120, ge=20, le=500)


class GenerationResponse(BaseModel):
    id: str
    status: Literal["queued", "failed"]
    message: str


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
    model_source: Literal["modelscope"] = "modelscope"
    model_id: str = "IndexTeam/IndexTTS-2"
    downloaded: bool
    loaded: bool = False
