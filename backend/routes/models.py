"""Model management endpoints."""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models
from ..services.task_queue import create_background_task
from ..utils.progress import get_progress_manager
from ..utils.tasks import get_task_manager

router = APIRouter()


def _get_dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def _copy_with_progress(src: Path, dst: Path, progress_manager, copied_so_far: int, total_bytes: int) -> int:
    """Copy a directory tree with byte-level progress tracking."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        dest_item = dst / item.name
        if item.is_dir():
            copied_so_far = _copy_with_progress(item, dest_item, progress_manager, copied_so_far, total_bytes)
        else:
            size = item.stat().st_size
            shutil.copy2(str(item), str(dest_item))
            copied_so_far += size
            progress_manager.update_progress(
                "migration",
                copied_so_far,
                total_bytes,
                filename=item.name,
                status="downloading",
            )
    return copied_so_far


@router.post("/models/load")
async def load_model(model_size: str = "default"):
    """Manually prepare the IndexTTS2 model snapshot."""
    from ..services import tts

    try:
        tts_model = tts.get_tts_model()
        result = tts_model.load_model(model_size)
        if asyncio.iscoroutine(result):
            await result
        return {"message": f"Model {model_size} loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/unload")
async def unload_model():
    """Unload the default IndexTTS2 backend handle."""
    from ..services import tts

    try:
        tts.unload_tts_model()
        return {"message": "Model unloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_name}/unload")
async def unload_model_by_name(model_name: str):
    """Unload a specific model from memory without deleting it from disk."""
    from ..backends import get_model_config, unload_model_by_config

    config = get_model_config(model_name)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

    try:
        was_loaded = unload_model_by_config(config)
        if not was_loaded:
            return {"message": f"Model {model_name} is not loaded"}
        return {"message": f"Model {model_name} unloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/models/progress/{model_name}")
async def get_model_progress(model_name: str):
    """Get model download progress via Server-Sent Events."""
    progress_manager = get_progress_manager()

    async def event_generator():
        async for event in progress_manager.subscribe(model_name):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models/cache-dir")
async def get_models_cache_dir():
    """Get the active install-local model cache directory."""
    from ..services.model_sources import get_active_model_cache_dir, get_model_source

    return {"path": str(get_active_model_cache_dir()), "source": get_model_source()}


@router.post("/models/migrate")
async def migrate_models(request: models.ModelMigrateRequest):
    """Legacy endpoint kept for older clients; model storage is no longer movable."""
    raise HTTPException(status_code=410, detail="Model storage is fixed to the install directory and cannot be changed.")


@router.get("/models/migrate/progress")
async def get_migration_progress():
    """Get model migration progress via Server-Sent Events."""
    progress_manager = get_progress_manager()

    async def event_generator():
        async for event in progress_manager.subscribe("migration"):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models/status", response_model=models.ModelStatusListResponse)
async def get_model_status():
    """Get status of all available models."""
    task_manager = get_task_manager()

    active_download_names = {task.model_name for task in task_manager.get_active_downloads()}

    from ..backends import get_all_model_configs, check_model_loaded
    from ..services.model_sources import get_model_cache_dir_for_repo, is_model_cached

    registry_configs = get_all_model_configs()
    model_configs = [
        {
            "model_name": cfg.model_name,
            "display_name": cfg.display_name,
            "hf_repo_id": cfg.hf_repo_id,
            "model_size": cfg.model_size,
            "check_loaded": lambda c=cfg: check_model_loaded(c),
        }
        for cfg in registry_configs
    ]

    model_to_repo = {cfg["model_name"]: cfg["hf_repo_id"] for cfg in model_configs}
    active_download_repos = {model_to_repo.get(name) for name in active_download_names if name in model_to_repo}

    statuses = []

    for config in model_configs:
        try:
            downloaded = is_model_cached(config["hf_repo_id"], weight_extensions=(".safetensors", ".bin", ".pt", ".pth", ".npz"))
            size_mb = None
            loaded = False

            if downloaded:
                try:
                    repo_cache = get_model_cache_dir_for_repo(config["hf_repo_id"])
                    if repo_cache.exists():
                        total_size = sum(
                            f.stat().st_size
                            for f in repo_cache.rglob("*")
                            if f.is_file() and not f.name.endswith(".incomplete")
                        )
                        size_mb = total_size / (1024 * 1024)
                except Exception:
                    pass

            try:
                loaded = config["check_loaded"]()
            except Exception:
                loaded = False

            is_downloading = config["hf_repo_id"] in active_download_repos

            if is_downloading:
                downloaded = False
                size_mb = None

            statuses.append(
                models.ModelStatus(
                    model_name=config["model_name"],
                    display_name=config["display_name"],
                    hf_repo_id=config["hf_repo_id"],
                    downloaded=downloaded,
                    downloading=is_downloading,
                    size_mb=size_mb,
                    loaded=loaded,
                )
            )
        except Exception:
            try:
                loaded = config["check_loaded"]()
            except Exception:
                loaded = False

            is_downloading = config["hf_repo_id"] in active_download_repos

            statuses.append(
                models.ModelStatus(
                    model_name=config["model_name"],
                    display_name=config["display_name"],
                    hf_repo_id=config["hf_repo_id"],
                    downloaded=False,
                    downloading=is_downloading,
                    size_mb=None,
                    loaded=loaded,
                )
            )

    return models.ModelStatusListResponse(models=statuses)


@router.post("/models/download")
async def trigger_model_download(request: models.ModelDownloadRequest):
    """Trigger download of a specific model."""
    from ..backends import get_model_config, get_model_load_func

    task_manager = get_task_manager()
    progress_manager = get_progress_manager()

    config = get_model_config(request.model_name)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model_name}")

    load_func = get_model_load_func(config)

    async def download_in_background():
        try:
            result = load_func()
            if asyncio.iscoroutine(result):
                await result
            task_manager.complete_download(request.model_name)
        except Exception as e:
            task_manager.error_download(request.model_name, str(e))

    task_manager.start_download(request.model_name)

    progress_manager.update_progress(
        model_name=request.model_name,
        current=0,
        total=0,
        filename="Connecting to model source...",
        status="downloading",
    )

    create_background_task(download_in_background())

    return {"message": f"Model {request.model_name} download started"}


@router.post("/models/download/cancel")
async def cancel_model_download(request: models.ModelDownloadRequest):
    """Cancel or dismiss an errored/stale download task."""
    task_manager = get_task_manager()
    progress_manager = get_progress_manager()

    removed = task_manager.cancel_download(request.model_name)

    progress_removed = False
    with progress_manager._lock:
        if request.model_name in progress_manager._progress:
            del progress_manager._progress[request.model_name]
            progress_removed = True

    if removed or progress_removed:
        return {"message": f"Download task for {request.model_name} cancelled"}
    return {"message": f"No active task found for {request.model_name}"}


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a downloaded model from the active install-local model cache."""
    from ..backends import get_model_config, unload_model_by_config
    from ..services.model_sources import get_model_cache_dir_for_repo

    config = get_model_config(model_name)
    if not config:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

    hf_repo_id = config.hf_repo_id

    try:
        unload_model_by_config(config)

        repo_cache_dir = get_model_cache_dir_for_repo(hf_repo_id)

        if not repo_cache_dir.exists():
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found in cache")

        try:
            shutil.rmtree(repo_cache_dir)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete model cache directory: {str(e)}")

        return {"message": f"Model {model_name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")
