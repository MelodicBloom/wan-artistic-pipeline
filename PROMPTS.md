# Prompt Design Document

> A human-readable companion to `prompt-packs/surreal-ethereal-dancer.json`.
> Describes the complete semantic, motion, timing, and meaning architecture of the series.

---

## Series Overview

Five video generations forming a unified arc:

| # | Name | Palette | Motion Type | Camera | Duration |
|---|------|---------|-------------|--------|----------|
| 01 | Liquid Bloom Dance | Gold, marble white | Undulation | Slow orbit + push | 6s |
| 02 | Abalone Dreamscape | Teal, cobalt, pearl | Lateral sway | Static micro-float | 7s |
| 03 | Golden Flow Motion | Amber, warm white | Underwater flow | Slow dolly + tilt | 5s |
| 04 | Nacre Bloom | Pearl, black, spectrum | Dissolution | Locked | 7s |
| 05 | Void Dancer | Jade, cold gold, void | Weightless float | Wide → portrait | 8s |

**Series arc:** `warmth → cool → kinetic → dissolution → cosmic`

---

## Controlnet Parameter Rationale

Each hybrid uses different ControlNet weights based on the type of motion it requires:

- **High SparseCtrl** (0.80) for hybrids with strong camera moves (02, 05) — locks figure position so camera motion reads cleanly.
- **Lower SparseCtrl** (0.60) for dissolution hybrid (04) — allows natural dissolution without pose fighting it.
- **Higher Canny** (0.50–0.55) for hybrids with complex fabric and edge work (03, 04).
- **AnimateDiff scale 1.1** only on hybrid_03 — needed for fabric trailing physics.

---

## Easing Vocabulary

| Term Used | Behavior | Where Applied |
|-----------|----------|---------------|
| cubic ease-in-out | Symmetric acceleration/deceleration | Camera orbits, body undulations |
| sinusoidal | Smooth oscillation, no hard stops | Lateral sways, orbital drifts |
| ease-out fluid | Fast initiation, drag deceleration | Arm extensions, fabric unfolding |
| exponential decay | Oscillation that dies out | Fabric flutter after peak extension |
| linear continuous | Constant velocity, no ramp | Background swirls, nebula expansion |
| ease-in acceleration | Slow start building to full speed | Dolly moves, dissolution progression |

---

## Timing Cue Map

Key emotional beats across the series (all in seconds from clip start):

```
hybrid_01:  0.3s body start │ 1.5s first bloom │ 3.0s petal peak │ 4.5s camera peak
hybrid_02:  0s sway start   │ 3.5s shimmer peak │ 5.0s swirl peak │ 5.5s fade begins
hybrid_03:  0s in-motion    │ 0.3s fabric trail │ 4.0s lighting peak │ 3.0s dolly mid
hybrid_04:  0.5s dissolve   │ 1.0s rose 1 bloom │ 2.6s rose 3 bloom │ 6.5s full dissolve
hybrid_05:  0s float start  │ 2.5s pull-in begins │ 6.0s portrait reached │ 8.0s hard cut
```

---

## Work Alignment Notes

**AURELITH:** The nacre and wood-grain textures map directly to AURELITH's computational material shaders. The depth/normal decomposition in the Zoe+Canny ControlNet stack mirrors the GLSL normal map blending in the WebGL surface system.

**Melodyfire:** The dancer is the visual expression of Melodyfire's core concept — rhythm made into a unified creative body. The timing cue map above could drive audio-reactive parameter changes.

**Beats & Boxes:** The dark void environments with particle/floral reactive elements are a direct translation of the immersive installation design — screens replaced by video generation.

**Shader Gallery:** Hybrid_04's prism fracture effect (spectral bands on dissolution boundary) is the same light-refraction logic used in the interactive shader gallery's edge-normal visualization.

---

## Meaning → Intent → Inspiration (Summary)

| Hybrid | Meaning | Intent | Key Inspiration |
|--------|---------|--------|-----------------|
| 01 | Transformation without rupture | Establish visual language | Ana Mendieta, Sugimoto |
| 02 | Surrender and receptivity | Cool counterpoint to 01 | Turrell, Kusama |
| 03 | Momentum as identity | Maximum kinetic energy | Loïe Fuller, fluid dynamics |
| 04 | Self as temporary coherence | Emotional climax | Bill Viola, anatta |
| 05 | Solitude as freedom | Earned intimate closing | Kubrick, Agnes Martin |

---

*This document is auto-generated from `prompt-packs/surreal-ethereal-dancer.json`. Edit the JSON as the source of truth.*
