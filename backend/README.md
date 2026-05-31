# Backend

FastAPI backend scaffold for the AudioScribe rewrite.

Runtime storage is install-local only. The backend reads `AUDIOSCRIBE_INSTALL_DIR`; if it is unset, it uses the repository root in development.

## Dev

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:AUDIOSCRIBE_INSTALL_DIR=(Get-Location).Path
.\.venv\Scripts\uvicorn audioscribe.app:create_app --factory --reload --host 127.0.0.1 --port 17493
```
