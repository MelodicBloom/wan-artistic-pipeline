# Motion Control Surface v0.1

The Motion Control Surface is the Wan/Comfy execution adapter for governed generative-motion semantics. It does not redefine Motion Oracle grammar names and it does not replace Observation Ad Pipeline contracts.

## Authority boundary

- **Motion Oracle** owns semantic topology, motion grammar names, material-response meaning, modifiers, easing profiles, and failure taxonomy.
- **Observation Ad Pipeline** owns provider-neutral Motion Program contracts, validation, hashes, calibration plans, and experiment receipts.
- **wan-artistic-pipeline** owns Wan-facing translation: sparse-keyframe metadata, TTM path choice, ControlNet strengths, frame count, workflow binding, runtime execution, and output metadata.

The calibration pack records immutable provisional source commits for the two upstream semantic/contract authorities. Those references should be advanced to their merged canonical commits after the upstream PRs land.

## Existing mechanism reused

`src/prompt_engine.py` already emits structured multi-keyframe metadata for hybrid prompt definitions. The control-surface adapter therefore compiles each scene into that existing hybrid shape rather than adding a second scheduler.

A small backwards-compatible extension allows `hybrid.keyframe_notes` to replace the dancer-specific legacy pose notes. Existing dancer packs continue using the original defaults; non-human sources can now define source-appropriate anchor states.

## Calibration pack

`prompt-packs/motion-control-surface-calibration.json` describes a deliberately clean sixfold relief reference with:

- named movable/stationary radial regions;
- explicit preservation locks;
- material behaviors for wood, paper, opal, labradorite, and abalone;
- scene `0B` using `radial.counterphase`;
- scene `0A` using `radial.hinged_aperture`;
- masked lighting, ombre, glow, bleed, and contained distortion;
- a locked-front camera;
- one-factor parameter experiments.

The generated base-image prompt is part of the calibration artifact so the reference can be regenerated without silently changing the control surface.

## Why the locked-front TTM path exists

Existing TTM paths are dancer/cinematic paths and include orbit. For topology-sensitive tests, orbit is a confounder: a model can substitute camera rotation for local structural choreography.

`ttm_paths/locked_front_micro_dolly.json` therefore constrains orbit, yaw, roll, and background movement to zero and uses only a 1.6% closed micro-dolly plus very low parallax on declared movable regions.

## Experiment rule

One-factor experiment variants preserve every unrelated field. Examples:

- fold strength `0.2 / 0.4 / 0.6`;
- petal phase offset `0.08 / 0.18 / 0.34s`;
- mineral-probe incidence `14 / 24 / 36°`;
- contained distortion frequency `0.42 / 0.8 / 1.2`;
- lens `32 / 48 / 85mm` at the same dolly amount.

Each experiment includes a pre-generation prediction. Candidate review should compare the observed effect with that prediction and record topology drift, edge stability, material spill, texture boiling, camera drift, and loop error.

## Current execution boundary

The adapter intentionally emits:

`binding_status = requires_installed_node_and_parameter_mapping`

The calibration pack leaves `generation.workflow` null. This is deliberate. The repository has working Wan/Comfy examples, but the current cinematic workflow includes dancer-specific OpenPose/SparseCtrl assumptions. Binding the new generic control surface to that graph without an installed-node inventory and a topology-safe control mapping would create a false executable contract.

Promotion to executable status requires:

1. capture the installed ComfyUI node inventory and exact Wan wrapper schema;
2. build or select a non-human I2V graph that accepts start image, temporal latent/frame count, prompt conditioning, TTM path, depth/canny as appropriate, and encoded output;
3. map every graph-bound control to a concrete node/input and validate the mapping;
4. run one calibration source through all five one-factor sweeps;
5. record seeds, model/checkpoint, graph hash, node patches, reference hash, output hash, and QA result.

Until then the subsystem is a valid deterministic adapter and calibration contract, not a claim of completed Wan execution.

## Verification

```bash
python -m unittest discover -s tests -p 'test_motion_control_surface.py' -v
```

The focused CI also validates the two JSON artifacts with the standard library before running the tests.
