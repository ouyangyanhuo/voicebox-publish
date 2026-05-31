from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

import dev


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
BACKEND = ROOT / "backend"
TAURI = APP / "src-tauri"
BINARIES = TAURI / "binaries"
BUILD = ROOT / "build"
PYINSTALLER = BUILD / "pyinstaller"
TARGET_TRIPLE = "x86_64-pc-windows-msvc" if os.name == "nt" else ""


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"[build] {' '.join(command)}", flush=True)
    subprocess.check_call(command, cwd=str(cwd), env=env)


def ensure_pyinstaller(python: Path) -> None:
    probe = subprocess.run(
        [str(python), "-c", "import PyInstaller"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode != 0:
        run([str(python), "-m", "pip", "install", "pyinstaller>=6.11,<7"], env=dev.local_tool_env())


def backend_binary_name() -> str:
    suffix = ".exe" if os.name == "nt" else ""
    if TARGET_TRIPLE:
        return f"audioscribe-backend-{TARGET_TRIPLE}{suffix}"
    return f"audioscribe-backend{suffix}"


def pyinstaller_window_options() -> list[str]:
    if os.name == "nt":
        return ["--noconsole"]
    return []


def build_backend() -> Path:
    python = dev.ensure_backend_env()
    ensure_pyinstaller(python)

    dist = BUILD / "backend-dist"
    work = PYINSTALLER / "backend-work"
    spec = PYINSTALLER / "spec"
    dist.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    spec.mkdir(parents=True, exist_ok=True)

    run(
        [
            str(python),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            *pyinstaller_window_options(),
            "--name",
            "audioscribe-backend",
            "--distpath",
            str(dist),
            "--workpath",
            str(work),
            "--specpath",
            str(spec),
            "--paths",
            str(BACKEND),
            str(BACKEND / "audioscribe" / "server.py"),
        ],
        env=dev.local_tool_env(),
    )

    source = dist / ("audioscribe-backend.exe" if os.name == "nt" else "audioscribe-backend")
    if not source.exists():
        raise RuntimeError(f"Backend binary was not created: {source}")

    BINARIES.mkdir(parents=True, exist_ok=True)
    target = BINARIES / backend_binary_name()
    shutil.copy2(source, target)
    print(f"[build] Backend sidecar: {target}", flush=True)
    return target


def build_frontend() -> None:
    dev.ensure_frontend_env()
    run(dev.frontend_script_command("build"), cwd=APP, env=dev.local_tool_env())


def build_tauri() -> None:
    env = dev.dev_env()
    env["TAURI_CONFIG"] = json.dumps(
        {
            "bundle": {
                "externalBin": ["binaries/audioscribe-backend"],
            }
        }
    )
    run(dev.tauri_command(["build"]), cwd=APP, env=env)


def main() -> int:
    if os.name != "nt":
        print("[build] Non-Windows packaging is scaffolded but not finalized yet.", flush=True)

    build_backend()
    build_frontend()
    build_tauri()
    print(f"[build] Bundle output: {TAURI / 'target' / 'release' / 'bundle'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"[build] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        print(f"[build] Command failed with exit code {exc.returncode}", file=sys.stderr, flush=True)
        raise SystemExit(exc.returncode)
