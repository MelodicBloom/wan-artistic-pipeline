"""
Layer 4 — Job Queue
Multi-worker ThreadPoolExecutor that dispatches generation jobs.
Handles errors, cooldowns, and progress reporting.
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
                try:
                    success = future.result()
                    status = "✅" if success else "⚠️"
                    completed += 1
                    log.info(f"{status} [{completed}/{total}] {job['name']}")
                except Exception as e:
                    log.error(f"❌ Job {job['name']} raised: {e}")
                finally:
                    time.sleep(self.cooldown)

        log.info(f"Queue complete — {total} jobs processed")
