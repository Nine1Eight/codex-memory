# Sigil Route Agent — Termux install + real ARC training

1. Download `sigil_route_agent_ACTUAL_ARC_GAMES.zip` into Android Downloads.
2. Download `termux_sigil_arc_train.sh` into Android Downloads or copy it to Termux.
3. In Termux:

```bash
termux-setup-storage
cp ~/storage/downloads/termux_sigil_arc_train.sh ~/
chmod +x ~/termux_sigil_arc_train.sh
export ARC_API_KEY="YOUR_NEW_ROTATED_KEY"
export SIGIL_ONLY_GAME=sb26
export SIGIL_MAX_STEPS_PER_GAME=40
export SIGIL_VLLM_ENABLED=0
~/termux_sigil_arc_train.sh
```

With local GGUF:

```bash
export SIGIL_VLLM_ENABLED=1
export SIGIL_GGUF_MODEL="$HOME/models/YOUR_MODEL.gguf"
export SIGIL_GGUF_CTX=8192
export SIGIL_GGUF_THREADS=4
export SIGIL_GGUF_MAX_TOKENS=384
export SIGIL_ONLY_GAME=sb26
export SIGIL_MAX_STEPS_PER_GAME=250
~/termux_sigil_arc_train.sh
```

All 25 games:

```bash
unset SIGIL_ONLY_GAME
export SIGIL_MAX_STEPS_PER_GAME=250
~/termux_sigil_arc_train.sh
```

Outputs are written under `~/sigil_route_agent_e2e/runs/...`.
