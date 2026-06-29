"""
Layer 3b — Batch Scheduler
Builds structured batch manifests for multi-keyframe TTM batch runs.
Each job is stamped with batch_id, variant_id, keyframe_set_id for
full traceability from manifest -> output filename -> quality review.

Design rationale:
  Batch identity is kept separate from prompt/motion identity.
  batch_id  -> identifies the full run (date + index)
  variant_id -> identifies hybrid + variation index
  keyframe_set_id -> identifies the sparse-motion anchor configuration
  This three-level key makes re-runs, partial failures, and A/B comparisons
  cheap and unambiguous without restructuring the job schema.
"""

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

log = logging.getLogger(__name__)


DEFAULT_KEYFRAME_POSES = [
    "arm raised high, head tilted — peak spatial tension",
    "gentle torso undulation, petals beginning to release — mid-motion",
    "peak extension, bloom fully present — emotional apex",
    "soft release, subtle smile, settling posture — resolution",
]


def build_keyframe_set(
    hybrid: Dict,
    control: Dict,
    duration_seconds: float,
    keyframe_set_index: int = 0,
) -> Dict:
    """
    Builds one keyframe set for a hybrid.
    strength curve: high at start/end anchors, lower in middle — allows
    texture flow and interpolation elasticity in the body of the clip
    without losing pose consistency at the critical read points.
    """
    count = int(control.get("multi_keyframe_count", 4))
    strengths = control.get("sparse_keyframe_strengths", {"start": 0.90, "middle": 0.65, "end": 0.90})
    motion = hybrid.get("motion", {})
    timing = hybrid.get("timing", {})

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
            "pose": DEFAULT_KEYFRAME_POSES[i] if i < len(DEFAULT_KEYFRAME_POSES) else "interpolated",
            "behavior": motion.get("body", {}).get("type", "smooth interpolation"),
            "easing": motion.get("body", {}).get("easing", "cubic ease-in-out"),
            "cue": timing.get("motion_start", "start of clip") if is_anchor else "interpolated",
            "is_anchor": is_anchor,
        })

    return {
        "keyframe_set_id": f"kfset_{keyframe_set_index:02d}",
        "anchor_count": count,
        "interpolation": "latent blending + temporal attention",
        "noise_injection": "small stochastic jitter on intermediate frames only",
        "keyframes": keyframes,
    }


def build_batch_manifest(
    jobs: List[Dict],
    control_payload: Dict,
    gen_cfg: Dict,
    ttm_path: Optional[str] = None,
    batch_index: Optional[int] = None,
) -> List[Dict]:
    """
    Stamps every job with batch_id, variant_id, keyframe_set_id, and
    the full multikeyframe metadata payload. Returns the enriched job list.

    Does not mutate jobs in-place — returns a new list.
    """
    date_str = datetime.now().strftime("%Y%m%d")
    idx = batch_index if batch_index is not None else random.randint(0, 99)
    batch_id = f"batch_{date_str}_{idx:02d}"
    duration = float(gen_cfg.get("duration_seconds", 6))
    fps = int(gen_cfg.get("fps", 24))
    resolved_ttm = ttm_path or control_payload.get("ttm_path", "ttm_paths/gentle_orbit.json")

    enriched = []
    for i, job in enumerate(jobs):
        hybrid = job.get("_hybrid", {})
        variant_id = f"{hybrid.get('id', 'h00')}_var{(i % 2) + 1:02d}"
        kfset = build_keyframe_set(hybrid, control_payload, duration, keyframe_set_index=i)

        stamped = dict(job)
        stamped.update({
            "batch_id": batch_id,
            "variant_id": variant_id,
            "keyframe_set_id": kfset["keyframe_set_id"],
            "output_stem": f"{batch_id}__{variant_id}__{kfset['keyframe_set_id']}__s{job['seed']}",
            "metadata": {
                "schema": "wan_art_pipeline.multikeyframe.v1",
                "batch_id": batch_id,
                "variant_id": variant_id,
                "hybrid_id": hybrid.get("id"),
                "hybrid_name": hybrid.get("name"),
                "duration_seconds": duration,
                "fps": fps,
                "ttm_path": resolved_ttm,
                "sparsectrl": {
                    "strengths": control_payload.get("sparse_strengths", {"start": 0.9, "middle": 0.65, "end": 0.9}),
                    "anchor_count": kfset["anchor_count"],
                    "interpolation": kfset["interpolation"],
                    "noise_injection": kfset["noise_injection"],
                },
                "keyframe_set": kfset,
                "camera": hybrid.get("camera", {}),
                "motion": hybrid.get("motion", {}),
                "semantics": hybrid.get("semantics", {}),
                "controlnet": {
                    "sparsectrl_strength": control_payload.get("sparsectrl_strength", 0.75),
                    "zoe_strength": control_payload.get("zoe_strength", 0.95),
                    "canny_strength": control_payload.get("canny_strength", 0.45),
                },
                "generation": gen_cfg,
                "meaning": hybrid.get("meaning", ""),
                "intent": hybrid.get("intent", ""),
                "inspiration": hybrid.get("inspiration", ""),
                "takeaways": hybrid.get("takeaways", []),
            },
        })
        enriched.append(stamped)
        log.debug(f"Stamped: {stamped['output_stem']}")

    log.info(f"Batch manifest built: {batch_id} — {len(enriched)} jobs")
    return enriched


def save_manifest(jobs: List[Dict], output_dir: Path, batch_id: str) -> Path:
    """Saves batch manifest as JSON alongside generated outputs."""
    path = output_dir / f"{batch_id}__manifest.json"
    with open(path, "w") as f:
        json.dump(jobs, f, indent=2, default=str)
    log.info(f"Manifest saved: {path}")
    return path
