from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import dev


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "backend" / "indextts2_worker"
WORKER_VENV = WORKER / ".venv"
RESEARCH = ROOT / "cache" / "research" / "index-tts"
REPO_URL = "https://github.com/index-tts/index-tts.git"


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"[indextts2] {' '.join(command)}", flush=True)
    subprocess.check_call(command, cwd=str(cwd), env=env)


def worker_python() -> Path:
    if os.name == "nt":
        return WORKER_VENV / "Scripts" / "python.exe"
    return WORKER_VENV / "bin" / "python"


def setup_env() -> dict[str, str]:
    env = dev.local_tool_env()
    env["UV_CACHE_DIR"] = str(ROOT / "cache" / "uv")
    env["PIP_CACHE_DIR"] = str(ROOT / "cache" / "pip")
    env["TEMP"] = str(ROOT / "cache" / "tmp")
    env["TMP"] = str(ROOT / "cache" / "tmp")
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["UV_PROJECT_ENVIRONMENT"] = str(WORKER_VENV)
    for key in ("UV_CACHE_DIR", "PIP_CACHE_DIR", "TEMP"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    return env


def ensure_uv() -> str:
    uv = shutil.which("uv")
    if uv:
        return uv
    print("[indextts2] uv not found; installing uv into the main backend venv", flush=True)
    python = dev.ensure_backend_env()
    run([str(python), "-m", "pip", "install", "uv"], env=setup_env())
    uv = shutil.which("uv")
    if uv:
        return uv
    scripts_uv = python.parent / ("uv.exe" if os.name == "nt" else "uv")
    if scripts_uv.exists():
        return str(scripts_uv)
    raise RuntimeError("uv installation completed but uv executable was not found")


def ensure_source() -> None:
    if (RESEARCH / "pyproject.toml").exists():
        return
    if RESEARCH.exists():
        shutil.rmtree(RESEARCH)
    RESEARCH.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", REPO_URL, str(RESEARCH)], env=setup_env())


def sync_worker() -> None:
    uv = ensure_uv()
    ensure_source()
    WORKER.mkdir(parents=True, exist_ok=True)
    run(
        [
            uv,
            "sync",
            "--active",
            "--no-extra",
            "webui",
            "--no-extra",
            "deepspeed",
        ],
        cwd=RESEARCH,
        env=setup_env(),
    )
    run(
        [
            uv,
            "pip",
            "install",
            "--python",
            str(worker_python()),
            "-r",
            str(WORKER / "requirements.txt"),
        ],
        env=setup_env(),
    )


def main() -> int:
    try:
        if not worker_python().exists():
            run([sys.executable, "-m", "venv", str(WORKER_VENV)], env=setup_env())
        sync_worker()
        print(f"[indextts2] Worker Python: {worker_python()}", flush=True)
        print("[indextts2] Download the model to model/modelscope/IndexTeam/IndexTTS-2 before generating.", flush=True)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"[indextts2] Command failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except RuntimeError as exc:
        print(f"[indextts2] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
