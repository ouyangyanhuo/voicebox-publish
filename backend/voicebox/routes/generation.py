from __future__ import annotations

import uuid

from fastapi import APIRouter, Request

from ..database import connect
from ..schemas import GenerationRequest, GenerationResponse

router = APIRouter()


@router.post("", response_model=GenerationResponse)
def generate(request: Request, payload: GenerationRequest) -> GenerationResponse:
    generation_id = str(uuid.uuid4())
    with connect(request.app.state.paths.database_path) as conn:
        conn.execute(
            """
            INSERT INTO generations (id, role_id, text, language, status, emotion_snapshot)
            VALUES (?, ?, ?, ?, 'queued', ?)
            """,
            (generation_id, payload.role_id, payload.text, payload.language, payload.model_dump_json()),
        )
    return GenerationResponse(
        id=generation_id,
        status="queued",
        message="Generation queue scaffold created. IndexTTS2 worker is not wired yet.",
    )
