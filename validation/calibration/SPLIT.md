# Pre-registered calibration / validation split (split-1)

Written 2026-10-31, BEFORE any calibration run and before any case data were obtained.
This rule may not be changed after the first calibration run. A change before that is a new version (split-2) with a dated reason.

## Exclusions, applied first and logged in `EXCLUDED.md` with the reason
1. Piping or internal-erosion failures (the engine models overtopping only).
2. Cases without at least two of: peak outflow, time to peak, final breach width, final breach depth or lake drawdown.
3. Cases without enough geometry to build the prism (dam height, crest width, slopes or a profile, reservoir volume or stage-volume data).

## Assignment
| Group | Rule |
|---|---|
| G1 USDA-ARS (JET) | Sort tests by published test ID. Odd positions -> calibration, even -> validation. |
| G2 Reclamation (JET) | Same rule. |
| G3 DLBreach set | Split into sub-groups by material (non-cohesive, cohesive, composite). Within each, sort by case name; odd positions -> calibration, even -> validation. A sub-group of one -> validation. |
| G4 IMPACT field | All validation (field-scale hold-out). |
| G5 Wahl 1998 historic | Screening validation only: reported separately, never counted in the pass rate, never used to calibrate. |
| G6 Queen Bess 1997 | Validation (GLOF analogue hold-out). |
| G7 Dig Tsho | Reconstruction only (ensemble, `cal-1` frozen); never calibration or validation. |

## Blind handling
- Observed outputs of validation cases are stored in `observed_validation.csv`, separate from model inputs, and are not used until stage 4.
- Calibration may use only calibration-tier inputs and observations.
- Every assignment is listed in `ASSIGNMENT.md` and committed, with a git tag `split-1`, before the first calibration run.

## Acceptance limits (from the plan, to confirm before stage 4)
Peak within x1.5, time to peak within x2, final top width within +/-50 %, lake drawdown within +/-25 %, each passing in at least 2 of 3 cases; water and sediment balance below 1e-6 of volume moved in every case.

## split-2 amendments (2026-10-31, after reading the sources, BEFORE any calibration run)
Reason: the sources showed two situations the split-1 rules did not cover. No engine result on any case has been seen.
- Exclusion 4: embankments whose source specifies separate zones with different materials (core/shell, clay cover)
  are excluded, because the engine has one uniform material. Cases the source itself models as homogeneous stay in.
- Rule 3 interpretation: missing PRIMARY data (dam height, reservoir volume or stage-volume) -> exclude. Missing
  SECONDARY dimensions (crest width, a slope) may be taken from a figure or assumed, flagged as assumed in the case
  file, and covered by a sensitivity run. This matches how the DLBreach report treats its "a" (assumed) values.
- Duplicates across groups are kept once, in the most specific group (USDA-ARS E1S1 in G1; IMPACT field tests in G4).

## split-3 (2026-11-01, BEFORE any calibration run): new groups G8 (Walsh 2019) and G9 (Taiwan field tests)
Rules for the new groups, written before any engine run on them:
| Group | Rule |
|---|---|
| G8 Walsh (2019) Queen's tests | Two series, kept separate. Slope series S1-S6 and beach series W1-W5, each sorted by test ID: odd positions -> calibration, even -> validation. The two USGS tests (Walder et al. 2015) listed in Walsh's Table 2.1 are excluded under rule 3 (no reservoir data in our sources). |
| G9 Taiwan (Chao, Hung & Chen 2025) | Within each archive family (CP, NCP): run _1 -> calibration, _2 -> validation. Applied only after the exclusions pass on the archive contents. Dam material (at least grain size) counts as PRIMARY for these non-cohesive tests; without it the group is excluded. |
Observation sources for G8: peak discharge from Walsh Tables 2.1 and 3.1; time to peak and breach width over time from Walsh Figs 2.5-2.7 and 3.x (read from figures, flagged as such).
