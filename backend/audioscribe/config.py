from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class StorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimePaths:
    install_dir: Path
    data_dir: Path
    cache_dir: Path
    model_dir: Path
    logs_dir: Path
    database_path: Path
    generated_audio_dir: Path
    role_samples_dir: Path
    audio_library_dir: Path
    worker_cache_dir: Path
    modelscope_model_dir: Path
    huggingface_cache_dir: Path
    preset_voice_dir: Path


def get_install_dir() -> Path:
    raw = os.environ.get("VOICEBOX_INSTALL_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def get_runtime_paths() -> RuntimePaths:
    install = get_install_dir()
    data = install / "data"
    cache = install / "cache"
    model = install / "model"
    logs = install / "logs"
    return RuntimePaths(
        install_dir=install,
        data_dir=data,
        cache_dir=cache,
        model_dir=model,
        logs_dir=logs,
        database_path=data / "voicebox.db",
        generated_audio_dir=data / "generations",
        role_samples_dir=data / "roles",
        audio_library_dir=data / "audio-library",
        worker_cache_dir=cache / "indextts2",
        modelscope_model_dir=model / "modelscope",
        huggingface_cache_dir=cache / "huggingface",
        preset_voice_dir=install / "preset-voices",
    )


def _ensure_writable(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".voicebox_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise StorageError(f"Directory is not writable: {path} ({exc})") from exc


def initialize_runtime() -> RuntimePaths:
    paths = get_runtime_paths()
    for path in (
        paths.data_dir,
        paths.cache_dir,
        paths.model_dir,
        paths.logs_dir,
        paths.generated_audio_dir,
        paths.role_samples_dir,
        paths.audio_library_dir,
        paths.worker_cache_dir,
        paths.modelscope_model_dir,
        paths.huggingface_cache_dir,
        paths.preset_voice_dir,
    ):
        _ensure_writable(path)

    os.environ["MODELSCOPE_CACHE"] = str(paths.modelscope_model_dir)
    os.environ["HF_HOME"] = str(paths.huggingface_cache_dir)
    os.environ["HF_HUB_CACHE"] = str(paths.huggingface_cache_dir / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(paths.cache_dir / "transformers")
    os.environ["TORCH_HOME"] = str(paths.cache_dir / "torch")
    os.environ["VOICEBOX_WORKER_CACHE"] = str(paths.worker_cache_dir)
    return paths
