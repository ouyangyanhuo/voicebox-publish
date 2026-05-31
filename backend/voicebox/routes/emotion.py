from __future__ import annotations

import uuid

import json

from fastapi import APIRouter, Request

from ..database import connect
from ..schemas import EmotionPresetCreate, EmotionPresetResponse

router = APIRouter()


@router.get("", response_model=list[EmotionPresetResponse])
def list_presets(request: Request) -> list[EmotionPresetResponse]:
    with connect(request.app.state.paths.database_path) as conn:
        rows = conn.execute("SELECT * FROM emotion_presets ORDER BY updated_at DESC").fetchall()
    return [
        EmotionPresetResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            emo_alpha=row["emo_alpha"],
            emo_vector=[0.0] * 8 if row["emo_vector"] is None else json.loads(row["emo_vector"]),
            emo_text=row["emo_text"],
        )
        for row in rows
    ]


@router.post("", response_model=EmotionPresetResponse)
def create_preset(request: Request, payload: EmotionPresetCreate) -> EmotionPresetResponse:
    preset_id = str(uuid.uuid4())
    with connect(request.app.state.paths.database_path) as conn:
        conn.execute(
            """
            INSERT INTO emotion_presets (id, name, description, emo_alpha, emo_vector, emo_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                preset_id,
                payload.name,
                payload.description,
                payload.emo_alpha,
                json.dumps(payload.emo_vector),
                payload.emo_text,
            ),
        )
    return EmotionPresetResponse(id=preset_id, **payload.model_dump())
