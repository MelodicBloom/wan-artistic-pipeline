"""
Layer 2 — Prompt Engine
Hybrid prompt assembly: base_style + hybrid + CLIP tokens + random extra modifier.
Produces coherent, varied prompts per generation while staying on-aesthetic.
Also generates structured multi-keyframe metadata per job.
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional

log = logging.getLogger(__name__)


DEFAULT_POSE_NOTES = [
    "arm raised high, head tilted — spatial tension at apex",
    "gentle torso undulation, petals beginning to release — motion entering",
    "peak extension, bloom fully present — emotional apex",
    "soft release, subtle smile, settling posture — resolution",
]


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


def build_multikeyframe_metadata(
    hybrid: Dict,
    control_payload: Dict,
    duration_seconds: float,
    fps: int,
) -> Dict:
    """
    Builds structured multi-keyframe metadata for one job.

    Kept separate from prompt assembly so the metadata is typed, inspectable,
    and passable to batch_scheduler.py without needing to re-parse prose.

    Strength curve design: high at anchors (0.9), low in middle (0.65).
    Rationale: start/end poses are the viewer's read points. Middle frames
    should remain elastic so texture flow and motion inference can breathe.
    A flat curve over-stabilizes and reads as mechanical.
    """
    count = int(control_payload.get("multi_keyframe_count", 4))
    strengths = control_payload.get("sparse_strengths", {"start": 0.9, "middle": 0.65, "end": 0.9})
    ttm_path = control_payload.get("ttm_path", "ttm_paths/gentle_orbit.json")
    motion = hybrid.get("motion", {})
    timing = hybrid.get("timing", {})
    camera = hybrid.get("camera", {})

    times = [round(duration_seconds * i / max(count - 1, 1), 2) for i in range(count)]
    keyframe_labels = ["start"] + [f"mid{i}" for i in range(1, count - 1)] + ["end"]

    keyframes = []
    for i, label in enumerate(keyframe_labels):
        is_anchor = (i == 0 or i == count - 1)
        strength = float(strengths["start"] if i == 0 else strengths["end"] if i == count - 1 else strengths["middle"])
        keyframes.append({
            "id": label,
            "t": times[i],
            "strength": strength,
            "pose": DEFAULT_POSE_NOTES[i] if i < len(DEFAULT_POSE_NOTES) else "interpolated",
            "behavior": motion.get("body", {}).get("type", "smooth interpolation"),
            "easing": motion.get("body", {}).get("easing", "cubic ease-in-out"),
            "cue": timing.get("motion_start", "start of clip") if is_anchor else "interpolated",
            "is_anchor": is_anchor,
        })

    return {
        "schema": "wan_art_pipeline.multikeyframe.v1",
        "hybrid_id": hybrid.get("id"),
        "hybrid_name": hybrid.get("name"),
        "duration_seconds": duration_seconds,
        "fps": fps,
        "ttm_path": ttm_path,
        "sparsectrl": {
            "strengths": strengths,
            "anchor_count": count,
            "interpolation": "latent blending + temporal attention",
            "noise_injection": "small stochastic jitter on intermediate frames only",
        },
        "keyframes": keyframes,
        "camera": camera,
        "motion": motion,
        "semantics": hybrid.get("semantics", {}),
        "meaning": hybrid.get("meaning", ""),
        "intent": hybrid.get("intent", ""),
        "inspiration": hybrid.get("inspiration", ""),
        "takeaways": hybrid.get("takeaways", []),
    }


def generate_job_prompts(
    pack: Dict,
    semantic_tokens: List[str],
    variations_per_hybrid: int = 2,
    control_payload: Optional[Dict] = None,
    duration_seconds: float = 6.0,
    fps: int = 24,
) -> List[Dict]:
    """
    Returns a flat list of job dicts, one per hybrid x variation.
    Each dict has: name, positive, negative, seed, metadata, _hybrid.
    _hybrid is kept for batch_scheduler.py access; stripped before queue dispatch.
    """
    jobs = []
    base = pack["base_style"]
    negative = pack.get("negative", "")
    extras = pack.get("extra_modifiers", ["cinematic"])
    cp = control_payload or {}

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
                "_hybrid": hybrid,
                "metadata": build_multikeyframe_metadata(
                    hybrid=hybrid,
                    control_payload=cp,
                    duration_seconds=duration_seconds,
                    fps=fps,
                ),
            })
            log.debug(f"Job prepared: {name}")

    return jobs
