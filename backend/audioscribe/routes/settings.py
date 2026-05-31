from __future__ import annotations

import subprocess
import threading

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..config import RuntimePaths
from ..database import connect
from ..schemas import InstallStatus, RuntimePathSummary, SettingsResponse, SettingsUpdate

router = APIRouter()

_install_lock = threading.Lock()
_install_state: dict[str, object] = {
    "installing": False,
    "package": None,
    "message": None,
    "log": None,
    "error": None,
    "done": False,
}


def _check_cuda() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _check_deepspeed() -> bool:
    try:
        import deepspeed
        return True
    except Exception:
        return False


def _worker_python(paths: RuntimePaths) -> str:
    import os
    explicit = os.environ.get("AUDIOSCRIBE_INDEXTTS2_PYTHON")
    if explicit:
        return explicit
    venv = paths.install_dir / "backend" / "indextts2_worker" / ".venv"
    if os.name == "nt":
        return str(venv / "Scripts" / "python.exe")
    return str(venv / "bin" / "python")


def _set_install_state(**kwargs) -> None:
    with _install_lock:
        for k, v in kwargs.items():
            _install_state[k] = v


def _run_install(pip_args: list[str], package_label: str, paths: RuntimePaths, extra_env: dict[str, str] | None = None) -> None:
    import os
    python = _worker_python(paths)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    _set_install_state(
        installing=True, package=package_label, message=f"Installing {package_label}...",
        log="", error=None, done=False,
    )
    try:
        proc = subprocess.run(
            ["uv", "pip", "install", "--python", python, *pip_args],
            cwd=str(paths.install_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60 * 30,
            check=False,
        )
        output = (proc.stdout or "")[-4000:]
        if proc.returncode != 0:
            _set_install_state(
                installing=False, package=package_label, message=f"{package_label} installation failed.",
                log=output, error=f"pip exited with code {proc.returncode}", done=True,
            )
        else:
            _set_install_state(
                installing=False, package=package_label, message=f"{package_label} installed successfully.",
                log=output, error=None, done=True,
            )
    except subprocess.TimeoutExpired:
        _set_install_state(
            installing=False, package=package_label, message=f"{package_label} installation timed out.",
            log=None, error="Timeout after 30 minutes", done=True,
        )
    except Exception as exc:
        _set_install_state(
            installing=False, package=package_label, message=f"{package_label} installation failed.",
            log=None, error=str(exc), done=True,
        )


def _path_summary(request: Request) -> RuntimePathSummary:
    paths = request.app.state.paths
    return RuntimePathSummary(
        install_dir=str(paths.install_dir),
        data_dir=str(paths.data_dir),
        cache_dir=str(paths.cache_dir),
        model_dir=str(paths.model_dir),
        logs_dir=str(paths.logs_dir),
        database_path=str(paths.database_path),
        generated_audio_dir=str(paths.generated_audio_dir),
        role_samples_dir=str(paths.role_samples_dir),
        preset_voice_dir=str(paths.preset_voice_dir),
        temp_dir=str(paths.temp_dir),
    )


def _get_install_status() -> InstallStatus | None:
    with _install_lock:
        if not _install_state["installing"] and not _install_state["done"]:
            return None
        return InstallStatus(**_install_state)


def _row_to_settings(request: Request, row) -> SettingsResponse:
    return SettingsResponse(
        model_source="modelscope",
        github_mirror_enabled=bool(row["github_mirror_enabled"]),
        gpu_mode=row["gpu_mode"],
        use_fp16=bool(row["use_fp16"]),
        use_cuda_kernel=bool(row["use_cuda_kernel"]),
        use_deepspeed=bool(row["use_deepspeed"]),
        paths=_path_summary(request),
        cuda_available=_check_cuda(),
        deepspeed_available=_check_deepspeed(),
        install_status=_get_install_status(),
    )


@router.get("", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    with connect(request.app.state.paths.database_path) as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        return _row_to_settings(request, row)


@router.put("", response_model=SettingsResponse)
def update_settings(request: Request, patch: SettingsUpdate) -> SettingsResponse:
    fields = patch.model_dump(exclude_unset=True)
    if fields:
        values = {
            key: int(value) if isinstance(value, bool) else value
            for key, value in fields.items()
        }
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        with connect(request.app.state.paths.database_path) as conn:
            conn.execute(
                f"UPDATE settings SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                values,
            )
    return get_settings(request)


@router.post("/install-cuda-torch", response_model=SettingsResponse)
def install_cuda_torch(request: Request, background_tasks: BackgroundTasks) -> SettingsResponse:
    with _install_lock:
        if _install_state["installing"]:
            raise HTTPException(status_code=409, detail="Another installation is in progress.")
    _set_install_state(done=False)
    background_tasks.add_task(
        _run_install,
        ["--reinstall", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124"],
        "CUDA PyTorch",
        request.app.state.paths,
    )
    return get_settings(request)


@router.post("/install-deepspeed", response_model=SettingsResponse)
def install_deepspeed(request: Request, background_tasks: BackgroundTasks) -> SettingsResponse:
    with _install_lock:
        if _install_state["installing"]:
            raise HTTPException(status_code=409, detail="Another installation is in progress.")
    _set_install_state(done=False)
    background_tasks.add_task(
        _run_install,
        ["--reinstall", "deepspeed"],
        "DeepSpeed",
        request.app.state.paths,
        {"DS_BUILD_OPS": "0"},
    )
    return get_settings(request)
