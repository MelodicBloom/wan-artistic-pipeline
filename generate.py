#!/usr/bin/env python3
"""
Entry point for the Wan 2.2 Autonomous Artistic Pipeline.

Usage:
  python generate.py                          # Single batch run on default image
  python generate.py --watch                  # Watch input/ for new images
  python generate.py --dry-run                # Validate config/prompts without calling ComfyUI
  python generate.py --image path/to/img.jpg  # Run on specific image
  python generate.py --sparse-keyframes       # Enable sparse keyframe + TTM metadata
  python generate.py --sparse-keyframes --ttm-path ttm_paths/gentle_orbit.json
"""

import argparse
import json
import logging
from pathlib import Path

from src.pipeline import Pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Wan 2.2 Artistic Pipeline")
    parser.add_argument("--watch", action="store_true", help="Watch input/ for new images")
    parser.add_argument("--dry-run", action="store_true", help="Validate without generating")
    parser.add_argument("--image", type=Path, help="Run on specific image")
    parser.add_argument("--config", type=Path, default=Path("config/pipeline.yaml"))
    parser.add_argument("--sparse-keyframes", action="store_true",
                        help="Enable sparse keyframe guidance + TTM motion metadata")
    parser.add_argument("--ttm-path", type=Path, default=None,
                        help="Override default TTM motion path JSON (e.g. ttm_paths/gentle_orbit.json)")
    return parser.parse_args()


def build_control_payload(pipeline: Pipeline, args) -> dict:
    """
    Assembles the control payload from config + CLI flags.
    CLI flags always win over config defaults.
    Kept as a pure function so it is testable independently of pipeline state.
    """
    control = dict(pipeline.cfg.get("controlnet", {}))
    paths = dict(pipeline.cfg.get("paths", {}))
    pipeline_cfg = dict(pipeline.pipeline_cfg)

    sparse_enabled = bool(args.sparse_keyframes or pipeline_cfg.get("enable_sparse_keyframes", False))
    kf_count = int(pipeline_cfg.get("multi_keyframe_count", 4))
    kf_strengths = control.get("sparse_keyframe_strengths", {"start": 0.90, "middle": 0.65, "end": 0.90})

    default_ttm = Path(paths.get("ttm_path_folder", "ttm_paths/")) / paths.get("default_ttm_path", "gentle_orbit.json")
    resolved_ttm = str(args.ttm_path or default_ttm)

    return {
        "enable_sparse_keyframes": sparse_enabled,
        "multi_keyframe_count": kf_count,
        "sparse_strengths": {
            "start": float(kf_strengths.get("start", 0.90)),
            "middle": float(kf_strengths.get("middle", 0.65)),
            "end": float(kf_strengths.get("end", 0.90)),
        },
        "sparsectrl_strength": float(control.get("sparsectrl_strength", 0.75)),
        "zoe_strength": float(control.get("zoe_strength", 0.95)),
        "canny_strength": float(control.get("canny_strength", 0.45)),
        "animatediff_scale": float(control.get("animatediff_scale", 1.0)),
        "ttm_path": resolved_ttm,
    }


def main():
    args = parse_args()
    pipeline = Pipeline(config_path=args.config)
    control_payload = build_control_payload(pipeline, args)

    if args.dry_run:
        from src.prompt_engine import load_pack, generate_job_prompts
        from src.clip_analyzer import analyze
        from src.gpu_manager import get_generation_params

        image = args.image or pipeline.default_image
        tokens = analyze(image)
        pack = load_pack(pipeline.prompt_pack_path)
        jobs = generate_job_prompts(
            pack, tokens,
            variations_per_hybrid=pipeline.pipeline_cfg["variations_per_hybrid"],
            control_payload=control_payload,
            duration_seconds=pipeline.gen_cfg.get("duration_seconds", 6),
            fps=pipeline.gen_cfg.get("fps", 24),
        )
        gen_params = get_generation_params(pipeline.gen_cfg)

        print(f"\n--- DRY RUN ---")
        print(f"VRAM params: {gen_params}")
        print(f"Control payload:\n{json.dumps(control_payload, indent=2)}")
        print(f"Total jobs: {len(jobs)}")
        for j in jobs:
            print(f"\n[{j['name']}]")
            print(f"  Prompt: {j['positive'][:120]}...")
            print(f"  Seed: {j['seed']}")
            if "metadata" in j:
                print(f"  Keyframes: {len(j['metadata'].get('keyframes', []))}")
                print(f"  TTM path: {j['metadata'].get('ttm_path')}")
        return

    pipeline.control_payload = control_payload

    if args.watch:
        pipeline.run_watch()
    elif args.image:
        pipeline.run_on_image(args.image)
    else:
        pipeline.run_once()


if __name__ == "__main__":
    main()
