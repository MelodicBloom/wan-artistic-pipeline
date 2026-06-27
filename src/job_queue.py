"""
Layer 4 — Job Queue
Multi-worker ThreadPoolExecutor that dispatches generation jobs.
Handles errors, cooldowns, and progress reporting.

Batch scaling note:
  For single-GPU setups, num_workers=1 is strongly recommended for video generation.
  Increasing workers on one GPU causes VRAM contention and degrades total throughput.
  Use num_workers > 1 only when jobs are routed to separate physical GPUs.
  The queue is intentionally sequential-first: it keeps the model hot across
  many jobs, which is more efficient than parallelism on shared VRAM.
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Callable

log = logging.getLogger(__name__)


class JobQueue:
    def __init__(self, num_workers: int = 2, cooldown_seconds: int = 1):
        self.num_workers = num_workers
        self.cooldown = cooldown_seconds

    def run(
        self,
        jobs: List[Dict],
        run_fn: Callable,
        image_path: Path,
        workflow_path: Path,
        gen_params: Dict,
    ):
        """
        Dispatches all jobs using the provided run_fn.
        run_fn signature: (job, image_path, workflow_path, gen_params) -> bool

        Job names include batch_id/variant_id/keyframe_set_id if batch manifest
        was built upstream by batch_scheduler.py.
        """
        total = len(jobs)
        log.info(f"Dispatching {total} jobs across {self.num_workers} workers")

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {
                executor.submit(
                    run_fn, job, image_path, workflow_path, gen_params
                ): job
                for job in jobs
            }

            completed = 0
            for future in as_completed(futures):
                job = futures[future]
                label = job.get("output_stem", job["name"])
                try:
                    success = future.result()
                    status = "OK" if success else "WARN"
                    completed += 1
                    log.info(f"[{status}] [{completed}/{total}] {label}")
                except Exception as e:
                    log.error(f"[FAIL] {label} raised: {e}")
                finally:
                    time.sleep(self.cooldown)

        log.info(f"Queue complete — {total} jobs processed")
