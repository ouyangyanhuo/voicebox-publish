from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from .. import __version__
from ..schemas import DirectoryStatus, FilesystemHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


def _check_directory(path: Path) -> DirectoryStatus:
    error = None
    writable = False
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".voicebox_health_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        writable = True
    except OSError as exc:
        error = str(exc)
    return DirectoryStatus(path=str(path), exists=path.exists(), writable=writable, error=error)


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    paths = request.app.state.paths
    return HealthResponse(status="healthy", version=__version__, install_dir=str(paths.install_dir))


@router.get("/health/filesystem", response_model=FilesystemHealthResponse)
def filesystem_health(request: Request) -> FilesystemHealthResponse:
    paths = request.app.state.paths
    checks = [
        _check_directory(paths.data_dir),
        _check_directory(paths.cache_dir),
        _check_directory(paths.model_dir),
        _check_directory(paths.logs_dir),
    ]
    return FilesystemHealthResponse(
        healthy=all(item.exists and item.writable for item in checks),
        directories=checks,
    )
