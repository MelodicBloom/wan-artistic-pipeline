"""
Layer 7 — Pipeline Orchestrator
Wires all layers together: config -> analyze -> prompt -> queue -> generate -> watch.
"""

import logging
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os

from src.clip_analyzer import analyze
from src.prompt_engine import load_pack, generate_job_prompts
from src.gpu_manager import get_generation_params, clear_cache
from src.job_queue import JobQueue
from src.comfy_client import ComfyClient
from src.watcher import FolderWatcher
from src.batch_scheduler import build_batch_manifest, save_manifest

load_dotenv()
log = logging.getLogger(__name__)


def load_config(config_path: Path = Path("config/pipeline.yaml")) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


class Pipeline:
    def __init__(self, config_path: Path = Path("config/pipeline.yaml")):
        self.cfg = load_config(config_path)
        self.pipeline_cfg = self.cfg["pipeline"]
        self.gen_cfg = self.cfg["generation"]
        self.paths_cfg = self.cfg["paths"]

        self.prompt_pack_path = Path(self.paths_cfg["prompt_pack"])
        self.workflow_path = Path(self.paths_cfg["workflow"])
        self.input_dir = Path(self.paths_cfg["input_dir"])
        self.output_dir = Path(self.paths_cfg["output_dir"])
        self.default_image = Path(os.getenv("DEFAULT_IMAGE", "input/IMG_4738.jpg"))

        self.comfy = ComfyClient(
            host=os.getenv("COMFY_HOST", self.paths_cfg.get("comfy_host", "127.0.0.1")),
            port=int(os.getenv("COMFY_PORT", self.paths_cfg.get("comfy_port", 8188))),
        )
        self.queue = JobQueue(
            num_workers=self.pipeline_cfg["num_workers"],
            cooldown_seconds=self.pipeline_cfg["cooldown_seconds"],
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.control_payload = {}  # set by generate.py before run

    def run_on_image(self, image_path: Path):
        """Full pipeline run for a single input image."""
        log.info(f"Pipeline start -> {image_path.name}")
        clear_cache()

        tokens = analyze(image_path)
        log.info(f"Semantic tokens: {tokens}")

        pack = load_pack(self.prompt_pack_path)
        jobs = generate_job_prompts(
            pack,
            tokens,
            variations_per_hybrid=self.pipeline_cfg["variations_per_hybrid"],
            control_payload=getattr(self, "control_payload", {}),
            duration_seconds=self.gen_cfg.get("duration_seconds", 6),
            fps=self.gen_cfg.get("fps", 24),
        )
        log.info(f"Generated {len(jobs)} job prompts")

        # Build batch manifest with full traceability
        jobs = build_batch_manifest(
            jobs=jobs,
            control_payload=getattr(self, "control_payload", {}),
            gen_cfg=self.gen_cfg,
            ttm_path=getattr(self, "control_payload", {}).get("ttm_path"),
        )

        gen_params = get_generation_params(self.gen_cfg)

        def run_fn(job, img_path, wf_path, gp):
            return self.comfy.run_job(
                workflow_path=wf_path,
                positive=job["positive"],
                negative=job["negative"],
                image_name=img_path.name,
                seed=job["seed"],
                gen_params=gp,
                metadata=job.get("metadata"),
            )

        for batch_num in range(1, self.pipeline_cfg["num_batches"] + 1):
            log.info(f"--- Batch {batch_num}/{self.pipeline_cfg['num_batches']} ---")
            self.queue.run(jobs, run_fn, image_path, self.workflow_path, gen_params)

        if jobs:
            batch_id = jobs[0].get("batch_id", "batch_unknown")
            save_manifest(jobs, self.output_dir, batch_id)

        log.info(f"Pipeline complete for {image_path.name}")

    def run_once(self):
        """Single batch run on the default image."""
        if not self.comfy.health_check():
            log.error("ComfyUI not reachable at configured host:port. Is it running?")
            return
        self.run_on_image(self.default_image)

    def run_watch(self):
        """Start folder watcher — auto-trigger on new image drops."""
        if not self.comfy.health_check():
            log.warning("ComfyUI not reachable — watcher running in dry-run mode")

        watcher = FolderWatcher(
            watch_dir=self.input_dir,
            on_new_image=self.run_on_image,
        )
        watcher.start()
        log.info("Pipeline watching for new images. Ctrl+C to stop.")
        watcher.join()
