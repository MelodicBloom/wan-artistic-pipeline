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
from src.batch_scheduler import build_batch_manifest

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

    def test_scheduler_preserves_compiled_control_surface_metadata(self) -> None:
        compiled = compile_scene(self.surface, "0A")
        jobs = [{
            "name": "compiled_0a",
            "positive": compiled["positive"],
            "negative": compiled["negative"],
            "seed": 314159,
            "_hybrid": compiled["hybrid"],
            "metadata": compiled["metadata"],
        }]
        manifest = build_batch_manifest(
            jobs=jobs,
            control_payload=compiled["control_payload"],
            gen_cfg={"duration_seconds": 8, "fps": 24},
            ttm_path=compiled["control_payload"]["ttm_path"],
            batch_index=0,
        )
        metadata = manifest[0]["metadata"]
        self.assertIn("motion_program", metadata)
        self.assertEqual(self.surface["structure"], metadata["motion_program"]["structure"])
        self.assertEqual(self.surface["materials"], metadata["motion_program"]["materials"])
        self.assertFalse(metadata["motion_program"]["loop"])
        self.assertEqual(compiled["metadata"]["keyframes"], metadata["keyframe_set"]["keyframes"])

    def test_stationary_regions_reject_unknown_geometry_primitives(self) -> None:
        invalid = copy.deepcopy(self.surface)
        invalid["scenes"][0]["channels"][0]["target"] = "outer_anchor"
        invalid["scenes"][0]["channels"][0]["primitive"] = "scale.local"
        errors = validate_surface(invalid)
        self.assertTrue(any("not permitted on stationary region" in error for error in errors), errors)

    def test_generation_fields_are_validated_before_compile_indexing(self) -> None:
        invalid = copy.deepcopy(self.surface)
        for field in ("sparse_strengths", "sparsectrl_strength", "zoe_strength", "canny_strength", "animatediff_scale", "ttm_path"):
            invalid["generation"].pop(field)
        errors = validate_surface(invalid)
        self.assertTrue(any("generation.sparse_strengths is required" in error for error in errors), errors)
        with self.assertRaisesRegex(ValueError, "generation\.sparse_strengths is required"):
            compile_scene(invalid, "0B")

    def test_both_immutable_authority_references_are_required(self) -> None:
        invalid = copy.deepcopy(self.surface)
        invalid["semantic_authority"].pop("commit")
        invalid["contract_reference"].pop("commit")
        errors = validate_surface(invalid)
        self.assertTrue(any("semantic_authority.commit is required" in error for error in errors), errors)
        self.assertTrue(any("contract_reference.commit is required" in error for error in errors), errors)

    def test_keyframe_notes_keep_semantic_anchors_for_supported_counts(self) -> None:
        hybrid = {
            "id": "notes",
            "name": "notes",
            "motion": {"body": {"type": "test", "easing": "linear"}},
            "timing": {},
            "camera": {},
            "keyframe_notes": ["START", "ENTRY", "PEAK", "END"],
        }
        for count in (2, 3, 4, 5):
            metadata = build_multikeyframe_metadata(
                hybrid=hybrid,
                control_payload={"multi_keyframe_count": count, "sparse_strengths": {"start": 0.9, "middle": 0.65, "end": 0.9}},
                duration_seconds=8,
                fps=24,
            )
            self.assertEqual("START", metadata["keyframes"][0]["pose"])
            self.assertEqual("END", metadata["keyframes"][-1]["pose"])

    def test_final_keyframe_maps_to_emitted_frame(self) -> None:
        compiled = compile_scene(self.surface, "0B")
        final = compiled["metadata"]["keyframes"][-1]
        self.assertEqual(191, final["frame_index"])
        self.assertAlmostEqual(191 / 24, final["t"], places=6)
        self.assertEqual(192, compiled["metadata"]["frame_count"])

    def test_compiled_motion_program_retains_loop_material_and_structure_controls(self) -> None:
        compiled = compile_scene(self.surface, "0B")
        program = compiled["control_payload"]["motion_program"]
        self.assertFalse(program["loop"])
        self.assertEqual(self.surface["structure"], program["structure"])
        self.assertEqual(self.surface["materials"], program["materials"])

    def test_experiment_variants_hold_seed_and_prompt_inputs_constant(self) -> None:
        variants = build_experiment_variants(self.surface)
        for experiment_id in {item["experiment_id"] for item in variants}:
            subset = [item for item in variants if item["experiment_id"] == experiment_id]
            self.assertEqual({314159}, {item["execution_seed"] for item in subset})
            self.assertEqual(1, len({repr(item["prompt_inputs"]) for item in subset}))

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
        self.assertEqual(1.0, path["motions"][0]["factor_start"])
        self.assertEqual(1.0, path["motions"][0]["factor_end"])
        self.assertEqual(1.016, path["motions"][0]["peak_factor"])
        self.assertEqual(191, path["motions"][0]["end_frame_index"])


if __name__ == "__main__":
    unittest.main()
