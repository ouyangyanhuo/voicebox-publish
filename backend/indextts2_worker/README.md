# IndexTTS2 Worker

The worker runtime is intentionally isolated from the main FastAPI backend. Do not import IndexTTS2 from the main backend process.

Real inference is launched by the main backend as a subprocess. By default it expects:

```text
backend/indextts2_worker/.venv/Scripts/python.exe
```

Override with `AUDIOSCRIBE_INDEXTTS2_PYTHON` if the worker Python lives elsewhere.

The worker must install the official `indextts` package from the audited repository with `uv`, then install `backend/indextts2_worker/requirements.txt` into the same venv for the worker wrapper dependencies. Run this from the project root:

```powershell
just setup-indextts2
```

The ModelScope snapshot must exist at:

```text
<install>/model/modelscope/IndexTeam/IndexTTS-2
```

All worker cache and temporary paths are forced under `<install>/cache`.
