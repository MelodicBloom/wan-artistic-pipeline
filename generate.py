#!/usr/bin/env python3
"""
Entry point for the Wan 2.2 Autonomous Artistic Pipeline.

Usage:
  python generate.py            # Single batch run on default image
  python generate.py --watch    # Watch input/ folder for new images
  python generate.py --dry-run  # Validate config/prompts without calling ComfyUI
  python generate.py --image path/to/image.jpg  # Run on specific image
"""

import argparse
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
    return parser.parse_args()


def main():
    args = parse_args()
    pipeline = Pipeline(config_path=args.config)

    if args.dry_run:
        from src.prompt_engine import load_pack, generate_job_prompts
        from src.clip_analyzer import analyze
        from src.gpu_manager import get_generation_params

        image = args.image or pipeline.default_image
        tokens = analyze(image)
        pack = load_pack(pipeline.prompt_pack_path)
        jobs = generate_job_prompts(
            pack, tokens,
            variations_per_hybrid=pipeline.pipeline_cfg["variations_per_hybrid"]
        )
        gen_params = get_generation_params(pipeline.gen_cfg)

        print(f"\n--- DRY RUN ---")
        print(f"VRAM params: {gen_params}")
        print(f"Total jobs: {len(jobs)}")
        for j in jobs:
            print(f"\n[{j['name']}]")
            print(f"  Prompt: {j['positive'][:120]}...")
            print(f"  Seed: {j['seed']}")
        return

    if args.watch:
        pipeline.run_watch()
    elif args.image:
        pipeline.run_on_image(args.image)
    else:
        pipeline.run_once()


if __name__ == "__main__":
    main()
