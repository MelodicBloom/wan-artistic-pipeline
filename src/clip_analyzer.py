"""
Layer 1 — CLIP Semantic Analyzer
Extracts visual tokens from an input image via CLIP.
Falls back to curated defaults if CLIP is unavailable.
"""

import logging
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)

CLIP_AVAILABLE = False
clip_model = None
clip_processor = None

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    CLIP_AVAILABLE = True
    log.info("CLIP loaded successfully")
except Exception as e:
    log.warning(f"CLIP unavailable ({e}) — using fallback semantics")


FALLBACK_TOKENS = [
    "ethereal dancer",
    "marbled liquid texture",
    "white flowers",
    "swirling dark background",
    "graceful pose",
    "iridescent abalone",
    "golden lighting",
    "flowing organic form",
]


def analyze(image_path: Path) -> List[str]:
    """Return a list of semantic tokens for the given image."""
    if not CLIP_AVAILABLE:
        log.info("CLIP fallback: returning default tokens")
        return FALLBACK_TOKENS

    try:
        from PIL import Image
        import torch

        image = Image.open(image_path).convert("RGB")
        candidates = [
            "ethereal dancer", "marbled texture", "iridescent surface",
            "blooming flowers", "swirling dark background", "golden glow",
            "liquid silk fabric", "surreal figure", "graceful pose",
            "cosmic void", "nacre shimmer", "flowing hair",
        ]
        inputs = clip_processor(
            text=candidates, images=image, return_tensors="pt", padding=True
        )
        with torch.no_grad():
            outputs = clip_model(**inputs)
            logits = outputs.logits_per_image[0]
            probs = logits.softmax(dim=0).tolist()

        scored = sorted(zip(candidates, probs), key=lambda x: x[1], reverse=True)
        top_tokens = [token for token, _ in scored[:6]]
        log.info(f"CLIP extracted tokens: {top_tokens}")
        return top_tokens

    except Exception as e:
        log.warning(f"CLIP analysis failed ({e}) — using fallback")
        return FALLBACK_TOKENS
