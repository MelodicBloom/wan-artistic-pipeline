"""Wan-facing adapter for provider-neutral Motion Program control surfaces.

This module does not redefine Motion Oracle semantics and does not pretend to
bind arbitrary Motion Program primitives directly to ComfyUI nodes. It converts
an approved/calibration control surface into the hybrid metadata shape already
consumed by ``prompt_engine.build_multikeyframe_metadata`` and retains numeric
controls in a separate payload for workflow binding and run receipts.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .prompt_engine import build_multikeyframe_metadata


PROMPT_SECTION_ORDER = (
    "subject",
    "structure",
    "preservation",
    "motion",
    "materials",
    "lighting",
    "camera",
    "timing",
)

REQUIRED_TOP_LEVEL = {
    "schema",
    "id",
    "semantic_authority",
    "contract_reference",
    "subject",
    "structure",
    "preservation",
    "materials",
    "scenes",
    "lighting",
    "camera",
    "generation",
    "negative",
}


def load_surface(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _duplicates(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return sorted(dupes)


def validate_surface(surface: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(surface))
    if missing:
        return ["missing required top-level fields: " + ", ".join(missing)]

    if surface["schema"] != "wan.motion_control_surface.v0.1":
        errors.append("schema must be wan.motion_control_surface.v0.1")

    authority = surface["semantic_authority"]
    for field in ("system", "repository", "path", "version", "status", "commit"):
        if not authority.get(field):
            errors.append(f"semantic_authority.{field} is required")

    if authority.get("system") != "Motion Oracle":
        errors.append("semantic_authority.system must remain Motion Oracle")

    contract = surface["contract_reference"]
    for field in ("system", "repository", "path", "status", "commit"):
        if not contract.get(field):
            errors.append(f"contract_reference.{field} is required")

    regions = surface["structure"].get("regions", [])
    region_ids = [region.get("id") for region in regions]
    if not regions or any(not region_id for region_id in region_ids):
        errors.append("structure.regions must declare non-empty ids")
    for duplicate in _duplicates(region_ids):
        errors.append(f"duplicate structure region id: {duplicate}")
    region_map = {region["id"]: region for region in regions if region.get("id")}

    scenes = surface["scenes"]
    scene_ids = [scene.get("id") for scene in scenes]
    if not scenes or any(not scene_id for scene_id in scene_ids):
        errors.append("scenes must declare non-empty ids")
    for duplicate in _duplicates(scene_ids):
        errors.append(f"duplicate scene id: {duplicate}")

    materials = set(surface["materials"])
    generic_targets = {"all_movable_regions", "paper_microtexture", "micro_patterns"}
    known_targets = set(region_map) | materials | generic_targets
    non_geometric_prefixes = ("reveal.", "light.", "material.", "effect.", "shade.", "texture.")

    for scene in scenes:
        if float(scene.get("duration_seconds", 0)) <= 0:
            errors.append(f"{scene.get('id')}: duration_seconds must be > 0")
        channels = scene.get("channels", [])
        if not channels:
            errors.append(f"{scene.get('id')}: at least one motion channel is required")
        for channel in channels:
            target = channel.get("target")
            primitive = channel.get("primitive", "")
            if target not in known_targets:
                errors.append(f"{scene.get('id')}: unknown channel target {target!r}")
            if target in region_map and not region_map[target].get("movable", False):
                if not primitive.startswith(non_geometric_prefixes):
                    errors.append(
                        f"{scene.get('id')}: {primitive} is not permitted on stationary region {target!r}"
                    )

    prohibited = set(surface["preservation"].get("prohibited", []))
    if "whole_object_spin" not in prohibited:
        errors.append("preservation.prohibited must include whole_object_spin")
    if "transparent_duplicate" not in prohibited:
        errors.append("preservation.prohibited must include transparent_duplicate")

    generation = surface["generation"]
    required_generation_fields = (
        "fps",
        "multi_keyframe_count",
        "sparse_strengths",
        "sparsectrl_strength",
        "zoe_strength",
        "canny_strength",
        "animatediff_scale",
        "ttm_path",
    )
    for field in required_generation_fields:
        if field not in generation:
            errors.append(f"generation.{field} is required")
    fps = int(generation.get("fps", 0))
    if fps <= 0:
        errors.append("generation.fps must be > 0")
    if int(generation.get("multi_keyframe_count", 0)) < 2:
        errors.append("generation.multi_keyframe_count must be >= 2")

    experiment_ids = [item.get("id") for item in surface.get("experiments", [])]
    for duplicate in _duplicates(experiment_ids):
        errors.append(f"duplicate experiment id: {duplicate}")

    return errors


def _format_structure(surface: Dict[str, Any]) -> str:
    parts = []
    for region in surface["structure"]["regions"]:
        state = "movable" if region.get("movable") else "stationary"
        parts.append(f"{region['id']} ({state}): {region.get('description', region['id'])}")
    symmetry = surface["structure"].get("symmetry_order")
    prefix = f"{symmetry}-fold structure; " if symmetry else ""
    return prefix + "; ".join(parts)


def _format_channel(channel: Dict[str, Any]) -> str:
    ordered = [channel["primitive"], f"target={channel['target']}"]
    for key in (
        "amplitude",
        "unit",
        "strength",
        "start",
        "end",
        "phase_offset_seconds",
        "speed",
        "frequency",
        "octaves",
    ):
        if key in channel:
            ordered.append(f"{key}={channel[key]}")
    if channel.get("easing"):
        ordered.append(f"easing={channel['easing']}")
    return " ".join(str(value) for value in ordered)


def _format_materials(surface: Dict[str, Any]) -> str:
    entries = []
    for name, spec in surface["materials"].items():
        entries.append(
            f"{name}: {spec['description']}; response={spec['response']}; "
            f"lighting={spec.get('lighting_response', 'material-local')}"
        )
    return "; ".join(entries)


def _negative_terms(surface: Dict[str, Any]) -> List[str]:
    values = list(surface["preservation"].get("prohibited", []))
    values.extend(surface.get("negative", []))
    for group in surface.get("failure_classes", {}).values():
        values.extend(group)
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _scene(surface: Dict[str, Any], scene_id: str) -> Dict[str, Any]:
    match = next((scene for scene in surface["scenes"] if scene["id"] == scene_id), None)
    if match is None:
        raise ValueError(f"unknown scene_id {scene_id!r}")
    return match


def compile_scene(surface: Dict[str, Any], scene_id: str) -> Dict[str, Any]:
    errors = validate_surface(surface)
    if errors:
        raise ValueError("; ".join(errors))

    scene = _scene(surface, scene_id)
    duration = float(scene["duration_seconds"])
    fps = int(surface["generation"]["fps"])
    frame_count = max(1, round(duration * fps))
    channels = scene["channels"]

    sections = {
        "subject": surface["subject"],
        "structure": _format_structure(surface),
        "preservation": "Preserve " + ", ".join(surface["preservation"]["locks"]),
        "motion": (
            f"grammar={scene['grammar']}; "
            + "; ".join(_format_channel(channel) for channel in channels)
        ),
        "materials": _format_materials(surface),
        "lighting": canonical_json(surface["lighting"]),
        "camera": canonical_json(surface["camera"]),
        "timing": f"duration={duration}s; fps={fps}; frame_count={frame_count}; loop={scene.get('loop', False)}",
    }
    positive = ". ".join(sections[name] for name in PROMPT_SECTION_ORDER)
    negative = ", ".join(_negative_terms(surface))

    easing = scene.get("primary_easing") or channels[0].get("easing", "cubic ease-in-out")
    keyframe_notes = scene.get("keyframe_notes") or [
        "exact source pose and topology; establish all preservation locks",
        "local motion channels enter while stationary anchors remain fixed",
        "peak designed choreography; strongest material-local reveal",
        "return to approved end state without topology drift or ghosting",
    ]

    hybrid = {
        "id": f"{surface['id']}:{scene_id}",
        "name": scene.get("name", scene_id),
        "positive": positive,
        "semantics": {
            "subject": surface["subject"],
            "topology": surface["structure"].get("topology"),
            "grammar": scene["grammar"],
            "semantic_authority": surface["semantic_authority"],
            "contract_reference": surface["contract_reference"],
        },
        "motion": {
            "body": {
                "type": scene["grammar"],
                "easing": easing,
            },
            "channels": channels,
        },
        "camera": surface["camera"],
        "timing": {
            "duration_seconds": duration,
            "fps": fps,
            "total_frames": frame_count,
            "motion_start": scene.get("motion_start", "start of clip"),
        },
        "keyframe_notes": keyframe_notes,
        "meaning": scene.get("meaning", ""),
        "intent": scene.get("intent", surface.get("intent", "")),
        "inspiration": scene.get("inspiration", ""),
        "takeaways": scene.get("takeaways", []),
    }

    generation = surface["generation"]
    control_payload = {
        "enable_sparse_keyframes": bool(generation.get("enable_sparse_keyframes", True)),
        "multi_keyframe_count": int(generation["multi_keyframe_count"]),
        "sparse_strengths": generation["sparse_strengths"],
        "sparsectrl_strength": float(generation["sparsectrl_strength"]),
        "zoe_strength": float(generation["zoe_strength"]),
        "canny_strength": float(generation["canny_strength"]),
        "animatediff_scale": float(generation["animatediff_scale"]),
        "ttm_path": scene.get("ttm_path", generation["ttm_path"]),
        "motion_program": {
            "surface_id": surface["id"],
            "surface_sha256": sha256(surface),
            "scene_id": scene_id,
            "semantic_authority": surface["semantic_authority"],
            "contract_reference": surface["contract_reference"],
            "grammar": scene["grammar"],
            "channels": channels,
            "structure": surface["structure"],
            "materials": surface["materials"],
            "lighting": surface["lighting"],
            "effects": surface.get("effects", {}),
            "camera": surface["camera"],
            "preservation": surface["preservation"],
            "frame_count": frame_count,
            "fps": fps,
            "loop": bool(scene.get("loop", False)),
        },
    }

    metadata = build_multikeyframe_metadata(
        hybrid=hybrid,
        control_payload=control_payload,
        duration_seconds=duration,
        fps=fps,
    )

    payload = {
        "schema": "wan.motion_control_scene.v0.1",
        "surface_id": surface["id"],
        "surface_sha256": sha256(surface),
        "scene_id": scene_id,
        "semantic_authority": surface["semantic_authority"],
        "contract_reference": surface["contract_reference"],
        "positive": positive,
        "negative": negative,
        "sections": sections,
        "hybrid": hybrid,
        "control_payload": control_payload,
        "metadata": metadata,
        "execution": {
            "workflow": scene.get("workflow", generation.get("workflow")),
            "binding_status": "requires_installed_node_and_parameter_mapping",
            "frame_count": frame_count,
            "fps": fps,
        },
    }
    payload["compiled_sha256"] = sha256(payload)
    return payload


def set_dotted(value: Dict[str, Any], dotted: str, replacement: Any) -> None:
    current: Any = value
    parts = dotted.split(".")
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    leaf = parts[-1]
    if isinstance(current, list):
        current[int(leaf)] = replacement
    else:
        current[leaf] = replacement


def build_experiment_variants(surface: Dict[str, Any]) -> List[Dict[str, Any]]:
    variants: List[Dict[str, Any]] = []
    experiment_seed = int(surface.get("experiment_seed", 314159))
    prompt_inputs = {
        "base_image_prompt": surface.get("base_image_prompt", ""),
        "subject": surface["subject"],
        "negative": list(surface.get("negative", [])),
        "semantic_authority": surface["semantic_authority"],
        "contract_reference": surface["contract_reference"],
    }
    for experiment in surface.get("experiments", []):
        for candidate in experiment["values"]:
            mutated = copy.deepcopy(surface)
            set_dotted(mutated, experiment["parameter"], candidate)
            variants.append(
                {
                    "experiment_id": experiment["id"],
                    "parameter": experiment["parameter"],
                    "value": candidate,
                    "prediction": experiment["prediction"],
                    "surface": mutated,
                    "surface_sha256": sha256(mutated),
                    "execution_seed": experiment_seed,
                    "prompt_inputs": copy.deepcopy(prompt_inputs),
                }
            )
    return variants
