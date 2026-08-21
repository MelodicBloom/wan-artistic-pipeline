# wan-artistic-pipeline

Autonomous Wan 2.2 video generation pipeline — surreal ethereal dancer aesthetic, with a bounded generic motion-control adapter for topology-sensitive image-to-video calibration.

## Architecture

```
wan-artistic-pipeline/
├── .github/workflows/        # CI: lint, dry-run, focused control-surface validation
├── config/
│   └── pipeline.yaml         # Master config (VRAM tier, workers, paths)
├── prompt-packs/
│   ├── surreal-ethereal-dancer.json
│   └── motion-control-surface-calibration.json
├── ttm_paths/
│   ├── gentle_orbit.json
│   ├── cinematic_orbit_volumetric.json
│   └── locked_front_micro_dolly.json
├── workflows/
│   ├── i2v_base.json
│   ├── hybrid_sparsectrl_ttm.json
│   └── hybrid_cinematic_dancer.json
├── src/
│   ├── clip_analyzer.py      # CLIP semantic extraction
│   ├── prompt_engine.py      # Hybrid prompt assembly + multi-keyframe metadata
│   ├── motion_control_surface.py # Motion Program → Wan-facing hybrid/control adapter
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
git clone https://github.com/MelodicBloom/wan-artistic-pipeline
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
| 2.5 — Motion controls | `motion_control_surface.py` | Translate governed topology/material/choreography controls into the existing hybrid + sparse-keyframe metadata surface |
| 3 — GPU | `gpu_manager.py` | VRAM tier detection + OOM fallback ladder |
| 4 — Queue | `job_queue.py` | Multi-worker ThreadPoolExecutor job dispatch |
| 5 — ComfyUI | `comfy_client.py` | HTTP API → queue prompt → poll for completion |
| 6 — Watcher | `watcher.py` | Folder watch → auto-trigger on new image drop |
| 7 — CI | `.github/workflows/` | JSON/config validation, dry run, focused motion-control tests |

The generic motion-control adapter is intentionally separate from graph execution. It preserves semantic/numeric controls and emits compatible multi-keyframe metadata, but a calibration scene is not marked executable until an installed-node-aware Wan/Comfy graph maps those controls to real node inputs. See `docs/MOTION_CONTROL_SURFACE.md`.

## Colab

For Colab use, see [theelderemo/wan2.2-google-colab](https://github.com/theelderemo/wan2.2-google-colab). This repo handles the automation layer on top.

## License

Apache 2.0 — same as upstream Wan2.2.
