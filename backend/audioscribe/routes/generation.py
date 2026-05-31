from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse

from ..database import connect
from ..schemas import GenerationRequest, GenerationResponse, GenerationStatusResponse
from ..services.generation_runner import GenerationError, resolve_reference_audio, run_generation_task

router = APIRouter()


@router.post("", response_model=GenerationResponse)
def generate(request: Request, payload: GenerationRequest, background_tasks: BackgroundTasks) -> GenerationResponse:
    paths = request.app.state.paths
    try:
        speaker_audio = resolve_reference_audio(paths, payload)
        emo_audio_prompt = None
        if payload.emo_audio_id:
            emo_audio_prompt = str(resolve_reference_audio(paths, payload.model_copy(update={
                "audio_source": "upload",
                "uploaded_audio_id": payload.emo_audio_id,
            })))
    except GenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with connect(paths.database_path) as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    settings = {
        "gpu_mode": row["gpu_mode"],
        "use_fp16": bool(row["use_fp16"]),
        "use_cuda_kernel": bool(row["use_cuda_kernel"]),
        "use_deepspeed": bool(row["use_deepspeed"]),
    }
    params = payload.model_dump()
    params["speaker_audio"] = str(speaker_audio)
    params["emo_audio_prompt"] = emo_audio_prompt
    params["settings"] = settings

    generation_id = str(uuid.uuid4())
    with connect(paths.database_path) as conn:
        conn.execute(
            """
            INSERT INTO generations (
              id, role_id, text, language, status, emotion_snapshot, parameters_snapshot
            )
            VALUES (?, ?, ?, ?, 'queued', ?, ?)
            """,
            (
                generation_id,
                payload.role_id,
                payload.text,
                payload.language,
                payload.model_dump_json(),
                json.dumps(params, ensure_ascii=False),
            ),
        )
    background_tasks.add_task(run_generation_task, paths, generation_id)
    return GenerationResponse(
        id=generation_id,
        status="queued",
        message="Generation task queued.",
    )


@router.get("/{generation_id}", response_model=GenerationStatusResponse)
def get_generation(request: Request, generation_id: str) -> GenerationStatusResponse:
    with connect(request.app.state.paths.database_path) as conn:
        row = conn.execute("SELECT * FROM generations WHERE id = ?", (generation_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Generation not found")
    audio_url = f"/generate/{generation_id}/audio" if row["status"] == "completed" and row["audio_path"] else None
    return GenerationStatusResponse(
        id=row["id"],
        status=row["status"],
        text=row["text"],
        language=row["language"],
        audio_url=audio_url,
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{generation_id}/audio")
def get_generation_audio(request: Request, generation_id: str):
    with connect(request.app.state.paths.database_path) as conn:
        row = conn.execute("SELECT * FROM generations WHERE id = ?", (generation_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Generation not found")
    if row["status"] != "completed" or not row["audio_path"]:
        raise HTTPException(status_code=409, detail="Generation audio is not ready")
    audio_path = request.app.state.paths.generated_audio_dir / f"{generation_id}.wav"
    if not audio_path.exists() or str(audio_path.resolve()) != str(row["audio_path"]):
        raise HTTPException(status_code=404, detail="Generation audio file not found")
    return FileResponse(audio_path, media_type="audio/wav", filename=f"{generation_id}.wav")
