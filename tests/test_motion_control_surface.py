from __future__ import annotations

import copy
import unittest
from pathlib import Path

from src.motion_control_surface import (
    build_experiment_variants,
    compile_scene,
    load_surface,
    validate_surface,
)
from src.prompt_engine import build_multikeyframe_metadata

ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "prompt-packs" / "motion-control-surface-calibration.json"
TTM = ROOT / "ttm_paths" / "locked_front_micro_dolly.json"


class MotionControlSurfaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.surface = load_surface(SURFACE)

    def test_calibration_surface_validates(self) -> None:
        self.assertEqual([], validate_surface(self.surface))

    def test_scene_compilation_is_deterministic(self) -> None:
        first = compile_scene(self.surface, "0B")
        second = compile_scene(self.surface, "0B")
        self.assertEqual(first, second)
        self.assertEqual(first["compiled_sha256"], second["compiled_sha256"])
        self.assertEqual(192, first["execution"]["frame_count"])
        self.assertEqual(24, first["execution"]["fps"])
        self.assertEqual(
            "requires_installed_node_and_parameter_mapping",
            first["execution"]["binding_status"],
        )

    def test_surface_compiles_to_existing_hybrid_metadata_shape(self) -> None:
        compiled = compile_scene(self.surface, "0A")
        hybrid = compiled["hybrid"]
        self.assertEqual("radial.hinged_aperture", hybrid["motion"]["body"]["type"])
        self.assertEqual("locked_front", hybrid["camera"]["orientation"])
        self.assertEqual(4, len(compiled["metadata"]["keyframes"]))
        self.assertIn("charged state", compiled["metadata"]["keyframes"][0]["pose"].lower())
        self.assertNotIn("arm raised", compiled["metadata"]["keyframes"][0]["pose"].lower())

    def test_legacy_prompt_engine_still_uses_default_pose_notes(self) -> None:
        hybrid = {
            "id": "legacy",
            "name": "Legacy dancer",
            "motion": {"body": {"type": "undulation", "easing": "cubic ease-in-out"}},
            "timing": {},
            "camera": {},
        }
        metadata = build_multikeyframe_metadata(
            hybrid=hybrid,
            control_payload={
                "multi_keyframe_count": 4,
                "sparse_strengths": {"start": 0.9, "middle": 0.65, "end": 0.9},
            },
            duration_seconds=6,
            fps=24,
        )
        self.assertIn("arm raised", metadata["keyframes"][0]["pose"])

    def test_stationary_outer_anchor_cannot_receive_geometric_motion(self) -> None:
        invalid = copy.deepcopy(self.surface)
        invalid["scenes"][0]["channels"][0]["target"] = "outer_anchor"
        errors = validate_surface(invalid)
        self.assertTrue(any("stationary region" in error for error in errors), errors)

    def test_global_spin_and_transparent_duplicate_are_required_failures(self) -> None:
        invalid = copy.deepcopy(self.surface)
        invalid["preservation"]["prohibited"].remove("whole_object_spin")
        invalid["preservation"]["prohibited"].remove("transparent_duplicate")
        errors = validate_surface(invalid)
        self.assertTrue(any("whole_object_spin" in error for error in errors), errors)
        self.assertTrue(any("transparent_duplicate" in error for error in errors), errors)

    def test_one_factor_experiment_variants_preserve_unrelated_controls(self) -> None:
        variants = build_experiment_variants(self.surface)
        self.assertEqual(15, len(variants))
        fold = [item for item in variants if item["experiment_id"] == "EXP-FOLD"]
        self.assertEqual([0.2, 0.4, 0.6], [item["value"] for item in fold])
        self.assertEqual(
            [0.2, 0.4, 0.6],
            [item["surface"]["scenes"][1]["channels"][0]["strength"] for item in fold],
        )
        self.assertEqual(self.surface["camera"], fold[0]["surface"]["camera"])
        self.assertEqual(self.surface["lighting"], fold[0]["surface"]["lighting"])

    def test_calibration_ttm_has_no_orbit_or_background_motion(self) -> None:
        import json

        path = json.loads(TTM.read_text(encoding="utf-8"))
        self.assertEqual(0, path["constraints"]["orbit_degrees"])
        self.assertEqual(0, path["constraints"]["background_motion"])
        self.assertTrue(path["constraints"]["first_last_camera_match"])


if __name__ == "__main__":
    unittest.main()
