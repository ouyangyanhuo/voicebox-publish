"""Configuration module for voicebox backend.

All writable runtime state is rooted under the application install directory:

* ``data/`` stores user data and the SQLite database.
* ``cache/`` stores transient runtime caches.
* ``model/`` stores downloaded ML models.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_install_dir = Path(os.environ.get("VOICEBOX_INSTALL_DIR", ".")).resolve()
_data_dir = _install_dir / "data"
_cache_dir = _install_dir / "cache"
_models_dir = _install_dir / "model"


def _set_env_path(name: str, path: Path) -> None:
    os.environ[name] = str(path)


def _sync_huggingface_runtime_constants() -> None:
    try:
        from huggingface_hub import constants as hf_constants

        hf_constants.HF_HOME = str(_cache_dir / "huggingface")
        hf_constants.HF_HUB_CACHE = str(_models_dir / "huggingface")
    except Exception:
        pass

    try:
        from transformers.utils import hub as transformers_hub

        transformers_hub.TRANSFORMERS_CACHE = str(_models_dir / "huggingface")
    except Exception:
        pass


def configure_cache_environment() -> None:
    """Force third-party caches and model downloads under the install dir."""
    _set_env_path("VOICEBOX_INSTALL_DIR", _install_dir)
    _set_env_path("VOICEBOX_CACHE_DIR", _cache_dir)
    _set_env_path("VOICEBOX_MODELS_DIR", _models_dir)

    _set_env_path("XDG_CACHE_HOME", _cache_dir)
    _set_env_path("TORCH_HOME", _cache_dir / "torch")
    _set_env_path("NUMBA_CACHE_DIR", _cache_dir / "numba")
    _set_env_path("MPLCONFIGDIR", _cache_dir / "matplotlib")

    _set_env_path("HF_HOME", _cache_dir / "huggingface")
    _set_env_path("HF_HUB_CACHE", _models_dir / "huggingface")
    os.environ.pop("TRANSFORMERS_CACHE", None)
    _set_env_path("HF_DATASETS_CACHE", _cache_dir / "huggingface" / "datasets")

    _set_env_path("MODELSCOPE_CACHE", _models_dir / "modelscope")
    _set_env_path("MODELSCOPE_MODULES_CACHE", _cache_dir / "modelscope" / "modules")

    _sync_huggingface_runtime_constants()


def set_install_dir(path: str | Path) -> None:
    """Set the application install directory and derived writable roots."""
    global _install_dir, _data_dir, _cache_dir, _models_dir

    _install_dir = Path(path).resolve()
    _data_dir = _install_dir / "data"
    _cache_dir = _install_dir / "cache"
    _models_dir = _install_dir / "model"
    configure_cache_environment()
    ensure_storage_roots()
    logger.info("Install directory set to: %s", _install_dir)


def get_install_dir() -> Path:
    return _install_dir


def _path_relative_to_any_data_dir(path: Path) -> Path | None:
    """Extract the path within a data dir from an absolute or relative path."""
    parts = path.parts
    for idx, part in enumerate(parts):
        if part != "data":
            continue

        tail = parts[idx + 1 :]
        if tail:
            return Path(*tail)
        return Path()

    return None


def set_data_dir(path: str | Path):
    """
    Resolve the legacy data directory argument to an install directory.

    Args:
        path: Path to the data directory
    """
    data_path = Path(path).resolve()
    install_path = data_path.parent if data_path.name == "data" else data_path
    set_install_dir(install_path)
    logger.info("Legacy data directory argument resolved to install directory: %s", install_path)


def get_data_dir() -> Path:
    """
    Get the data directory path.

    Returns:
        Path to the data directory
    """
    return _data_dir


def to_storage_path(path: str | Path) -> str:
    """Convert a filesystem path to a DB-safe path relative to the data dir."""
    resolved_path = Path(path).resolve()

    relative_to_any_data_dir = _path_relative_to_any_data_dir(resolved_path)
    if relative_to_any_data_dir is not None:
        return str(relative_to_any_data_dir)

    try:
        return str(resolved_path.relative_to(_data_dir))
    except ValueError:
        return str(resolved_path)


def resolve_storage_path(path: str | Path | None) -> Path | None:
    """Resolve a DB-stored path against the configured data dir."""
    if path is None:
        return None

    stored_path = Path(path)
    if stored_path.is_absolute():
        rebased_path = _path_relative_to_any_data_dir(stored_path)
        if rebased_path is not None:
            candidate = (_data_dir / rebased_path).resolve()
            if candidate.exists() or not stored_path.exists():
                return candidate

        return stored_path

    # 0.3.0 records sometimes stored relative paths with the data-dir name
    # baked in (e.g. "data/profiles/..."). Joining those directly with
    # _data_dir produces a spurious "<data_dir>/data/profiles/..." nest.
    if stored_path.parts and stored_path.parts[0] == "data":
        stored_path = (
            Path(*stored_path.parts[1:]) if len(stored_path.parts) > 1 else Path()
        )

    return (_data_dir / stored_path).resolve()


def get_db_path() -> Path:
    """Get database file path."""
    return _data_dir / "voicebox.db"


def get_profiles_dir() -> Path:
    """Get profiles directory path."""
    path = _data_dir / "profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_generations_dir() -> Path:
    """Get generations directory path."""
    path = _data_dir / "generations"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_captures_dir() -> Path:
    """Get captures directory path."""
    path = _data_dir / "captures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    """Get cache directory path."""
    path = _cache_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_root_dir() -> Path:
    """Get the top-level runtime cache directory."""
    path = _cache_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_models_dir() -> Path:
    """Get the top-level model download directory."""
    path = _models_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_huggingface_home_dir() -> Path:
    path = get_cache_root_dir() / "huggingface"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_huggingface_models_dir() -> Path:
    path = get_models_dir() / "huggingface"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_modelscope_models_dir() -> Path:
    path = get_models_dir() / "modelscope"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_storage_roots() -> None:
    """Create and verify the required install-local writable roots."""
    for root in (_data_dir, _cache_dir, _models_dir):
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".voicebox-write-test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except Exception as exc:
            raise RuntimeError(f"Voicebox storage directory is not writable: {root}") from exc


configure_cache_environment()
