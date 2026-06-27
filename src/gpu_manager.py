"""
Layer 3 — GPU Manager
Detects available VRAM, applies offload flags, implements OOM fallback ladder.
"""

import logging
from typing import Dict

log = logging.getLogger(__name__)


def get_vram_gb() -> float:
    """Returns available GPU VRAM in GB, or 0 if no CUDA device."""
    try:
        import torch
        if not torch.cuda.is_available():
            return 0.0
        props = torch.cuda.get_device_properties(0)
        return props.total_memory / (1024 ** 3)
    except Exception:
        return 0.0


def clear_cache():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def get_generation_params(cfg: Dict) -> Dict:
    """
    Returns generation params with OOM fallback ladder applied based on VRAM.
    Ladder:
      >= 80 GB  → full A100 settings, no offload needed
      >= 40 GB  → 720P, offload flags on
      >= 24 GB  → 720P with all offloads, or drop to 480P
      < 24 GB   → force 480P, TI2V-5B-class settings
    """
    vram = get_vram_gb()
    log.info(f"Detected VRAM: {vram:.1f} GB")

    params = {
        "resolution": cfg.get("resolution", "1280x720"),
        "fps": cfg.get("fps", 24),
        "duration": cfg.get("duration_seconds", 5),
        "steps": cfg.get("steps", 30),
        "cfg_scale": cfg.get("cfg_scale", 7.0),
        "offload_model": True,
        "convert_model_dtype": True,
        "t5_cpu": True,
    }

    if vram >= 80:
        params["offload_model"] = False
        params["convert_model_dtype"] = False
        params["t5_cpu"] = False
        log.info("A100 80GB detected — offloads disabled")
    elif vram >= 40:
        log.info(">=40GB GPU — partial offloads enabled")
    elif vram >= 24:
        log.info("24GB GPU — all offloads enabled, may need 480P fallback")
    else:
        params["resolution"] = "832x480"
        log.warning(f"Low VRAM ({vram:.1f}GB) — forced 480P fallback")

    return params
