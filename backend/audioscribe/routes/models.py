from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
import requests

from ..config import RuntimePaths
from ..schemas import ModelListResponse, ModelStatusResponse

router = APIRouter()

MODEL_ID = "IndexTeam/IndexTTS-2"
MODEL_SUBDIR = Path("IndexTeam") / "IndexTTS-2"
MODEL_NAME = "indextts2"
SOURCES = ("modelscope", "huggingface")

_download_lock = threading.Lock()
_download_cancel_event = threading.Event()
_download_state: dict[str, object] = {
    "downloading": False,
    "source": "modelscope",
    "error": None,
    "message": None,
    "total_files": None,
    "completed_files": 0,
    "remaining_files": None,
    "total_bytes": None,
    "downloaded_bytes": 0,
    "current_file": None,
    "current_file_bytes": 0,
    "current_file_total_bytes": None,
    "current_file_progress_percent": None,
    "progress_percent": None,
    "cancel_requested": False,
}


@dataclass(frozen=True)
class ModelFile:
    path: str
    size: int
    sha256: str | None = None


def _snapshot_dir(paths: RuntimePaths) -> Path:
    return paths.model_dir / MODEL_SUBDIR


def _is_downloaded(snapshot_dir: Path) -> bool:
    return (snapshot_dir / "config.yaml").exists()


def _model_env(paths: RuntimePaths) -> dict[str, str]:
    env = os.environ.copy()
    env["AUDIOSCRIBE_INSTALL_DIR"] = str(paths.install_dir)
    env["MODELSCOPE_CACHE"] = str(paths.modelscope_model_dir)
    env["HF_HOME"] = str(paths.huggingface_cache_dir)
    env["HF_HUB_CACHE"] = str(paths.huggingface_cache_dir / "hub")
    env["HUGGINGFACE_HUB_CACHE"] = str(paths.huggingface_cache_dir / "hub")
    env["TRANSFORMERS_CACHE"] = str(paths.cache_dir / "transformers")
    env["TORCH_HOME"] = str(paths.cache_dir / "torch")
    env["TEMP"] = str(paths.temp_dir)
    env["TMP"] = str(paths.temp_dir)
    for path in (
        paths.modelscope_model_dir,
        paths.huggingface_cache_dir,
        paths.huggingface_cache_dir / "hub",
        paths.cache_dir / "transformers",
        paths.cache_dir / "torch",
        paths.temp_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return env


def _set_state(
    *,
    downloading: bool,
    source: str = "modelscope",
    error: str | None = None,
    message: str | None = None,
    total_files: int | None = None,
    completed_files: int = 0,
    remaining_files: int | None = None,
    total_bytes: int | None = None,
    downloaded_bytes: int = 0,
    current_file: str | None = None,
    current_file_bytes: int = 0,
    current_file_total_bytes: int | None = None,
    current_file_progress_percent: float | None = None,
    progress_percent: float | None = None,
    cancel_requested: bool = False,
) -> None:
    with _download_lock:
        _download_state["downloading"] = downloading
        _download_state["source"] = source
        _download_state["error"] = error
        _download_state["message"] = message
        _download_state["total_files"] = total_files
        _download_state["completed_files"] = completed_files
        _download_state["remaining_files"] = remaining_files
        _download_state["total_bytes"] = total_bytes
        _download_state["downloaded_bytes"] = downloaded_bytes
        _download_state["current_file"] = current_file
        _download_state["current_file_bytes"] = current_file_bytes
        _download_state["current_file_total_bytes"] = current_file_total_bytes
        _download_state["current_file_progress_percent"] = current_file_progress_percent
        _download_state["progress_percent"] = progress_percent
        _download_state["cancel_requested"] = cancel_requested


def _update_progress(
    *,
    source: str,
    total_files: int,
    completed_files: int,
    total_bytes: int,
    downloaded_bytes: int,
    current_file: str | None,
    current_file_bytes: int,
    current_file_total_bytes: int | None,
    message: str,
) -> None:
    remaining_files = max(total_files - completed_files, 0)
    progress_percent = round((downloaded_bytes / total_bytes) * 100, 2) if total_bytes else 0.0
    current_file_progress_percent = (
        round((current_file_bytes / current_file_total_bytes) * 100, 2)
        if current_file_total_bytes
        else None
    )
    with _download_lock:
        _download_state["downloading"] = True
        _download_state["source"] = source
        _download_state["error"] = None
        _download_state["message"] = message
        _download_state["total_files"] = total_files
        _download_state["completed_files"] = completed_files
        _download_state["remaining_files"] = remaining_files
        _download_state["total_bytes"] = total_bytes
        _download_state["downloaded_bytes"] = downloaded_bytes
        _download_state["current_file"] = current_file
        _download_state["current_file_bytes"] = current_file_bytes
        _download_state["current_file_total_bytes"] = current_file_total_bytes
        _download_state["current_file_progress_percent"] = current_file_progress_percent
        _download_state["progress_percent"] = progress_percent
        _download_state["cancel_requested"] = _download_cancel_event.is_set()


def _raise_if_cancelled() -> None:
    if _download_cancel_event.is_set():
        raise RuntimeError("Download stopped by user.")


# ---------------------------------------------------------------------------
# ModelScope
# ---------------------------------------------------------------------------

def _normalize_model_file(entry: object) -> ModelFile | None:
    sha256: str | None = None
    size = 0
    if isinstance(entry, dict):
        entry_type = str(entry.get("type") or entry.get("Type") or "").lower()
        if entry_type in {"tree", "directory", "dir", "folder"}:
            return None
        raw = (
            entry.get("Path")
            or entry.get("path")
            or entry.get("Name")
            or entry.get("name")
            or entry.get("file_path")
            or entry.get("FilePath")
        )
        value = str(raw) if raw else ""
        raw_size = entry.get("Size") or entry.get("size") or 0
        size = int(raw_size) if str(raw_size).isdigit() else 0
        raw_hash = entry.get("Sha256") or entry.get("sha256") or entry.get("Hash") or entry.get("hash")
        sha256 = str(raw_hash) if raw_hash else None
    elif isinstance(entry, str):
        value = entry
    else:
        value = str(entry)
    value = value.replace("\\", "/").strip("/")
    if not value or value.endswith("/"):
        return None
    return ModelFile(path=value, size=size, sha256=sha256)


def _list_model_files_modelscope(paths: RuntimePaths) -> list[ModelFile]:
    os.environ.update(_model_env(paths))
    try:
        from modelscope.hub.api import HubApi
    except Exception as exc:
        raise RuntimeError("ModelScope SDK is not installed.") from exc

    api = HubApi()
    errors: list[str] = []
    call_variants = (
        lambda: api.get_model_files(MODEL_ID, recursive=True),
        lambda: api.get_model_files(model_id=MODEL_ID, recursive=True),
        lambda: api.get_model_files(MODEL_ID, revision="master", recursive=True),
        lambda: api.get_model_files(model_id=MODEL_ID, revision="master", recursive=True),
    )
    for call in call_variants:
        try:
            raw_files = call()
            files = sorted(
                {file for item in raw_files for file in [_normalize_model_file(item)] if file},
                key=lambda file: file.path,
            )
            if files:
                return files
        except Exception as exc:
            errors.append(str(exc))
    joined = "; ".join(error for error in errors if error)
    raise RuntimeError(f"Could not fetch ModelScope file list for {MODEL_ID}. {joined[-1200:]}")


def _download_model_file_modelscope(
    paths: RuntimePaths,
    target: Path,
    model_file: ModelFile,
    *,
    total_files: int,
    completed_files: int,
    total_bytes: int,
    completed_bytes_before_file: int,
) -> int:
    os.environ.update(_model_env(paths))
    try:
        from modelscope.hub.api import HubApi
        from modelscope.hub.file_download import get_file_download_url
    except Exception as exc:
        raise RuntimeError("ModelScope SDK is not installed.") from exc

    _raise_if_cancelled()
    api = HubApi()
    cookies = api.get_cookies()
    endpoint = api.get_endpoint_for_read(repo_id=MODEL_ID, repo_type="model", token=None)
    revision = api.get_valid_revision(MODEL_ID, revision="master", cookies=cookies, endpoint=endpoint)
    url = get_file_download_url(MODEL_ID, model_file.path, revision, endpoint)

    output_path = target / Path(model_file.path)
    part_path = output_path.with_name(f"{output_path.name}.part")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    downloaded_for_file = part_path.stat().st_size if part_path.exists() else 0
    if output_path.exists() and output_path.stat().st_size >= model_file.size > 0:
        return model_file.size
    if model_file.size and downloaded_for_file >= model_file.size:
        part_path.replace(output_path)
        return model_file.size

    headers = {"X-Request-ID": os.urandom(16).hex()}
    if downloaded_for_file:
        headers["Range"] = f"bytes={downloaded_for_file}-"
    _update_progress(
        source="modelscope",
        total_files=total_files,
        completed_files=completed_files,
        total_bytes=total_bytes,
        downloaded_bytes=completed_bytes_before_file + downloaded_for_file,
        current_file=model_file.path,
        current_file_bytes=downloaded_for_file,
        current_file_total_bytes=model_file.size or None,
        message=f"Downloading {model_file.path}",
    )

    with requests.get(url, stream=True, headers=headers, cookies=cookies, timeout=120) as response:
        response.raise_for_status()
        with part_path.open("ab") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                _raise_if_cancelled()
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded_for_file += len(chunk)
                _update_progress(
                    source="modelscope",
                    total_files=total_files,
                    completed_files=completed_files,
                    total_bytes=total_bytes,
                    downloaded_bytes=completed_bytes_before_file + downloaded_for_file,
                    current_file=model_file.path,
                    current_file_bytes=downloaded_for_file,
                    current_file_total_bytes=model_file.size or None,
                    message=f"Downloading {model_file.path}",
                )

    if model_file.size and downloaded_for_file < model_file.size:
        raise RuntimeError(f"Download incomplete for {model_file.path}.")
    part_path.replace(output_path)
    return downloaded_for_file


# ---------------------------------------------------------------------------
# HuggingFace
# ---------------------------------------------------------------------------

def _list_model_files_huggingface(paths: RuntimePaths) -> list[ModelFile]:
    os.environ.update(_model_env(paths))
    try:
        from huggingface_hub import HfApi
    except Exception as exc:
        raise RuntimeError("huggingface_hub is not installed.") from exc

    api = HfApi()
    info = api.model_info(MODEL_ID)
    files: list[ModelFile] = []
    for sibling in (info.siblings or []):
        if sibling.rfilename and not sibling.rfilename.endswith("/"):
            size = sibling.size if isinstance(sibling.size, int) and sibling.size > 0 else 0
            files.append(ModelFile(path=sibling.rfilename, size=size))
    files.sort(key=lambda f: f.path)
    if not files:
        raise RuntimeError(f"No files found for HuggingFace model {MODEL_ID}.")
    return files


def _download_model_file_huggingface(
    paths: RuntimePaths,
    target: Path,
    model_file: ModelFile,
    *,
    total_files: int,
    completed_files: int,
    total_bytes: int,
    completed_bytes_before_file: int,
) -> int:
    os.environ.update(_model_env(paths))
    try:
        from huggingface_hub import hf_hub_download
    except Exception as exc:
        raise RuntimeError("huggingface_hub is not installed.") from exc

    _raise_if_cancelled()

    output_path = target / model_file.path
    if output_path.exists() and (model_file.size == 0 or output_path.stat().st_size >= model_file.size):
        return model_file.size or output_path.stat().st_size

    _update_progress(
        source="huggingface",
        total_files=total_files,
        completed_files=completed_files,
        total_bytes=total_bytes,
        downloaded_bytes=completed_bytes_before_file,
        current_file=model_file.path,
        current_file_bytes=0,
        current_file_total_bytes=model_file.size or None,
        message=f"Downloading {model_file.path}",
    )

    _raise_if_cancelled()
    hf_hub_download(
        repo_id=MODEL_ID,
        filename=model_file.path,
        local_dir=str(target),
        revision="main",
    )

    actual_size = output_path.stat().st_size if output_path.exists() else 0
    return model_file.size or actual_size


# ---------------------------------------------------------------------------
# Shared download orchestration
# ---------------------------------------------------------------------------

def _download_model(paths: RuntimePaths, source: str) -> None:
    target = _snapshot_dir(paths)
    _download_cancel_event.clear()
    _set_state(downloading=True, source=source, error=None, message=f"Fetching {source} file list...")

    list_fn = _list_model_files_huggingface if source == "huggingface" else _list_model_files_modelscope
    download_fn = _download_model_file_huggingface if source == "huggingface" else _download_model_file_modelscope

    try:
        os.environ.update(_model_env(paths))
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)

        files = list_fn(paths)
        total_bytes = sum(file.size for file in files)
        completed = 0
        downloaded_bytes = 0
        _update_progress(
            source=source,
            total_files=len(files),
            completed_files=0,
            total_bytes=total_bytes,
            downloaded_bytes=0,
            current_file=None,
            current_file_bytes=0,
            current_file_total_bytes=None,
            message=f"Downloading 0/{len(files)} files from {source}...",
        )
        for model_file in files:
            _raise_if_cancelled()
            local_file = target / Path(model_file.path)
            if local_file.exists() and (model_file.size == 0 or local_file.stat().st_size >= model_file.size):
                completed += 1
                downloaded_bytes += model_file.size or local_file.stat().st_size
                _update_progress(
                    source=source,
                    total_files=len(files),
                    completed_files=completed,
                    total_bytes=total_bytes,
                    downloaded_bytes=downloaded_bytes,
                    current_file=model_file.path,
                    current_file_bytes=model_file.size or local_file.stat().st_size,
                    current_file_total_bytes=model_file.size or None,
                    message=f"Downloaded {completed}/{len(files)} files.",
                )
                continue

            downloaded_file_bytes = download_fn(
                paths,
                target,
                model_file,
                total_files=len(files),
                completed_files=completed,
                total_bytes=total_bytes,
                completed_bytes_before_file=downloaded_bytes,
            )
            downloaded_bytes += model_file.size or downloaded_file_bytes
            completed += 1
            _update_progress(
                source=source,
                total_files=len(files),
                completed_files=completed,
                total_bytes=total_bytes,
                downloaded_bytes=downloaded_bytes,
                current_file=model_file.path,
                current_file_bytes=model_file.size or downloaded_file_bytes,
                current_file_total_bytes=model_file.size or None,
                message=f"Downloaded {completed}/{len(files)} files.",
            )

        if not _is_downloaded(target):
            raise RuntimeError(f"Download finished but config.yaml was not found in {target}")

        _set_state(
            downloading=False,
            source=source,
            error=None,
            message=f"IndexTTS2 model downloaded from {source}.",
            total_files=len(files),
            completed_files=len(files),
            remaining_files=0,
            total_bytes=total_bytes,
            downloaded_bytes=total_bytes,
            current_file=None,
            current_file_bytes=0,
            current_file_total_bytes=None,
            current_file_progress_percent=None,
            progress_percent=100.0,
        )
    except Exception as exc:
        cancelled = _download_cancel_event.is_set()
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        with _download_lock:
            total_files = _download_state.get("total_files")
            completed_files = _download_state.get("completed_files") or 0
            remaining_files = _download_state.get("remaining_files")
            total_bytes = _download_state.get("total_bytes")
            downloaded_bytes = _download_state.get("downloaded_bytes") or 0
            current_file = _download_state.get("current_file")
            current_file_bytes = _download_state.get("current_file_bytes") or 0
            current_file_total_bytes = _download_state.get("current_file_total_bytes")
            current_file_progress_percent = _download_state.get("current_file_progress_percent")
            progress_percent = _download_state.get("progress_percent")
        _set_state(
            downloading=False,
            source=source,
            error=None if cancelled else str(exc),
            message="Download stopped." if cancelled else "Download failed.",
            total_files=int(total_files) if isinstance(total_files, int) else None,
            completed_files=int(completed_files) if isinstance(completed_files, int) else 0,
            remaining_files=int(remaining_files) if isinstance(remaining_files, int) else None,
            total_bytes=int(total_bytes) if isinstance(total_bytes, int) else None,
            downloaded_bytes=int(downloaded_bytes) if isinstance(downloaded_bytes, int) else 0,
            current_file=str(current_file) if current_file else None,
            current_file_bytes=int(current_file_bytes) if isinstance(current_file_bytes, int) else 0,
            current_file_total_bytes=int(current_file_total_bytes) if isinstance(current_file_total_bytes, int) else None,
            current_file_progress_percent=(
                float(current_file_progress_percent)
                if isinstance(current_file_progress_percent, int | float)
                else None
            ),
            progress_percent=float(progress_percent) if isinstance(progress_percent, int | float) else None,
            cancel_requested=cancelled,
        )


# ---------------------------------------------------------------------------
# Status response
# ---------------------------------------------------------------------------

def _model_status_response(paths: RuntimePaths) -> ModelStatusResponse:
    snapshot_dir = _snapshot_dir(paths)
    with _download_lock:
        downloading = bool(_download_state["downloading"])
        source = str(_download_state["source"] or "modelscope")
        error = _download_state["error"]
        message = _download_state["message"]
        total_files = _download_state["total_files"]
        completed_files = _download_state["completed_files"]
        remaining_files = _download_state["remaining_files"]
        total_bytes = _download_state["total_bytes"]
        downloaded_bytes = _download_state["downloaded_bytes"]
        current_file = _download_state["current_file"]
        current_file_bytes = _download_state["current_file_bytes"]
        current_file_total_bytes = _download_state["current_file_total_bytes"]
        current_file_progress_percent = _download_state["current_file_progress_percent"]
        progress_percent = _download_state["progress_percent"]
        cancel_requested = _download_state["cancel_requested"]
    return ModelStatusResponse(
        model_source=source,
        model_dir=str(snapshot_dir),
        downloaded=_is_downloaded(snapshot_dir),
        downloading=downloading,
        total_files=int(total_files) if isinstance(total_files, int) else None,
        completed_files=int(completed_files) if isinstance(completed_files, int) else 0,
        remaining_files=int(remaining_files) if isinstance(remaining_files, int) else None,
        total_bytes=int(total_bytes) if isinstance(total_bytes, int) else None,
        downloaded_bytes=int(downloaded_bytes) if isinstance(downloaded_bytes, int) else 0,
        current_file=str(current_file) if current_file else None,
        current_file_bytes=int(current_file_bytes) if isinstance(current_file_bytes, int) else 0,
        current_file_total_bytes=int(current_file_total_bytes) if isinstance(current_file_total_bytes, int) else None,
        current_file_progress_percent=(
            float(current_file_progress_percent)
            if isinstance(current_file_progress_percent, int | float)
            else None
        ),
        progress_percent=float(progress_percent) if isinstance(progress_percent, int | float) else None,
        cancel_requested=bool(cancel_requested),
        error=str(error) if error else None,
        message=str(message) if message else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=ModelListResponse)
def list_models(request: Request) -> ModelListResponse:
    return ModelListResponse(items=[_model_status_response(request.app.state.paths)])


@router.get("/", response_model=ModelListResponse)
def list_models_slash(request: Request) -> ModelListResponse:
    return list_models(request)


@router.get("/status", response_model=ModelStatusResponse)
def model_status(request: Request) -> ModelStatusResponse:
    return _model_status_response(request.app.state.paths)


def _queue_download(paths: RuntimePaths, background_tasks: BackgroundTasks, source: str) -> None:
    with _download_lock:
        already_downloading = bool(_download_state["downloading"])
    if not already_downloading:
        _download_cancel_event.clear()
        _set_state(downloading=True, source=source, error=None, message="Download queued.")
        background_tasks.add_task(_download_model, paths, source)


@router.post("/download", response_model=ModelStatusResponse)
def download_default_model(
    request: Request,
    background_tasks: BackgroundTasks,
    source: str = Query("modelscope"),
) -> ModelStatusResponse:
    if source not in SOURCES:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
    _queue_download(request.app.state.paths, background_tasks, source)
    return _model_status_response(request.app.state.paths)


@router.post("/{model_name}/download", response_model=ModelStatusResponse)
def download_model(
    model_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
    source: str = Query("modelscope"),
) -> ModelStatusResponse:
    if model_name != MODEL_NAME:
        raise HTTPException(status_code=404, detail="Unknown model.")
    if source not in SOURCES:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
    _queue_download(request.app.state.paths, background_tasks, source)
    return _model_status_response(request.app.state.paths)


@router.post("/{model_name}/stop", response_model=ModelStatusResponse)
def stop_model_download(model_name: str, request: Request) -> ModelStatusResponse:
    if model_name != MODEL_NAME:
        raise HTTPException(status_code=404, detail="Unknown model.")
    with _download_lock:
        if not bool(_download_state["downloading"]):
            return _model_status_response(request.app.state.paths)
        _download_state["cancel_requested"] = True
        _download_state["message"] = "Stopping download..."
    _download_cancel_event.set()
    return _model_status_response(request.app.state.paths)


@router.delete("/{model_name}", response_model=ModelStatusResponse)
def delete_model(model_name: str, request: Request) -> ModelStatusResponse:
    if model_name != MODEL_NAME:
        raise HTTPException(status_code=404, detail="Unknown model.")
    with _download_lock:
        if bool(_download_state["downloading"]):
            raise HTTPException(status_code=409, detail="Cannot delete a model while it is downloading.")

    paths = request.app.state.paths
    snapshot_dir = _snapshot_dir(paths)
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    if snapshot_dir.parent.exists() and not any(snapshot_dir.parent.iterdir()):
        snapshot_dir.parent.rmdir()
    _set_state(downloading=False, error=None, message="IndexTTS2 model deleted.")
    return _model_status_response(request.app.state.paths)
