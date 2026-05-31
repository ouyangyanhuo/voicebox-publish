from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AudioScribe IndexTTS2 Worker")


class WorkerGenerateRequest(BaseModel):
    model_dir: str
    cfg_path: str
    speaker_audio: str
    text: str
    output_path: str
    emo_alpha: float = 1.0
    emo_vector: list[float] | None = None
    emo_text: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "engine": "indextts2", "state": "scaffold"}


@app.post("/generate")
def generate(_payload: WorkerGenerateRequest) -> dict[str, str]:
    return {
        "status": "not_implemented",
        "message": "IndexTTS2 inference is gated by dependency audit.",
    }
