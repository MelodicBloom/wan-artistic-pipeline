"""
Layer 5 — ComfyUI HTTP API Client
Queues prompts, polls for completion, retrieves output filenames.
"""

import json
import time
import uuid
import logging
import requests
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)


class ComfyClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.base_url = f"http://{host}:{port}"
        self.client_id = str(uuid.uuid4())

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def load_workflow(self, workflow_path: Path) -> Dict:
        with open(workflow_path) as f:
            return json.load(f)

    def inject_prompt(
        self,
        workflow: Dict,
        positive: str,
        negative: str,
        image_name: str,
        seed: int,
        gen_params: Dict,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Injects prompt, seed, image, and generation params into workflow nodes.
        Also stamps extra.wan_art_pipeline with the full metadata payload.

        Rationale for extra.wan_art_pipeline:
          ComfyUI's API format supports an 'extra' root key that persists
          through the queue and into history. This is the safest transport
          for structured metadata without touching node internals, which
          vary by custom node pack.
        """
        wf = json.loads(json.dumps(workflow))  # deep copy — never mutate source

        # Stamp metadata into extra block
        wf.setdefault("extra", {})
        wf["extra"]["wan_art_pipeline"] = metadata or {}
        wf["extra"]["wan_art_pipeline"]["seed"] = seed
        wf["extra"]["wan_art_pipeline"]["generation"] = gen_params

        pos_injected = False
        for node_id, node in wf.items():
            if not isinstance(node, dict):
                continue
            node_type = node.get("class_type", "")
            inputs = node.get("inputs", {})

            if node_type == "CLIPTextEncode" and "text" in inputs:
                if not pos_injected:
                    inputs["text"] = positive
                    pos_injected = True
                else:
                    inputs["text"] = negative

            if node_type == "LoadImage" and "image" in inputs:
                inputs["image"] = image_name

            if node_type in ("KSampler", "KSamplerAdvanced", "WanVideoI2VWrapper"):
                inputs["seed"] = seed
                if "steps" in inputs:
                    inputs["steps"] = gen_params.get("steps", 35)
                if "cfg" in inputs:
                    inputs["cfg"] = gen_params.get("cfg_scale", 7.0)

        return wf

    def queue_prompt(self, workflow: Dict) -> Optional[str]:
        """Sends workflow to ComfyUI queue. Returns prompt_id or None."""
        payload = {"prompt": workflow, "client_id": self.client_id}
        try:
            r = requests.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            prompt_id = r.json().get("prompt_id")
            log.info(f"Queued prompt_id={prompt_id}")
            return prompt_id
        except Exception as e:
            log.error(f"Failed to queue prompt: {e}")
            return None

    def poll_until_done(
        self,
        prompt_id: str,
        timeout: int = 600,
        interval: int = 5,
    ) -> Optional[Dict]:
        """Polls /history/{prompt_id} until done or timeout."""
        elapsed = 0
        while elapsed < timeout:
            try:
                r = requests.get(
                    f"{self.base_url}/history/{prompt_id}", timeout=10
                )
                if r.status_code == 200:
                    history = r.json()
                    if prompt_id in history:
                        log.info(f"Prompt {prompt_id} completed")
                        return history[prompt_id]
            except Exception as e:
                log.warning(f"Poll error: {e}")
            time.sleep(interval)
            elapsed += interval

        log.error(f"Timeout waiting for prompt {prompt_id}")
        return None

    def run_job(
        self,
        workflow_path: Path,
        positive: str,
        negative: str,
        image_name: str,
        seed: int,
        gen_params: Dict,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Full job: load -> inject -> queue -> poll. Returns success bool."""
        workflow = self.load_workflow(workflow_path)
        injected = self.inject_prompt(
            workflow, positive, negative, image_name, seed, gen_params, metadata
        )
        prompt_id = self.queue_prompt(injected)
        if not prompt_id:
            return False
        result = self.poll_until_done(prompt_id)
        return result is not None
