from __future__ import annotations

from fastapi import APIRouter, Request

from ..database import connect
from ..schemas import SettingsResponse, SettingsUpdate

router = APIRouter()


def _row_to_settings(row) -> SettingsResponse:
    return SettingsResponse(
        model_source="modelscope",
        github_mirror_enabled=bool(row["github_mirror_enabled"]),
        gpu_mode=row["gpu_mode"],
        use_fp16=bool(row["use_fp16"]),
        use_cuda_kernel=bool(row["use_cuda_kernel"]),
        use_deepspeed=bool(row["use_deepspeed"]),
    )


@router.get("", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    with connect(request.app.state.paths.database_path) as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
        return _row_to_settings(row)


@router.put("", response_model=SettingsResponse)
def update_settings(request: Request, patch: SettingsUpdate) -> SettingsResponse:
    fields = patch.model_dump(exclude_unset=True)
    if fields:
        values = {
            key: int(value) if isinstance(value, bool) else value
            for key, value in fields.items()
        }
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        with connect(request.app.state.paths.database_path) as conn:
            conn.execute(
                f"UPDATE settings SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                values,
            )
    return get_settings(request)
