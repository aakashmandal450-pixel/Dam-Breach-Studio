# Lumped 1-D model — changelog

## 0.2.0 — 2026-11-20 (Phase 2, step 3: headcut, Theory Part 4)
- headcut.py: Robinson (1992) face stress, Hanson et al. (2001) undercut at failure and advance rate,
  capped at the 0.5H:1V surface-erosion rate when the face cannot stand (DSO-2017-02 App. A1).
- model.py: staged process for cohesive soils with k_d — stage 1 surface erosion at the end of the
  notch invert, stage 2 plunging headcut (H_h > d_c) with base scour and widening, stage 3 control
  lowered, residual-block sliding with uplift (located in time inside the step), hand-off to the
  core (stage 4). `headcut="off"` keeps the 0.1.0 surface model. c_u = q_u/2 where q_u is given.
- Tests: 35 pass (12 new: hand calculation of tau_hf, E_v sign, zero below tau_c, cap, stage switch,
  water balance across stage switches). dt-convergence now includes LaurelRun: all breach metrics
  CONVERGED (p 0.9-2.6) except E1S3 Tp (no breach, undefined) and LaurelRun B (changes 1e-5, round-off).
- First calibration-case results in docs/theory/04_headcut.md 4.9: E2S2 Tp 18.1 h (obs 22.5, was 1.3);
  E1S1 Qp 10.3 (obs 6.5) because b_h reaches the flume width in stage 2 (wall-shear sensitivity next).

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
