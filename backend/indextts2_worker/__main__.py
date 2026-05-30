"""Subprocess entry point for IndexTTS2 inference.

The main backend talks to this process with JSON files so IndexTTS2's pinned
torch/transformers/numba stack stays outside the main Voicebox environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


def _set_env_path(name: str, path: Path) -> None:
    os.environ[name] = str(path)


def configure_worker_environment(install_dir: Path, model_root: Path, cache_root: Path) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    model_root.mkdir(parents=True, exist_ok=True)

    _set_env_path("VOICEBOX_INSTALL_DIR", install_dir)
    _set_env_path("VOICEBOX_CACHE_DIR", cache_root)
    _set_env_path("VOICEBOX_MODELS_DIR", install_dir / "model")
    _set_env_path("XDG_CACHE_HOME", cache_root)
    _set_env_path("TORCH_HOME", cache_root / "torch")
    _set_env_path("NUMBA_CACHE_DIR", cache_root / "numba")
    _set_env_path("MPLCONFIGDIR", cache_root / "matplotlib")
    _set_env_path("HF_HOME", cache_root / "huggingface")
    _set_env_path("HF_HUB_CACHE", model_root / "huggingface")
    _set_env_path("HF_DATASETS_CACHE", cache_root / "huggingface" / "datasets")
    _set_env_path("MODELSCOPE_CACHE", model_root / "modelscope")
    _set_env_path("MODELSCOPE_MODULES_CACHE", cache_root / "modelscope" / "modules")
    os.environ.pop("TRANSFORMERS_CACHE", None)


def _json_error(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    return 1


def _run(payload: dict) -> dict:
    install_dir = Path(payload["install_dir"]).resolve()
    model_dir = Path(payload["model_dir"]).resolve()
    cache_root = Path(payload["cache_dir"]).resolve()
    output_path = Path(payload["output_path"]).resolve()
    configure_worker_environment(install_dir, install_dir / "model", cache_root)

    # Upstream infer_v2 sets HF_HUB_CACHE at import time to a relative
    # './checkpoints/hf_cache'. Running with cwd=<install>/cache/indextts2 keeps
    # that fallback inside the install-local cache if upstream ignores env vars.
    worker_cwd = cache_root / "indextts2"
    worker_cwd.mkdir(parents=True, exist_ok=True)
    os.chdir(worker_cwd)

    try:
        from indextts.infer_v2 import IndexTTS2
    except Exception as exc:
        raise RuntimeError(
            "IndexTTS2 worker dependencies are not installed. Create an isolated "
            "worker venv and set INDEXTTS2_PYTHON to its python.exe."
        ) from exc

    cfg_path = Path(payload.get("cfg_path") or model_dir / "config.yaml").resolve()
    if not cfg_path.exists():
        raise RuntimeError(f"IndexTTS2 config.yaml not found in model snapshot: {cfg_path}")

    tts = IndexTTS2(
        cfg_path=str(cfg_path),
        model_dir=str(model_dir),
        use_fp16=bool(payload.get("use_fp16", False)),
        device=payload.get("device"),
        use_cuda_kernel=bool(payload.get("use_cuda_kernel", False)),
        use_deepspeed=False,
        use_accel=bool(payload.get("use_accel", False)),
        use_torch_compile=bool(payload.get("use_torch_compile", False)),
    )

    kwargs = {
        "spk_audio_prompt": payload["spk_audio_prompt"],
        "text": payload["text"],
        "output_path": str(output_path),
        "emo_audio_prompt": payload.get("emo_audio_prompt"),
        "emo_alpha": float(payload.get("emo_alpha", 1.0)),
        "emo_vector": payload.get("emo_vector"),
        "use_emo_text": bool(payload.get("use_emo_text", False)),
        "emo_text": payload.get("emo_text"),
        "use_random": bool(payload.get("use_random", False)),
        "interval_silence": int(payload.get("interval_silence", 200)),
        "verbose": bool(payload.get("verbose", False)),
        "max_text_tokens_per_segment": int(payload.get("max_text_tokens_per_segment", 120)),
    }

    generation_kwargs = payload.get("generation_kwargs") or {}
    if isinstance(generation_kwargs, dict):
        kwargs.update(generation_kwargs)

    if payload.get("seed") is not None:
        import random
        import numpy as np
        import torch

        seed = int(payload["seed"])
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    tts.infer(**kwargs)

    if not output_path.exists():
        raise RuntimeError("IndexTTS2 worker finished without producing output audio.")

    return {"ok": True, "output_path": str(output_path), "sample_rate": 22050}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one IndexTTS2 generation job")
    parser.add_argument("--payload", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    result_path = Path(args.result).resolve()
    try:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        result = _run(payload)
    except Exception as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
