from __future__ import annotations

from fastapi import APIRouter, Request

from ..schemas import ModelStatusResponse

router = APIRouter()


@router.get("/status", response_model=ModelStatusResponse)
def model_status(request: Request) -> ModelStatusResponse:
    paths = request.app.state.paths
    snapshot_dir = paths.modelscope_model_dir / "IndexTeam" / "IndexTTS-2"
    return ModelStatusResponse(downloaded=snapshot_dir.exists())


@router.post("/download")
def download_model() -> dict[str, str]:
    return {
        "status": "not_implemented",
        "message": "ModelScope IndexTTS2 download will be implemented after dependency audit.",
    }
