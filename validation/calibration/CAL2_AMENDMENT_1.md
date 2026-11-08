# cal-2 amendment 1: scarp threshold of the C1 headcut (`cal2-amend-1`)

**Status:** adopted 2026-11-08, before the cal-2 grid started. Runs of calibration cases with the new switches so far
are engine checks and probes, not calibration runs; none enters the fit (section 4).
Validation observations (`observed_validation.csv`) are still unopened (amendment 2).

**Changes:** one pre-registered value in `CAL2_PROPOSAL.md` s.2 (C1). Nothing else in the proposal changes: cases,
split, objective, factor ranges, runner, early no-breach stop, predictions P1-P7, and the commitment that stage 4 runs
on cal-2 whatever P1-P7 show.

| Item | Proposal (`cal2-proposal`) | Amended |
|---|---|---|
| C1 `headcut_min_slope` (overall slope a scarp must reach to be active) | 0.1 | **0.5** (the V3.2.2 value) |
| C1 `headcut_seg_slope` (cell-to-cell slope that joins drops into one scarp) | 0.1 | 0.1 (unchanged) |

## 1. What the T3 replays showed (`RUNS.md`, "T3 replays", 2026-11-07/08)

The proposal (s.3, T3) asks for diagnostic replays of Walsh S3 and Dig Tsho before the grid, and says large
departures are investigated, not tuned. Two findings bear on the C1 threshold.

1. **With threshold 0.1, a whole dam face is one headcut.** A scarp is active when its overall slope is >= the
   threshold. Embankment faces of the calibration and validation dams are 1:2 to 1:3.1 (slope 0.32-0.5), so at 0.1
   the entire downstream face counts as a single scarp of the full dam height, from the first minute of overflow,
   and the energy law R = C (q H)^(1/3) is applied with H = dam height. At prototype scale this dominates the breach:
   Dig Tsho (Westoby geometry, 5 kPa) peaks at 14,037 m3/s with the breach across the full 250 m crest, against
   3,751 m3/s with the V3.2.2 defaults; C1 alone gives 15,117 m3/s, C2-C4 alone 2,863 m3/s. A headcut in the sense of
   the energy law (Temple 1992; Hanson et al. 2001; the WinDAM/DLBreach stage-2 headcut) is a steep overfall scarp
   that forms on the face and migrates, not the face itself.
2. **Walsh no longer needs 0.1.** The value 0.1 came from the Walsh diagnostics (F5, run (c)), made before an
   all-pairs collapse existed, when lowering the breach lip had to come from the headcut. With C2 in place, Walsh S3
   (H/16, pilot channel, f_t = 3, phi 30.5 deg) gives: threshold 0.1: 213-231 L/s; threshold 0.5: 182 L/s;
   headcut off: 168 L/s; observed 240 L/s. The rise (55-80 s) and width (1.58-1.71 m) hardly change. Peaks scatter
   about +/-10 % between neighbouring settings (threshold events), so 0.5 vs 0.1 is within about 2 scatter widths.

## 2. Reasons for the change, and what is not a reason

- Reason (a), definition: a threshold below the face slope of ordinary embankments makes every face a headcut, which
  is not the process the energy law describes. 0.5 (about 27 deg) is above the face slopes, so a scarp exists only
  where erosion has steepened the bed beyond the face; this is the V3.2.2 value, used in cal-1.
- Reason (b), the basis of 0.1 is gone: it was chosen to make the Walsh lip erode, and C2 now does that.
- **Not a reason:** Dig Tsho's published peak (about 1,600 m3/s). Dig Tsho is the stage-5 case and its value is
  screening context only; the change is not chosen to move it toward that number, and no other value was tried
  against it. (At 0.5, Dig Tsho still peaks at 7,161 m3/s with C_h = 1: the scarp-height law remains strong at
  prototype scale. The C_h grid, down to 10^-1.5, is where that is decided, by the calibration cases.)
- The calibration fit played no part: the threshold was decided before any calibration case was run or scored with
  the cal-2 configuration (section 4), and the validation observations are unopened.

## 3. Consequences

- `cal2_config.json` sets `headcut_min_slope = 0.5`. Walsh S3 stays a seen validation-type case (split-5) and is
  reported separately; its T3 replay at the cal-2 setting is in `RUNS.md`.
- P3 (headcut identifiable on E2S2) and P1 (stable C_h) are unchanged and now test the amended rule.
- If the cal-2 fit shows that one C_h cannot serve lab and prototype dams (P1 fails on C_h), that is reported as a
  finding about the scarp-height energy law across scales; it is not fixed by a further change before stage 4.

## 4. Calibration cases run with the V3.3 switches so far (none enters the fit or any choice)

- Engine development (2026-11-07, threshold 0.1, H/4, cal-1 or default factors): C1+C2 smoke runs of E1S1, E2S2 and
  Castlewood, and the C5 speed / agreement comparisons on E1S1, E2S2, Castlewood and Walsh S3. Outputs were read for
  correctness (mass balance, NumPy vs Numba) and speed, not scored against observations.
- After this amendment was decided (2026-11-08, cal-2 configuration): one cost probe per case at default factors
  (Castlewood, South Fork, Goose Creek, E2S2, E1S3; 25 min CPU cap) to size the grid, and the runner smoke test below.
  They compute J as a check of the scoring path. Their results are reported in `RUNS.md` for completeness; they are
  not used for any choice and not reused by the grid, which runs every factor set itself (output folder
  `runs/calibration_grid_cal2`, empty at the start).

Runner smoke test:
`python/calibration/smoke_cal2.py`, E1S1 only: cal-2 options applied; cal-1 build unchanged; the early no-breach stop
ends a non-breaching run at 3 x observed Tp as completed and it is scored; a breaching run is not stopped early;
resume from a checkpoint reproduces the uninterrupted run exactly; balances <= 5e-11 m3.
