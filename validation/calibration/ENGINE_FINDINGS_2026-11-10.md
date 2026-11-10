# Engine findings after stage 4 (2026-11-10): numerical and physics errors behind the stage-4 failure

Post-stage-4 diagnosis on seen cases. These are diagnostic runs only: no engine file, case file or frozen result was
changed. Scripts: `/tmp` diagnostics, to be added to `python/diagnostics/` with V3.4. All cases used here (Castlewood,
Laurel Run, Yigong, Poerua) have been seen; any fix must be pre-registered and tested on the split-6 hold-out.

## 1. Steep-slope error of the hydrostatic reconstruction (mathematical; affects every case)

- **Test.** Steady flow down a plain 1:2.2 slope (Manning n 0.04), first order, compared with the exact normal flow:

  | Cell size | Bed drop per cell | Velocity / exact | Bed shear / exact |
  |---|---|---|---|
  | 13.3 m | 6.0 m | 25 % | 4 % |
  | 3.33 m | 1.5 m | 38 % | 10 % |
  | 1.0 m | 0.45 m | 52 % | 22 % |
  | 0.25 m | 0.11 m | 72 % | 46 % |

- **Cause.** With the Audusse et al. (2004) hydrostatic reconstruction, the face bed is max(zL, zR) and the face
  depths are reduced to it. When the bed drops more across a cell face than the water is deep (dz >> h, i.e. thin
  flow on a dam face), the lower cell's face depth is 0. The bed-slope momentum source it receives is then about
  0.5 g h^2 instead of g h dz. Gravity down the face is clipped, the flow cannot accelerate, depth is overestimated
  and velocity and shear are underestimated. The error grows with dz / h, i.e. with the cell size. This is a known
  property of the scheme (Delestre et al. 2012; Morales de Luna, Castro & Pares 2013; Chen & Noelle 2017).
- **Consequences.**
  - Erosion on downstream faces is a small, grid-dependent fraction of what it should be.
  - Peaks rise with refinement: Laurel Run, as calibrated, H/6 / 9 / 12 / 18 gives 609 / 1,046 / 1,184 / 1,436
    m3/s (observed 1,050).
  - Field cases (coarse cells, large dz per cell) are hit hardest, which explains the low field peaks.
  - The calibration factors compensated for it: C_h and f_t were pushed to the top of their ranges, by a different
    amount per case. That accounts for the unstable factors and for their failure to transfer across scale.
    Walsh over-predicts on finer grids (H/24 > H/16) because factors fitted to a coarse-grid error are applied where
    the error is smaller.
- **Candidate fixes.**
  - Chen & Noelle (2017) subcell hydrostatic reconstruction, designed for this steep-slope case.
  - A slope-source treatment for steep thin flows (Hou et al. 2013; Liang & Marche 2009).
  - Verification: inclined-plane normal flow within a few % at the field grid, lake at rest exact, wet/dry fronts.

## 2. Headcut acting under the lake (physics; causes breach self-sealing)

- **Evidence.**
  - Castlewood at H/9: the crest was cut 14 m deep, yet outflow fell from 259 m3/s to about 0, with the lake 0.2 m
    below the crest.
  - Process accounting for the lake-side rows (depth 15-18 m, speed 0.1-0.3 m/s), t = 720-900 s: C1 headcut
    removed 1,509 m (summed over cells) into suspension, and transport redeposited 1,476 m in place. The lowest pass
    lake -> outlet rose from 16.6 m to 20.8 m, sealing the breach.
  - Yigong: outflow rose to 12,050 m3/s at 19.3 h, then fell to 18 m3/s within 40 min with the lake still at 77 m.
    Crest lowering fell from 69 m to 60 m (refill).
- **Cause.** The C1 activation tests slope, a wet foot and q > 0, but not whether the scarp is a free overfall. In
  deep, slow lake water q = h u is large (17 m x 0.1 m/s), so R = C (q H)^1/3 is large although nothing plunges. The
  energy law (Temple; Hanson) applies to a free overfall only.
- **Fix tested (diagnostic patch).** Headcut only where the tailwater surface at the foot is below the bed at the
  scarp top. Castlewood H/6 / 9 / 12: 2,119 / 374 / 345 m3/s -> 1,654 / 1,909 / 2,261 m3/s (the choking is gone).

## 3. Grid size inside the sediment closure (mathematical)

- Ls = max(5 h, dx) in `Morphology._transport_exner`. Where 5 h < dx (shallow flow on faces), the pickup rate
  scales as 1/dx: halving the cells doubles erosion.
- The exponential relaxation 1 - exp(-dt u / Ls) is stable without the floor.
- Diagnostic Ls = 5 h, together with fix 2: the Castlewood H/6 -> H/9 change drops from +15 % to +8 % (2,001 /
  2,158 m3/s). It affects only capacity-law (non-cohesive) cases; cohesive detachment uses Ls only for deposition.

## 4. Field-scale start geometry (case rules)

- In every field case the pilot notch is narrower than one cell (0.23-0.91 of a cell) and is widened to a full cell.
  The lab cases resolve the notch with about 7 cells.
- Poerua and Yigong: the cell-averaged crest is 0.17-0.20 m below the nominal crest, so the lake starts above the
  model crest and spills over the whole crest (Poerua: no erosion at all).
- Fix: refine near the notch, or represent the notch at sub-cell scale; set the start level relative to the model
  crest.

## 5. What this means

- The stage-4 failure is largely numerical and implementation error, not only missing physics: the shear on dam
  faces is too low and grid-dependent (1), the breach can seal itself (2), and the closure contains dx (3).
- The calibrated factors absorbed these errors, which is why they were unstable and did not transfer.
- **V3.4 order:** fix 1, 2 and 3; add a grid-convergence test (H/6, H/9, H/12 on two field cases, peak within 10 %)
  to the verification suite before any calibration; then recalibrate and test once on split-6.
- Probabilistic and ML layers come after: an emulator of a grid-dependent engine would learn the numerical error.
