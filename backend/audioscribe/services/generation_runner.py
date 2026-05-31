from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from ..config import RuntimePaths
from ..database import connect


class GenerationError(RuntimeError):
    pass


def _inside(base: Path, candidate: Path) -> bool:
    base = base.resolve()
    candidate = candidate.resolve()
    return candidate == base or base in candidate.parents


def _load_preset_audio(paths: RuntimePaths, preset_voice_id: str) -> Path:
    manifest_path = paths.preset_voice_dir / "manifest.json"
    if not manifest_path.exists():
        raise GenerationError("Preset voice manifest is empty. Add preset voices first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    item = next((row for row in manifest.get("items", []) if row.get("id") == preset_voice_id), None)
    if not item:
        raise GenerationError("Preset voice not found.")
    audio_path = (paths.preset_voice_dir / item["file"]).resolve()
    if not _inside(paths.preset_voice_dir, audio_path) or not audio_path.exists():
        raise GenerationError("Preset voice audio file is missing or outside the preset directory.")
    return audio_path


def _load_audio_library_item(paths: RuntimePaths, item_id: str) -> Path:
    with connect(paths.database_path) as conn:
        row = conn.execute("SELECT * FROM audio_library_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise GenerationError("Uploaded reference audio not found.")
    audio_path = Path(row["audio_path"]).resolve()
    if not _inside(paths.install_dir, audio_path) or not audio_path.exists():
        raise GenerationError("Uploaded reference audio is missing or outside the install directory.")
    return audio_path


def resolve_reference_audio(paths: RuntimePaths, payload: Any) -> Path:
    if payload.audio_source == "preset":
        if not payload.preset_voice_id:
            raise GenerationError("Select a preset voice before generating.")
        return _load_preset_audio(paths, payload.preset_voice_id)

    if payload.audio_source == "upload":
        if not payload.uploaded_audio_id:
            raise GenerationError("Upload a reference audio file before generating.")
        return _load_audio_library_item(paths, payload.uploaded_audio_id)

    if payload.audio_source == "record":
        if not payload.recorded_audio_id:
            raise GenerationError("Record a reference audio file before generating.")
        return _load_audio_library_item(paths, payload.recorded_audio_id)

    if payload.audio_source == "role":
        if not payload.role_id:
            raise GenerationError("Select a role before generating.")
        with connect(paths.database_path) as conn:
            row = conn.execute(
                "SELECT audio_path FROM role_samples WHERE role_id = ? ORDER BY created_at DESC LIMIT 1",
                (payload.role_id,),
            ).fetchone()
        if not row:
            raise GenerationError("Selected role has no reference audio sample.")
        audio_path = Path(row["audio_path"]).resolve()
        if not _inside(paths.install_dir, audio_path) or not audio_path.exists():
            raise GenerationError("Role reference audio is missing or outside the install directory.")
        return audio_path

    raise GenerationError("Unsupported audio source.")


def _model_snapshot_dir(paths: RuntimePaths) -> Path:
    return paths.model_dir / "IndexTeam" / "IndexTTS-2"


def _worker_python(paths: RuntimePaths) -> Path:
    explicit = os.environ.get("AUDIOSCRIBE_INDEXTTS2_PYTHON")
    if explicit:
        return Path(explicit)

    worker_venv = paths.install_dir / "backend" / "indextts2_worker" / ".venv"
    if os.name == "nt":
        return worker_venv / "Scripts" / "python.exe"
    return worker_venv / "bin" / "python"


def _job_env(paths: RuntimePaths) -> dict[str, str]:
    env = os.environ.copy()
    env["AUDIOSCRIBE_INSTALL_DIR"] = str(paths.install_dir)
    env["AUDIOSCRIBE_WORKER_CACHE"] = str(paths.worker_cache_dir)
    env["MODELSCOPE_CACHE"] = str(paths.modelscope_model_dir)
    env["HF_HOME"] = str(paths.huggingface_cache_dir)
    env["HF_HUB_CACHE"] = str(paths.huggingface_cache_dir / "hub")
    env["TRANSFORMERS_CACHE"] = str(paths.cache_dir / "transformers")
    env["TORCH_HOME"] = str(paths.cache_dir / "torch")
    env["TEMP"] = str(paths.cache_dir / "tmp")
    env["TMP"] = str(paths.cache_dir / "tmp")
    return env


def run_generation_task(paths: RuntimePaths, generation_id: str) -> None:
    with connect(paths.database_path) as conn:
        row = conn.execute("SELECT * FROM generations WHERE id = ?", (generation_id,)).fetchone()
    if not row:
        return

    output_path = paths.generated_audio_dir / f"{generation_id}.wav"
    snapshot_dir = _model_snapshot_dir(paths)
    cfg_path = snapshot_dir / "config.yaml"
    worker_python = _worker_python(paths)
    worker_script = paths.install_dir / "backend" / "indextts2_worker" / "worker.py"

    try:
        if not worker_python.exists():
            raise GenerationError(
                f"IndexTTS2 worker runtime is not installed: {worker_python}. "
                "Create backend/indextts2_worker/.venv with uv sync before generating."
            )
        if not worker_script.exists():
            raise GenerationError(f"IndexTTS2 worker script is missing: {worker_script}")
        if not cfg_path.exists():
            raise GenerationError(
                f"IndexTTS2 ModelScope model is missing: {snapshot_dir}. Download IndexTeam/IndexTTS-2 first."
            )

        params = json.loads(row["parameters_snapshot"] or "{}")
        speaker_audio = Path(params["speaker_audio"]).resolve()
        if not _inside(paths.install_dir, speaker_audio) or not speaker_audio.exists():
            raise GenerationError("Reference audio is missing or outside the install directory.")

        with connect(paths.database_path) as conn:
            conn.execute(
                "UPDATE generations SET status = 'running', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (generation_id,),
            )

        paths.worker_cache_dir.mkdir(parents=True, exist_ok=True)
        paths.generated_audio_dir.mkdir(parents=True, exist_ok=True)
        (paths.cache_dir / "tmp").mkdir(parents=True, exist_ok=True)
        job_path = paths.worker_cache_dir / f"{generation_id}.json"
        job_payload = {
            "install_dir": str(paths.install_dir),
            "cache_dir": str(paths.cache_dir),
            "model_dir": str(snapshot_dir),
            "cfg_path": str(cfg_path),
            "speaker_audio": str(speaker_audio),
            "text": row["text"],
            "output_path": str(output_path),
            "emo_audio_prompt": params.get("emo_audio_prompt"),
            "emo_alpha": params.get("emo_alpha", 1.0),
            "emo_vector": params.get("emo_vector"),
            "use_emo_text": params.get("use_emo_text", False),
            "emo_text": params.get("emo_text"),
            "use_random": params.get("use_random", False),
            "interval_silence": params.get("interval_silence", 200),
            "max_text_tokens_per_segment": params.get("max_text_tokens_per_segment", 120),
            "settings": params.get("settings", {}),
        }
        job_path.write_text(json.dumps(job_payload, ensure_ascii=False), encoding="utf-8")

        completed = subprocess.run(
            [str(worker_python), str(worker_script), "--generate", str(job_path)],
            cwd=str(paths.install_dir),
            env=_job_env(paths),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60 * 60,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "IndexTTS2 worker failed."
            raise GenerationError(message[-4000:])
        if not output_path.exists():
            raise GenerationError("IndexTTS2 worker completed without creating an audio file.")

        version_id = str(uuid.uuid4())
        with connect(paths.database_path) as conn:
            conn.execute(
                """
                UPDATE generations
                SET status = 'completed', audio_path = ?, error = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (str(output_path), generation_id),
            )
            conn.execute(
                """
                INSERT INTO generation_versions (id, generation_id, audio_path, label, is_active)
                VALUES (?, ?, ?, 'Initial', 1)
                """,
                (version_id, generation_id, str(output_path)),
            )
    except Exception as exc:
        with connect(paths.database_path) as conn:
            conn.execute(
                """
                UPDATE generations
                SET status = 'failed', error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (str(exc), generation_id),
            )
