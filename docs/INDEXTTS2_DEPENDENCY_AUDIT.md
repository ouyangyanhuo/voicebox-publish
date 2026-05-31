# IndexTTS2 Dependency Audit

Status: not started.

This audit is mandatory before real IndexTTS2 inference code is implemented.

## Source To Audit

- GitHub: https://github.com/index-tts/index-tts
- ModelScope model: https://modelscope.cn/models/IndexTeam/IndexTTS-2

## Checklist

- [ ] Clone the official repository into a temporary research directory.
- [ ] Inspect `pyproject.toml` / lock files.
- [ ] Inspect `indextts/infer_v2.py`.
- [ ] Confirm `IndexTTS2(cfg_path, model_dir, ...)` initialization.
- [ ] Confirm exact `infer(...)` parameters.
- [ ] Identify runtime data files that must be bundled.
- [ ] Identify hidden imports and metadata collection for packaging.
- [ ] Identify any automatic secondary downloads.
- [ ] Force every cache path into the install-local `cache/` or `model/` roots.
- [ ] Run a CPU smoke generation in a clean worker venv.
- [ ] Document CUDA / FP16 / CUDA kernel / DeepSpeed support and failure modes.
