"""Model download source routing.

ModelScope is the default source. ModelScope downloads must use explicit
mappings and local snapshot paths so no backend silently falls back to
HuggingFace.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from .. import config
from .settings import get_download_settings_snapshot

logger = logging.getLogger(__name__)

HUGGINGFACE = "huggingface"
MODELSCOPE = "modelscope"

# Conservative explicit mappings. Models not listed here fail fast when
# ModelScope is selected.
MODELSCOPE_MODEL_IDS: dict[str, str] = {
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "Qwen/Qwen3-0.6B": "Qwen/Qwen3-0.6B",
    "Qwen/Qwen3-1.7B": "Qwen/Qwen3-1.7B",
    "Qwen/Qwen3-4B": "Qwen/Qwen3-4B",
    "openai/whisper-base": "AI-ModelScope/whisper-base",
    "openai/whisper-small": "AI-ModelScope/whisper-small",
    "openai/whisper-medium": "AI-ModelScope/whisper-medium",
    "openai/whisper-large-v3": "AI-ModelScope/whisper-large-v3",
    "openai/whisper-large-v3-turbo": "AI-ModelScope/whisper-large-v3-turbo",
}


def get_model_source() -> str:
    source, _github_mirror_enabled = get_download_settings_snapshot()
    if source not in (HUGGINGFACE, MODELSCOPE):
        return MODELSCOPE
    return source


def is_modelscope_enabled() -> bool:
    return get_model_source() == MODELSCOPE


def require_huggingface_source(feature: str) -> None:
    if is_modelscope_enabled():
        raise RuntimeError(f"{feature} does not support ModelScope downloads yet. Switch model downloads to HuggingFace.")


def get_modelscope_id(hf_repo: str) -> str:
    model_id = MODELSCOPE_MODEL_IDS.get(hf_repo)
    if model_id is None:
        raise RuntimeError(f"ModelScope source is enabled, but {hf_repo} is not mapped for ModelScope downloads.")
    return model_id


def resolve_model_reference(hf_repo: str) -> str:
    """Return a repo id for HF or a local snapshot path for ModelScope."""
    if not is_modelscope_enabled():
        return hf_repo
    return download_modelscope_snapshot(hf_repo)


def download_modelscope_snapshot(hf_repo: str) -> str:
    """Download a mapped ModelScope model and return its local snapshot path."""
    model_id = get_modelscope_id(hf_repo)
    try:
        from modelscope import snapshot_download
    except Exception:
        try:
            from modelscope.hub.snapshot_download import snapshot_download
        except Exception as exc:
            raise RuntimeError("ModelScope source is enabled, but the modelscope package is not installed.") from exc

    cache_dir = config.get_modelscope_models_dir()
    logger.info("Downloading %s from ModelScope as %s into %s", hf_repo, model_id, cache_dir)
    return snapshot_download(model_id=model_id, cache_dir=str(cache_dir))


def get_active_model_cache_dir() -> Path:
    if is_modelscope_enabled():
        return config.get_modelscope_models_dir()
    return config.get_huggingface_models_dir()


def get_huggingface_repo_cache_dir(hf_repo: str) -> Path:
    return config.get_huggingface_models_dir() / ("models--" + hf_repo.replace("/", "--"))


def get_modelscope_repo_cache_candidates(hf_repo: str) -> list[Path]:
    model_id = MODELSCOPE_MODEL_IDS.get(hf_repo)
    if not model_id:
        return []
    root = config.get_modelscope_models_dir()
    namespace, _, name = model_id.partition("/")
    candidates = [
        root / model_id,
        root / namespace / name if namespace and name else root / model_id,
        root / "hub" / model_id,
        root / "hub" / namespace / name if namespace and name else root / "hub" / model_id,
        root / "models" / model_id,
        root / "models" / namespace / name if namespace and name else root / "models" / model_id,
    ]
    return [c for c in candidates if c.exists()]


def get_model_cache_dir_for_repo(hf_repo: str) -> Path:
    if is_modelscope_enabled():
        candidates = get_modelscope_repo_cache_candidates(hf_repo)
        if candidates:
            return candidates[0]
        model_id = MODELSCOPE_MODEL_IDS.get(hf_repo, hf_repo.replace("/", "--"))
        return config.get_modelscope_models_dir() / model_id
    return get_huggingface_repo_cache_dir(hf_repo)


def _has_required_files(root: Path, required_files: Iterable[str]) -> bool:
    return all(any(root.rglob(fname)) for fname in required_files)


def is_model_cached(
    hf_repo: str,
    *,
    weight_extensions: tuple[str, ...] = (".safetensors", ".bin"),
    required_files: list[str] | None = None,
) -> bool:
    if not is_modelscope_enabled():
        repo_cache = get_huggingface_repo_cache_dir(hf_repo)
        if not repo_cache.exists():
            return False
        blobs_dir = repo_cache / "blobs"
        if blobs_dir.exists() and any(blobs_dir.glob("*.incomplete")):
            return False
        snapshots_dir = repo_cache / "snapshots"
        if not snapshots_dir.exists():
            return False
        if required_files:
            return _has_required_files(snapshots_dir, required_files)
        return any(any(snapshots_dir.rglob(f"*{ext}")) for ext in weight_extensions)

    if hf_repo not in MODELSCOPE_MODEL_IDS:
        return False
    roots = get_modelscope_repo_cache_candidates(hf_repo)
    if not roots:
        return False
    for root in roots:
        if required_files and _has_required_files(root, required_files):
            return True
        if not required_files and any(any(root.rglob(f"*{ext}")) for ext in weight_extensions):
            return True
    return False
