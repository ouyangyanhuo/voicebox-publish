from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
APP = ROOT / "app"
LOCAL_CACHE = ROOT / "cache"
BACKEND_VENV = BACKEND / ".venv"
BACKEND_PORT = "17493"
FRONTEND_PORT = "1420"


def venv_python() -> Path:
    if os.name == "nt":
        return BACKEND_VENV / "Scripts" / "python.exe"
    return BACKEND_VENV / "bin" / "python"


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print(f"[dev] {' '.join(command)}", flush=True)
    subprocess.check_call(command, cwd=str(cwd), env=env)


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_bun() -> str | None:
    explicit = os.environ.get("AUDIOSCRIBE_BUN_BIN")
    if explicit:
        explicit_path = Path(explicit)
        if explicit_path.exists():
            return str(explicit_path)
        found = shutil.which(explicit)
        if found:
            return found

    found = shutil.which("bun") or shutil.which("bun.exe")
    if found:
        return found

    if os.name != "nt":
        return None

    candidates: list[Path] = []
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / ".bun" / "bin" / "bun.exe")
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Programs" / "bun" / "bun.exe")

    bun = first_existing(candidates)
    return str(bun) if bun else None


def bun_command() -> str:
    bun = find_bun()
    if bun:
        return bun

    raise RuntimeError(
        "Bun was not found. Install Bun and reopen the terminal, then run `just dev` again.\n"
        "Windows quick install: powershell -c \"irm bun.sh/install.ps1 | iex\"\n"
        "If Bun is installed outside PATH, set AUDIOSCRIBE_BUN_BIN to the full bun.exe path."
    )


def frontend_install_command() -> list[str]:
    return [bun_command(), "install"]


def frontend_script_command(script: str, args: list[str] | None = None) -> list[str]:
    script_args = args or []
    return [bun_command(), "run", script, *script_args]


def tauri_command(args: list[str]) -> list[str]:
    return [bun_command(), str(APP / "node_modules" / "@tauri-apps" / "cli" / "tauri.js"), *args]


def local_tool_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(LOCAL_CACHE / "pip")
    env["BUN_INSTALL_CACHE_DIR"] = str(LOCAL_CACHE / "bun")
    env["TEMP"] = str(LOCAL_CACHE / "tmp")
    env["TMP"] = str(LOCAL_CACHE / "tmp")
    return env


def ensure_backend_env() -> Path:
    (LOCAL_CACHE / "pip").mkdir(parents=True, exist_ok=True)
    python = venv_python()
    if not python.exists():
        print("[dev] Creating backend virtual environment", flush=True)
        run([sys.executable, "-m", "venv", str(BACKEND_VENV)])

    probe = subprocess.run(
        [str(python), "-c", "import fastapi, uvicorn"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode != 0:
        print("[dev] Installing backend dependencies", flush=True)
        run(
            [str(python), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")],
            env=local_tool_env(),
        )
    return python


def ensure_frontend_env() -> None:
    vite_bin = APP / "node_modules" / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if vite_bin.exists():
        return
    (LOCAL_CACHE / "bun").mkdir(parents=True, exist_ok=True)
    (LOCAL_CACHE / "tmp").mkdir(parents=True, exist_ok=True)
    print("[dev] Installing frontend dependencies with bun", flush=True)
    run(frontend_install_command(), cwd=APP, env=local_tool_env())


def dev_env() -> dict[str, str]:
    env = os.environ.copy()
    env["BUN_INSTALL_CACHE_DIR"] = str(LOCAL_CACHE / "bun")
    env["PIP_CACHE_DIR"] = str(LOCAL_CACHE / "pip")
    env["TEMP"] = str(LOCAL_CACHE / "tmp")
    env["TMP"] = str(LOCAL_CACHE / "tmp")
    Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)
    env["AUDIOSCRIBE_INSTALL_DIR"] = str(ROOT)
    env["VITE_API_BASE_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def subprocess_creationflags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return 0


def start_backend(python: Path) -> subprocess.Popen:
    command = [
        str(python),
        "-m",
        "uvicorn",
        "audioscribe.app:create_app",
        "--factory",
        "--app-dir",
        str(BACKEND),
        "--reload-dir",
        str(BACKEND),
        "--host",
        "127.0.0.1",
        "--port",
        BACKEND_PORT,
        "--reload",
    ]
    print(f"[dev] Starting backend on http://127.0.0.1:{BACKEND_PORT}", flush=True)
    return subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=dev_env(),
        creationflags=subprocess_creationflags(),
    )


def wait_for_backend(process: subprocess.Popen) -> None:
    url = f"http://127.0.0.1:{BACKEND_PORT}/health"
    deadline = time.time() + 45
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend exited early with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    print(f"[dev] Backend ready: {url}", flush=True)
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    raise RuntimeError("Backend did not become ready within 45 seconds")


def frontend_command() -> list[str]:
    if command_exists("cargo"):
        print("[dev] Cargo found; starting Tauri desktop app", flush=True)
        return tauri_command(["dev"])
    print("[dev] Cargo not found; starting Vite web UI instead", flush=True)
    print(f"[dev] Open http://127.0.0.1:{FRONTEND_PORT}", flush=True)
    return frontend_script_command("dev", ["--host", "127.0.0.1"])


def terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        if hasattr(signal, "CTRL_BREAK_EVENT"):
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
    else:
        process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--frontend-only", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    selected_modes = sum([args.backend_only, args.frontend_only, args.check])
    if selected_modes > 1:
        raise RuntimeError("Use only one of --backend-only, --frontend-only, or --check.")

    if args.check:
        backend_python = ensure_backend_env()
        run([str(backend_python), "-m", "compileall", str(BACKEND)], env=local_tool_env())
        ensure_frontend_env()
        run(
            frontend_script_command("typecheck"),
            cwd=APP,
            env=local_tool_env(),
        )
        return 0

    if args.frontend_only:
        ensure_frontend_env()
        command = frontend_command()
        return subprocess.call(command, cwd=str(APP), env=dev_env())

    backend_python = ensure_backend_env()
    if not args.backend_only:
        ensure_frontend_env()

    backend_process = start_backend(backend_python)
    try:
        wait_for_backend(backend_process)
        if args.backend_only:
            print("[dev] Backend-only mode. Press Ctrl+C to stop.", flush=True)
            return backend_process.wait()

        command = frontend_command()
        frontend_process = subprocess.Popen(command, cwd=str(APP), env=dev_env())
        return frontend_process.wait()
    except KeyboardInterrupt:
        print("[dev] Stopping...", flush=True)
        return 130
    finally:
        terminate(backend_process)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"[dev] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        print(f"[dev] Command failed with exit code {exc.returncode}", file=sys.stderr, flush=True)
        raise SystemExit(exc.returncode)
