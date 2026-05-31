set shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Start the development environment.
# - Creates backend/.venv if missing
# - Installs backend and frontend dependencies if missing
# - Starts FastAPI on 127.0.0.1:17493
# - Starts Tauri desktop if Cargo is installed, otherwise starts the Vite web UI
dev:
    python scripts/dev.py

# Start only the FastAPI backend.
backend-dev:
    python scripts/dev.py --backend-only

# Start only the frontend web UI.
app-dev:
    python scripts/dev.py --frontend-only

# Run available scaffold checks.
check:
    python scripts/dev.py --check
