from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..database import connect
from ..schemas import UploadedGenerationAudioResponse

router = APIRouter()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".webm", ".m4a"}


def _safe_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported audio file type")
    return ext


@router.post("", response_model=UploadedGenerationAudioResponse)
def upload_generation_audio(request: Request, file: UploadFile = File(...)) -> UploadedGenerationAudioResponse:
    item_id = str(uuid.uuid4())
    ext = _safe_extension(file.filename or "")
    target_dir = request.app.state.paths.audio_library_dir / "generation-inputs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{item_id}{ext}"

    with target_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    with connect(request.app.state.paths.database_path) as conn:
        conn.execute(
            """
            INSERT INTO audio_library_items (id, name, audio_path, source)
            VALUES (?, ?, ?, 'generation')
            """,
            (item_id, file.filename or target_path.name, str(target_path)),
        )

    return UploadedGenerationAudioResponse(
        id=item_id,
        file_name=file.filename or target_path.name,
        audio_url=f"/generation-audio/{item_id}/audio",
    )


@router.get("/{audio_id}/audio")
def get_generation_input_audio(request: Request, audio_id: str):
    with connect(request.app.state.paths.database_path) as conn:
        row = conn.execute("SELECT * FROM audio_library_items WHERE id = ?", (audio_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    audio_path = Path(row["audio_path"]).resolve()
    install_dir = request.app.state.paths.install_dir.resolve()
    if install_dir not in audio_path.parents or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, filename=row["name"])
