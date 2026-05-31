from __future__ import annotations

import uuid

from fastapi import APIRouter, Request

from ..database import connect
from ..schemas import StoryCreate, StoryResponse

router = APIRouter()


@router.get("", response_model=list[StoryResponse])
def list_stories(request: Request) -> list[StoryResponse]:
    with connect(request.app.state.paths.database_path) as conn:
        rows = conn.execute(
            """
            SELECT stories.*, COUNT(story_lines.id) AS line_count
            FROM stories
            LEFT JOIN story_lines ON story_lines.story_id = stories.id
            GROUP BY stories.id
            ORDER BY stories.updated_at DESC
            """
        ).fetchall()
    return [
        StoryResponse(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            line_count=row["line_count"],
        )
        for row in rows
    ]


@router.post("", response_model=StoryResponse)
def create_story(request: Request, payload: StoryCreate) -> StoryResponse:
    story_id = str(uuid.uuid4())
    with connect(request.app.state.paths.database_path) as conn:
        conn.execute(
            "INSERT INTO stories (id, title, description) VALUES (?, ?, ?)",
            (story_id, payload.title, payload.description),
        )
    return StoryResponse(id=story_id, line_count=0, **payload.model_dump())
