# IndexTTS2 Dependency Audit

Source audited: `https://github.com/index-tts/index-tts`, cloned on 2026-05-30.
The checkout hit upstream Git LFS budget limits on example WAV files, but source,
configuration, and dependency metadata were available for inspection.

## Findings

- IndexTTS2 pins a conflicting ML stack: `torch==2.8.*`, `torchaudio==2.8.*`,
  `transformers==4.52.1`, `numba==0.58.1`, `numpy==1.26.2`, and
  `modelscope==1.27.0`. These are isolated in `backend/indextts2_worker`.
- `indextts/infer_v2.py` sets `HF_HUB_CACHE = './checkpoints/hf_cache'` at import
  time. The worker runs from `<install>/cache/indextts2` and also sets
  `HF_HOME`, `HF_HUB_CACHE`, `MODELSCOPE_CACHE`, `TORCH_HOME`, `NUMBA_CACHE_DIR`,
  and `MPLCONFIGDIR` before importing IndexTTS2.
- Runtime downloads still occur for auxiliary models:
  `facebook/w2v-bert-2.0`, `amphion/MaskGCT`,
  `funasr/campplus`, and `nvidia/bigvgan_v2_22khz_80band_256x`.
- `infer_v2.py` writes output via `torchaudio.save()` at 22050 Hz.
- PyInstaller-hostile patterns exist in the upstream tree:
  `@torch.jit.script`, `importlib.metadata.version()`, runtime `hf_hub_download`,
  and package-relative CUDA/source loading. The main Voicebox binary therefore
  does not bundle IndexTTS2 directly.
- Required local model snapshot files include `config.yaml`, `gpt.pth`,
  `s2mel.pth`, `wav2vec2bert_stats.pt`, `feat1.pt`, and `feat2.pt`.

## Integration Decision

IndexTTS2 runs in an isolated subprocess selected by `INDEXTTS2_PYTHON` or by
`backend/indextts2_worker/.venv`. The main backend only downloads/resolves the
snapshot path and exchanges JSON payloads plus WAV files with the worker.
