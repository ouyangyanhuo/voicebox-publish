"""IndexTTS2 backend using an isolated worker subprocess."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from .base import (
    combine_voice_prompts as _combine_voice_prompts,
    is_model_cached,
    model_load_progress,
)
from .. import config
from ..services.model_sources import download_model_snapshot
from ..utils.audio import load_audio

logger = logging.getLogger(__name__)

INDEXTTS2_HF_REPO = "IndexTeam/IndexTTS-2"
INDEXTTS2_MODEL_NAME = "indextts2"
INDEXTTS2_SAMPLE_RATE = 22050

_REQUIRED_FILES = ["config.yaml", "gpt.pth", "s2mel.pth", "wav2vec2bert_stats.pt", "feat1.pt", "feat2.pt"]


class IndexTTS2Backend:
    """IndexTTS2 zero-shot voice cloning backend."""

    def __init__(self) -> None:
        self.model_dir: str | None = None
        self._model_load_lock = asyncio.Lock()

    def is_loaded(self) -> bool:
        # The heavy model lives in the isolated worker process. The main backend
        # only tracks that a local snapshot has been resolved.
        return self.model_dir is not None

    def unload_model(self) -> None:
        self.model_dir = None

    def _get_model_path(self, model_size: str = "default") -> str:
        return INDEXTTS2_HF_REPO

    def _is_model_cached(self, model_size: str = "default") -> bool:
        return is_model_cached(
            INDEXTTS2_HF_REPO,
            weight_extensions=(".safetensors", ".bin", ".pt", ".pth", ".npz"),
            required_files=_REQUIRED_FILES,
        )

    async def load_model(self, model_size: str = "default") -> None:
        if self.model_dir and Path(self.model_dir).exists():
            return

        async with self._model_load_lock:
            if self.model_dir and Path(self.model_dir).exists():
                return
            await asyncio.to_thread(self._load_model_sync)

    def _load_model_sync(self) -> None:
        is_cached = self._is_model_cached()
        with model_load_progress(INDEXTTS2_MODEL_NAME, is_cached):
            model_dir = download_model_snapshot(INDEXTTS2_HF_REPO)
            cfg_path = Path(model_dir) / "config.yaml"
            if not cfg_path.exists():
                raise RuntimeError(f"IndexTTS2 snapshot is missing config.yaml: {model_dir}")
            self.model_dir = str(Path(model_dir).resolve())

    async def create_voice_prompt(
        self,
        audio_path: str,
        reference_text: str,
        use_cache: bool = True,
    ) -> Tuple[dict, bool]:
        return {"ref_audio": str(audio_path), "ref_text": reference_text}, False

    async def combine_voice_prompts(
        self,
        audio_paths: List[str],
        reference_texts: List[str],
    ) -> Tuple[np.ndarray, str]:
        return await _combine_voice_prompts(audio_paths, reference_texts)

    async def generate(
        self,
        text: str,
        voice_prompt: dict,
        language: str = "en",
        seed: Optional[int] = None,
        instruct: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        await self.load_model()
        assert self.model_dir is not None

        ref_audio = voice_prompt.get("ref_audio")
        if not ref_audio or not Path(ref_audio).exists():
            raise RuntimeError("IndexTTS2 requires a cloned voice profile with reference audio.")

        advanced = voice_prompt.get("indextts2") or {}
        output_dir = config.get_cache_root_dir() / "indextts2"
        output_dir.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        payload_path = output_dir / f"{job_id}.json"
        result_path = output_dir / f"{job_id}.result.json"
        output_path = output_dir / f"{job_id}.wav"

        payload = {
            "install_dir": str(config.get_install_dir()),
            "cache_dir": str(config.get_cache_root_dir()),
            "model_dir": self.model_dir,
            "cfg_path": str(Path(self.model_dir) / "config.yaml"),
            "spk_audio_prompt": ref_audio,
            "text": text,
            "output_path": str(output_path),
            "seed": seed,
            "emo_audio_prompt": advanced.get("emo_audio_prompt"),
            "emo_alpha": advanced.get("emo_alpha", 1.0),
            "emo_vector": advanced.get("emo_vector"),
            "use_emo_text": advanced.get("use_emo_text", False),
            "emo_text": advanced.get("emo_text"),
            "use_random": advanced.get("use_random", False),
            "interval_silence": advanced.get("interval_silence", 200),
            "max_text_tokens_per_segment": advanced.get("max_text_tokens_per_segment", 120),
            "use_fp16": advanced.get("use_fp16", False),
            "use_cuda_kernel": advanced.get("use_cuda_kernel", False),
            "use_accel": advanced.get("use_accel", False),
            "use_torch_compile": advanced.get("use_torch_compile", False),
            "generation_kwargs": {
                key: value
                for key, value in {
                    "do_sample": advanced.get("do_sample"),
                    "top_p": advanced.get("top_p"),
                    "top_k": advanced.get("top_k"),
                    "temperature": advanced.get("temperature"),
                    "length_penalty": advanced.get("length_penalty"),
                    "num_beams": advanced.get("num_beams"),
                    "repetition_penalty": advanced.get("repetition_penalty"),
                    "max_mel_tokens": advanced.get("max_mel_tokens"),
                }.items()
                if value is not None
            },
        }
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        await asyncio.to_thread(self._run_worker, payload_path, result_path)

        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "IndexTTS2 worker failed")

        audio, sample_rate = load_audio(str(output_path), sr=None)
        return np.asarray(audio, dtype=np.float32), int(sample_rate or INDEXTTS2_SAMPLE_RATE)

    def _run_worker(self, payload_path: Path, result_path: Path) -> None:
        python_exe = self._get_worker_python()
        cmd = [
            python_exe,
            "-m",
            "backend.indextts2_worker",
            "--payload",
            str(payload_path),
            "--result",
            str(result_path),
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(config.get_install_dir())
        proc = subprocess.run(
            cmd,
            cwd=str(config.get_install_dir()),
            env=env,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("INDEXTTS2_WORKER_TIMEOUT", "1800")),
        )
        if proc.returncode != 0:
            detail = ""
            if result_path.exists():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    detail = result.get("error") or result.get("traceback") or ""
                except Exception:
                    detail = ""
            if not detail:
                detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"IndexTTS2 worker failed: {detail}")

    def _get_worker_python(self) -> str:
        configured = os.getenv("INDEXTTS2_PYTHON")
        if configured:
            return configured

        worker_root = Path(__file__).resolve().parents[1] / "indextts2_worker"
        candidates = [
            worker_root / ".venv" / "Scripts" / "python.exe",
            worker_root / ".venv" / "bin" / "python",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return sys.executable
