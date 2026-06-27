"""
Layer 2 — Prompt Engine
Hybrid prompt assembly: base_style + hybrid + CLIP tokens + random extra modifier.
Produces coherent, varied prompts per generation while staying on-aesthetic.
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict

log = logging.getLogger(__name__)


def load_pack(path: Path) -> Dict:
    with open(path) as f:
        return json.load(f)


def assemble(
    base_style: str,
    hybrid_positive: str,
    semantic_tokens: List[str],
    extra_modifiers: List[str],
    shuffle: bool = True,
) -> str:
    """
    Builds a full prompt by combining the four components.
    Shuffles non-base components for variation while keeping coherence.
    """
    extra = random.choice(extra_modifiers)
    token_str = ", ".join(semantic_tokens[:4])

    components = [hybrid_positive, token_str, extra]
    if shuffle:
        random.shuffle(components)

    full = f"{base_style}, {', '.join(components)}, masterful surreal coherence, artistic integrity"
    return full


def generate_job_prompts(
    pack: Dict,
    semantic_tokens: List[str],
    variations_per_hybrid: int = 2,
) -> List[Dict]:
    """
    Returns a flat list of job dicts, one per hybrid × variation.
    Each dict has: name, positive, negative, seed.
    """
    jobs = []
    base = pack["base_style"]
    negative = pack.get("negative", "")
    extras = pack.get("extra_modifiers", ["cinematic"])

    for hybrid in pack["hybrids"]:
        for var_idx in range(1, variations_per_hybrid + 1):
            prompt = assemble(base, hybrid["positive"], semantic_tokens, extras)
            seed = random.randint(0, 999_999_999)
            name = f"{hybrid['name'].replace(' ', '_').lower()}_v{var_idx}_s{seed}"
            jobs.append({
                "name": name,
                "positive": prompt,
                "negative": negative,
                "seed": seed,
            })
            log.debug(f"Job prepared: {name}")

    return jobs
