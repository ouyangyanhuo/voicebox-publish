from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import initialize_runtime
from .database import initialize_database
from .routes import emotion, generation, health, models, preset_voices, roles, settings, stories


def create_app() -> FastAPI:
    paths = initialize_runtime()
    initialize_database(paths.database_path)

    app = FastAPI(title="Voicebox API", version=__version__)
    app.state.paths = paths

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:1420", "http://127.0.0.1:1420", "tauri://localhost"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(settings.router, prefix="/settings", tags=["settings"])
    app.include_router(models.router, prefix="/models", tags=["models"])
    app.include_router(roles.router, prefix="/roles", tags=["roles"])
    app.include_router(generation.router, prefix="/generate", tags=["generation"])
    app.include_router(stories.router, prefix="/stories", tags=["stories"])
    app.include_router(emotion.router, prefix="/emotion-presets", tags=["emotion"])
    app.include_router(preset_voices.router, prefix="/preset-voices", tags=["preset-voices"])
    return app
