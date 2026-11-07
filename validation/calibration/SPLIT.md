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

## split-4 (2026-11-02, BEFORE any calibration run): Walsh (G8) removed for this round
Reason: setup diagnostics at default and extreme factor values (runs/diag_setup.json, runs/diag_suspended.json) showed the
engine cannot start a breach from Walsh's 6 cm notch and 0.4 L/s trickle at the cal-1 grid (12.5 cm cells): at most 55 mm of
lowering and no rise in outflow in 600 s, against observed peaks within about 2 minutes. A 4 cm grid would cost about
150 h for the Walsh runs. This is an engine resolution limit, not a data problem, so all 11 Walsh tests (S1-S6, W1-W5)
are excluded from both calibration and validation in this round, and may return in a later round.
Also fixed in cal-1 before any run: non-cohesive cases use bed load plus Wu, Wang & Jia (2000) suspended load.
Calibration: E1S1, E1S3, E2S2, Castlewood, SouthFork, GooseCreek. Validation: E1S2, E2S1, E2S3, Poerua, Yigong, LaurelRun,
IMPACT 1-02, IMPACT 2C-02 (+ Taiwan pending).

## split-5 (2026-11-07, after the cal-1 fit, BEFORE any cal-2 code): Walsh (G8) S-series returns as SEEN validation
Reason: the Walsh S3 diagnostics (RUNS.md, 2026-11-03 to 2026-11-06) located the engine limits behind split-4 and
shaped cal-2 changes C1 and C2 (CAL2_PROPOSAL.md). Walsh can therefore not be a blind test, but it is the only
fully instrumented non-cohesive breach in the set and is kept as a separately reported check of those changes.
What has been seen (disclosure): Walsh Tables 2.1 / 3.1 and Figs 2.5-2.7 (all S and W tests; read for the case files
and the S3 diagnostics); Barlow et al. (2024) Table 1 (peak discharge for upstream slopes 10, 18.4, 25 and 30 deg);
model results for S3 only (diagnostic runs, never scored).
Rules, written before any cal-2 run on Walsh:
| Item | Rule |
|---|---|
| Cases | S-series tests whose case files exist (S1 18.4 deg, S3 30 deg, S5 25 deg). S2, S4, S6 and the W-series stay excluded for now (no case files; W needs the beach geometry checked). |
| Tier | `seen-validation`: never calibration, never in the stage-4 pass rate; reported in its own table next to stage 4. |
| Start state | Walsh stage 3 ("T = 0", onset of rapid rise): V pilot channel along the notch line, top width = breach width B* at T = 0 read from Walsh Fig. 2.7 for each test (flagged "read from figure"), sides at the friction angle, from where its floor meets the upstream face to the toe. Lake level at T = 0 from the case file (as in the S3 diagnostics). |
| Material | repose / friction angle 30.5 deg, measured for this sand (Beddoe & Take 2016, used by Barlow et al. 2024), replacing the assumed 33 deg; other values as in the case files. |
| Scored | Qp; time to peak from T = 0 (model datum: start of the run); B* at the time of the peak, read from Walsh Fig. 2.7. Same objective terms as calibration, plus the stage-4 acceptance limits. |
| Model | frozen cal-2 (factors and config), grid H/16; H/24 reported as a grid check. |
| Timing | run once, at stage 4, after cal-2 is frozen. |
