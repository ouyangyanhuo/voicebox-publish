from __future__ import annotations

import uuid

from fastapi import APIRouter, Request

from ..database import connect
from ..schemas import RoleCreate, RoleResponse

router = APIRouter()


@router.get("", response_model=list[RoleResponse])
def list_roles(request: Request) -> list[RoleResponse]:
    with connect(request.app.state.paths.database_path) as conn:
        rows = conn.execute(
            """
            SELECT roles.*, COUNT(role_samples.id) AS sample_count
            FROM roles
            LEFT JOIN role_samples ON role_samples.role_id = roles.id
            GROUP BY roles.id
            ORDER BY roles.updated_at DESC
            """
        ).fetchall()
    return [
        RoleResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            language=row["language"],
            sample_count=row["sample_count"],
        )
        for row in rows
    ]


@router.post("", response_model=RoleResponse)
def create_role(request: Request, payload: RoleCreate) -> RoleResponse:
    role_id = str(uuid.uuid4())
    with connect(request.app.state.paths.database_path) as conn:
        conn.execute(
            "INSERT INTO roles (id, name, description, language) VALUES (?, ?, ?, ?)",
            (role_id, payload.name, payload.description, payload.language),
        )
    return RoleResponse(id=role_id, sample_count=0, **payload.model_dump())
