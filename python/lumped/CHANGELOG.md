# Lumped 1-D model — changelog

## 0.1.0 — 2026-11-20 (Phase 2, steps 1-2: overtopping core)
- hydraulics.py: exact critical-flow trapezoid weir (default), DL Breach weir option, submergence,
  crest overflow, Manning normal depth and shear (Theory Part 1).
- sediment.py: cohesive excess-shear; DL Breach total load (Wu 2000 bed + Zhang/Guo suspended) with
  the DL Breach steep-slope correction; Chiew-Parker option; non-equilibrium relaxation (Theory Part 2).
- geometry.py: dam profile, side areas, planar bank stability beta = (alpha_s + beta_s)/2, vertical
  while a vertical bank is stable; Culmann cross-check (Theory Part 3).
- model.py: explicit fixed-step integration; flat-top + downstream-slope reaches; erosion allocated over
  bed and walls; slope rotation about the toe (Appendix 3A); mass-failure wedges; valley-width limit;
  reservoir positivity; case adapter using the 2-D engine's reservoir curves.
- Not yet: headcut (Part 4), piping (Part 5), impulse wave (Part 6), moraine (Part 7), adaptive dt (Part 8).
- Tests: 23 pass. dt-convergence (dt, dt/2, dt/4) on the six calibration cases: 13 of 18 metrics
  CONVERGED with p ~ 1; E1S3 is a no-breach case (Tp undefined); E2S2 Qp changes < 1 % per halving but
  p = 0.35.

## 0.0.1 — 2026-11-20 (Phase 0)
- Package created on branch `lumped-1d`, after the 2-D engine was frozen at tag `v34-final`.
- Test runner (`tests/run_all.py`) and launcher (`run_lumped_tests.ps1`) in place; no physics yet.
