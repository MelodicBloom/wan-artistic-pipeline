# wan-artistic-pipeline

Autonomous Wan 2.2 video generation pipeline — surreal ethereal dancer aesthetic.

## Architecture

```
wan-artistic-pipeline/
├── .github/workflows/        # CI: lint, dry-run, output archival
├── config/
│   └── pipeline.yaml         # Master config (VRAM tier, workers, paths)
├── prompt-packs/
│   └── surreal-ethereal-dancer.json
├── workflows/
│   ├── i2v_base.json         # ComfyUI I2V workflow (GGUF + Wan 2.2)
│   └── hybrid_zoe_canny_sparsectrl.json
├── src/
│   ├── clip_analyzer.py      # CLIP semantic extraction
│   ├── prompt_engine.py      # Hybrid prompt assembly + variation
│   ├── comfy_client.py       # ComfyUI HTTP API client
│   ├── gpu_manager.py        # VRAM management + OOM fallback ladder
│   ├── job_queue.py          # Multi-worker ThreadPoolExecutor queue
│   ├── watcher.py            # Watchdog folder watcher → triggers queue
│   └── pipeline.py           # Main orchestrator — imports all modules
├── generate.py               # Entry point
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
git clone https://github.com/qt314wink/wan-artistic-pipeline
cd wan-artistic-pipeline
pip install -r requirements.txt

# Copy and fill in your config
cp .env.example .env

# Run full batch on default image
python generate.py

# Or drop images into input/ for auto-processing
python generate.py --watch
```

## Layers

| Layer | Module | Purpose |
|---|---|---|
| 1 — Analysis | `clip_analyzer.py` | CLIP semantic token extraction from input image |
| 2 — Prompt | `prompt_engine.py` | Hybrid assembly: base + hybrid + semantics + extras |
| 3 — GPU | `gpu_manager.py` | VRAM tier detection + OOM fallback ladder |
| 4 — Queue | `job_queue.py` | Multi-worker ThreadPoolExecutor job dispatch |
| 5 — ComfyUI | `comfy_client.py` | HTTP API → queue prompt → poll for completion |
| 6 — Watcher | `watcher.py` | Folder watch → auto-trigger on new image drop |
| 7 — CI | `.github/workflows/` | Lint, dry-run validation, output archival |

## Colab

For Colab use, see [theelderemo/wan2.2-google-colab](https://github.com/theelderemo/wan2.2-google-colab). This repo handles the automation layer on top.

## License

Apache 2.0 — same as upstream Wan2.2.
