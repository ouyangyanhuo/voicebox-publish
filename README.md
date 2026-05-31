# AudioScribe

AudioScribe is being rebuilt as a local desktop TTS authoring app using IndexTTS2 as the only speech generation engine.

Core stack:

- Backend: Python + FastAPI.
- Frontend: Tauri + TypeScript + React.
- TTS: IndexTTS2 through an isolated worker runtime.
- Model downloads: ModelScope by default.

The current repository state is the framework scaffold. See [PROJECT_DEVELOPMENT.md](PROJECT_DEVELOPMENT.md) for the full development plan.

## Development Layout

```text
backend/              FastAPI backend and IndexTTS2 worker scaffold
app/                  Tauri + TypeScript frontend
preset-voices/        Local preset voice manifest and audio folder
docs/                 implementation audits and development notes
```

## Next Implementation Gate

Before implementing real IndexTTS2 inference code, complete `docs/INDEXTTS2_DEPENDENCY_AUDIT.md` according to the `add-tts-engine` skill constraints.

## Start Development

Install `just`, Python, and Bun. Rust/Cargo is optional for the Tauri desktop shell.

```powershell
cd F:\Project\audioscribe
just dev
```

`just dev` starts the FastAPI backend on `http://127.0.0.1:17493` and uses Bun for all frontend commands. If Rust/Cargo is available it starts the Tauri desktop app; otherwise it starts the Vite web UI at `http://127.0.0.1:1420`.

If Bun is not available:

```powershell
powershell -c "irm bun.sh/install.ps1 | iex"
```

Then reopen PowerShell and run `just dev` again.

Useful commands:

```powershell
just backend-dev
just app-dev
just check
just build
```

## Packaging

`just build` builds the FastAPI backend as a Tauri sidecar and then runs the Tauri desktop bundle build.

```powershell
just build
```

Build output is written under:

```text
app/src-tauri/target/release/bundle/
```

The IndexTTS2 worker packaging is still a planned release step; the current build command packages the scaffolded FastAPI backend sidecar, frontend, Tauri shell, and `preset-voices/` resources.
