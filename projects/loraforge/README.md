# LORAForge Workspace

Created by `setup_loraforge.py` v2.2.

## Layout

```text
/data/data/com.termux/files/home/loraforge/
├── adapters/          # LoRA/adapter outputs
├── checkpoints/       # resumable training checkpoints
├── configs/           # JSON/YAML configs
├── data/              # raw/processed local data
├── datasets/          # dataset files
├── logs/              # installer and run logs
├── models/base/       # base model directories
├── models/gguf/       # GGUF exports or local GGUF models
├── outputs/           # final artifacts
└── scripts/           # verification and launch helpers
```

## Verify

```bash
python3 scripts/verify_env.py
```

## Install hints

### Termux

```bash
pkg update
pkg install python git clang make cmake pkg-config rust binutils libffi openssl
pkg install python-torch
python3 -m pip install -U -r requirements.txt
```

### Desktop Linux

Use a virtual environment, then install the Python dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -U pip setuptools wheel
python3 -m pip install -U -r requirements.txt
```

Install PyTorch using the official selector for your CPU/CUDA/ROCm target.

## Notes

- This setup does not store API keys.
- Torch is validated defensively because local files named `torch.py` or `torch/` can shadow the real package.
- The installer refuses to claim success for broken imports.
