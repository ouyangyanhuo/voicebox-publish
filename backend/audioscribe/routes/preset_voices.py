from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..schemas import PresetVoiceListResponse

router = APIRouter()


def _load_manifest(preset_dir):
    manifest_path = preset_dir / "manifest.json"
    if not manifest_path.exists():
        return {"version": 1, "items": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@router.get("", response_model=PresetVoiceListResponse)
def list_preset_voices(request: Request) -> PresetVoiceListResponse:
    return PresetVoiceListResponse(items=_load_manifest(request.app.state.paths.preset_voice_dir).get("items", []))


@router.get("/{voice_id}/audio")
def get_preset_voice_audio(request: Request, voice_id: str):
    preset_dir = request.app.state.paths.preset_voice_dir
    manifest = _load_manifest(preset_dir)
    item = next((row for row in manifest.get("items", []) if row.get("id") == voice_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Preset voice not found")
    audio_path = (preset_dir / item["file"]).resolve()
    if not str(audio_path).startswith(str(preset_dir.resolve())) or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Preset voice audio not found")
    return FileResponse(audio_path)
