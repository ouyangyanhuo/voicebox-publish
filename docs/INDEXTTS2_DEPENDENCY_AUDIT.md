# IndexTTS2 Dependency Audit

Status: implementation-gated audit completed enough for v1 worker integration; CPU smoke generation is still blocked until the large model files and worker venv are installed locally.

## Sources Audited

- Official GitHub repository: https://github.com/index-tts/index-tts
- Official ModelScope model: https://modelscope.cn/models/IndexTeam/IndexTTS-2
- Local research checkout: `cache/research/index-tts`

The repository clone required `GIT_LFS_SKIP_SMUDGE=1` because the official repository currently reports an exceeded Git LFS budget while downloading example wav files. Source files were still checked out for audit.

## Dependency Findings

- Official package name: `indextts`, version `2.0.0`.
- Official installation path uses `uv`; README explicitly warns that plain pip/conda installs are not supported.
- Python requirement: `>=3.10`.
- Heavy pinned dependencies include `torch==2.8.*`, `torchaudio==2.8.*`, `transformers==4.52.1`, `modelscope==1.27.0`, `numba==0.58.1`, `numpy==1.26.2`, `librosa`, `safetensors`, `sentencepiece`, `descript-audiotools`, `wetext` on Windows/macOS, and `WeTextProcessing` on Linux.
- Optional `deepspeed==0.17.1` is documented as difficult on Windows and should remain opt-in.
- Official PyTorch index is CUDA 12.8 for Windows/Linux via `uv` source configuration.

## Runtime Download And Cache Risks

- `indextts/infer_v2.py` hard-codes `os.environ['HF_HUB_CACHE'] = './checkpoints/hf_cache'` before importing HuggingFace utilities.
- Initialization performs additional HuggingFace/Transformers downloads:
  - `facebook/w2v-bert-2.0` via `SeamlessM4TFeatureExtractor.from_pretrained`
  - `amphion/MaskGCT` via `hf_hub_download`
  - `funasr/campplus` via `hf_hub_download`
  - BigVGAN via `BigVGAN.from_pretrained`
- AudioScribe worker must force and re-patch HuggingFace cache paths to `<install>/cache/huggingface` immediately before and after importing `indextts.infer_v2`.
- The primary IndexTTS2 model must be downloaded from ModelScope to `<install>/model/modelscope/IndexTeam/IndexTTS-2`; no HuggingFace fallback is allowed.

## Confirmed IndexTTS2 Interface

Initialization:

```python
IndexTTS2(
    cfg_path="<snapshot>/config.yaml",
    model_dir="<snapshot>",
    use_fp16=False,
    use_cuda_kernel=False,
    use_deepspeed=False,
)
```

Generation:

```python
tts.infer(
    spk_audio_prompt=...,
    text=...,
    output_path=...,
    emo_audio_prompt=...,
    emo_alpha=...,
    emo_vector=...,
    use_emo_text=...,
    emo_text=...,
    use_random=...,
    interval_silence=...,
    max_text_tokens_per_segment=...,
)
```

Emotion vector order is `[happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]`.

## Packaging Notes

- Do not merge IndexTTS2 dependencies into the main FastAPI venv.
- Worker should run from `backend/indextts2_worker/.venv` or an explicitly configured `AUDIOSCRIBE_INDEXTTS2_PYTHON`.
- PyInstaller packaging for worker is not finalized; expect hidden imports and collect-all requirements for `indextts`, `wetext`/`WeTextProcessing`, `descript_audiotools`, `safetensors`, `sentencepiece`, and BigVGAN/native CUDA modules.
- CPU smoke generation remains required after local model download and worker venv setup.

## Implementation Decision

Proceed with an install-local worker subprocess integration that fails clearly when:

- worker venv is missing,
- ModelScope snapshot is missing,
- secondary HuggingFace-compatible dependencies cannot be cached under `<install>/cache`,
- CUDA/FP16/DeepSpeed options are unsupported.

No fake audio fallback is allowed.
