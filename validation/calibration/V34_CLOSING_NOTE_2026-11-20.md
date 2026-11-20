# V3.4 (2-D engine) — closing note, 2026-11-20

The 2-D engine (`python/breach_engine_2d_v3_2.py`) is frozen at tag `v34-final`. Development moves to
a 1-D lumped morphodynamic model (`python/lumped/`, branch `lumped-1d`). The 2-D engine is kept as a
research thread; nothing is deleted.

## Why it was stopped
- Every V3.4 fix (F1-F7) added per-cell on/off rules: scarp slope gates (C1 cumulative, F7 per-cell),
  the free-overfall test (F2), collapse modes (F5). Each tripped differently on each grid.
- Grid convergence (H/9, H/12, H/15) failed on both Laurel Run and Castlewood for every variant tested
  (F1-F4, F1-F7, one-cell rule, overfall `any`/`free`). Peak flow and width oscillated or kept drifting.
- A grid-independent width (B_eq) showed the Castlewood width oscillation is physics, not measurement.
- The one-cell headcut rule converged on Castlewood only together with overfall `any`, and eroded Laurel
  wall to wall; the overfall test alone changes Castlewood Qp by a factor of ~3.5.
- Stage-4 blind validation with frozen cal-2 (2026-11-09): 2 of 8 cases passed all limits, J total 27.2.

## Findings worth keeping
- Over-widening at calibration-scale factors comes from F5 (bank_wedge) and F7 (face slope), about
  equally; F6 (hydro face flux) narrows the breach.
- Detachment laws on non-cohesive cases with default MaterialProps (tau_c = 1 Pa, n = 1) make Hanson and
  Partheniades algebraically identical; those sweep rows are invalid.
- GCI verdicts need an observed-order guard (0.5 <= p <= 3); outside it GCI collapses to ~0.

## Where the detail is
Project notes: HANDOFF_2026-11-19, V34_LAW_SWEEP_WIDTH_2026-11-19, V34_CONVERGENCE_BEQ_2026-11-19.
Results: runs/v34_convergence, runs/v34_convergence_beq, runs/v34_law_sweep, runs/v34_castlewood_refit,
runs/v34_isolation_f567. Tools: python/calibration/v34_*.py and run_v34_*.ps1.

The bad diagnostic script v34_grid_check_f7.py (wrong model, Qin = 0, false early peak) and its launcher
run_v34_f7.ps1 were removed at this tag.
