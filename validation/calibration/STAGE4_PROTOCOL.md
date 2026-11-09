# Stage 4 protocol: blind validation of the frozen cal-2 model (`stage4-protocol`)

**Written:** 2026-11-08, after cal-2 was frozen (`cal-2`, `python/calibration/cal-2.json`) and **before any stage-4
run**. `observed_validation.csv` has not been opened for its values (disclosure, s.8). Commit and tag
`stage4-protocol` together with the case files and scripts listed in s.7 before the first run. Nothing in this file
changes after that tag; the results are reported whatever they show.

## 1. Model

- Engine V3.3 with the cal-2 options (`cal2_config.json`, `CAL2_AMENDMENT_1.md`), Numba backend.
- Factors: frozen cal-2, **F_all = (f_kd 1, C_h 10, f_t 3.16)**. This is the primary model; every pass/fail is
  judged on it.
- All three factors are unstable by the cal-2 LOO rule. As in `CALIBRATION_PROTOCOL.md` s.LOO.4, they stay at
  F_all. Each blind case is also run at the distinct LOO factor sets of `cal-2.json`: LOO_1 = (0.1, 10, 3.16)
  (E1S1 left out) and LOO_2 = (3.16, 1, 10) (E2S2 left out). The min-max over F_all, LOO_1 and LOO_2 is reported as
  the **LOO envelope**, secondary and not in the pass rate.
- No change to the engine, configuration, factors or case files after the `stage4-protocol` tag.

## 2. Cases

### Blind (counted in the pass rate): the 8 validation-tier cases of `ASSIGNMENT.md`

Case files `python/calibration/cases/<id>.json`, built from `cases_validation_inputs.csv` and the input sections of
the sources only, by the cal-1 case rules (`cal1_config.json`: grid H/8 lab, H/6 field; section width = test section
width (lab), crest length if given, else 12 H; upstream stub H/2 and apron 2 H (field); power-law reservoir with
exponent A H / V, or 2 when only the storage is known; outfall downstream; reservoir level at the notch invert or
the level the source gives).

| Case | Built from | Main assumptions (flagged in the file) |
|---|---|---|
| E1S2 | Hanson et al. 2005 Tables 1, 3 (emb. 1, soil 2: qu 32 kPa, kd 2.0 cm3/N-s, tau_c 0.14 Pa); reservoir as E1S1 | d50, porosity, tan phi as soils 1/2 |
| E2S1 | same (emb. 2, soil 1: qu 22, kd 14.2, tau_c 0.14); reservoir Fig. 2 1.5 m curve as E2S2 | as E1S2 |
| E2S3 | same (emb. 2, soil 3 CL: qu 82, kd 0.038, tau_c 10); reservoir as E2S2 | d50, porosity, tan phi as E1S3 |
| Poerua | Wu 2016 Table 6.1 #9 | storage 6e6 m3 (midpoint of 5-7e6), exponent 2.67; no inflow; crest width 0 |
| Yigong | Wu 2016 Table 6.1 #8; DLBreach card (dam length 1000 m; inflow 859 m3/s to 24 h, 0 at 28 h) | exponent A H / V with H = 80 m (card: 86 m) |
| LaurelRun | Wu 2016 Table 6.3 #17 | inflow 100 m3/s, slopes, soil, kd 7.2 (DLBreach assumed; not scaled by f_kd) |
| IMPACT_1-02 | Wu 2016 Table 6.3 #15; T04-08-04 Table 1 (SP3 as-built geometry) and Fig. 2 (inflow, from the PDF vector paths) | reservoir area-height from DLBreach card Impactfld03 (another test at the same site); crest length 12 H |
| IMPACT_2C-02 | Wu 2016 Table 6.1 #6; T04-08-04 Table 3 | constant inflow = inflow volume over 0-2690 s / 2690 s (s.8 e); reservoir as IMPACT_1-02; crest length 12 H. **Case file added later** (s.6a) |

`kd_status` "measured" (E1S2, E2S1, E2S3, IMPACT_1-02) -> kd x f_kd; otherwise kd as given.

### Seen validation (reported separately, never in the pass rate): Walsh S1, S3, S5 (split-5)

Stage-3 start with a V pilot channel of top width B* at T = 0 (0.54 / 0.37 / 0.46 m, read from Walsh Fig. 2.7a),
friction angle 30.5 deg, frozen cal-2, `diag_walsh.py --model cal-2`. Grid H/16 (primary), H/24 (grid check);
600 s; outflow logged every 1 s. Scored on Qp, time to peak from the start of the run (Walsh T = 0), and B* at the
time of the model peak vs B* at the observed peak (1.76 / 1.40 / 1.29 m, Fig. 2.7a).

## 3. Run rules

- Grid, numerics and outputs as cal-2. Post-peak stop on; CPU budget 8 h per run, checkpoints every 30 min CPU.
  A run stopped by the budget is **censored**: it is scored from its state at the stop and flagged.
- `t_end`: lab cases 100,000 s; field cases 43,200 s, or the simulation period of the source's DLBreach input card
  if longer (Yigong 300,000 s). The engine also stops 600 s after the lake is drained.
- The early no-breach stop of cal-2 is **not** used (it needs the observed Tp).
- IMPACT_1-02: primary inflow = SP3 curve of T04-08-04 Fig. 2 (the report recommends the SP3 as-built data for this
  test); the IMPACT WP2 curve (about 5 % lower) is run at F_all as a sensitivity (reported, not scored for the pass
  rate).
- Every run is done once. A run that ends with an error (exception) is re-run unchanged; the error is reported.

## 4. Outputs (as cal-1 / cal-2)

Qp = peak outflow through the dam section; Tp = time of that peak from the model t = 0 (start of overtopping, or the
time origin of the source's inflow record for IMPACT_1-02); B = final breach width (crest rows, columns lowered by at
least 50 % of the maximum); breached = notch invert lowered by more than 50 % of the notch depth, with its time
`t_breach_phys_s` (checked every 60 s of model time; 600 s while morphology is accelerated in lab runs).

## 5. Scoring and acceptance limits (`score_stage4.py`)

Limits (from `SPLIT.md`, confirmed here): **peak within x1.5; time to peak within x2; final width within +/-50 %;
lake drawdown within +/-25 %; water and sediment balance error below 1e-6 of the volume released** (initial lake +
inflow - final lake, taken as initial - final lake volume).

- Each limit is applied to every blind case that has the matching observation. A **limit passes** if it is met in at
  least 2/3 of the cases where it applies ("at least 2 of 3 cases" in `SPLIT.md`, read as a share).
- No-breach case (E2S3, observed outcome "no breach"): the limit is "the model does not breach within the observed
  test duration" (sum of the stage times in `observed_validation.csv`; the whole run if none is given), plus the
  width limit. Qp and Tp limits do not apply.
- Lake drawdown: `observed_validation.csv` has no drawdown column (checked from the header only), so this limit is
  reported as not applicable. The model's end-of-run lake level is reported.
- A **case passes** if it meets all limits that apply to it. The headline result is the number of blind cases passing
  (of 8) and which limits pass.
- The calibration objective J (log errors of Qp and Tp, relative width error, no-breach penalty) is also reported
  per case and in total.
- LOO envelope and IMPACT_1-02 inflow sensitivity: reported next to the primary result, not used for pass/fail.
- Walsh: Qp within x1.5, time to peak within x2 and B* at peak within +/-50 % are reported per test and grid, in a
  separate table.

## 6. Order

6a. IMPACT_2C-02 waits for its inflow volume (s.8 e). The other runs start under the `stage4-protocol` tag. The
    2C-02 case file is then committed and tagged `stage4-protocol-2c` (built by the rules above, nothing else
    changed) before its runs. `run_stage4.py` re-run picks up only the missing runs and rewrites the manifest.
    Scoring (step 4) waits until every run, 2C-02 included, has a result. If no inflow volume can be obtained,
    2C-02 is reported as "boundary data missing" and left out of the pass rate (7 blind cases), recorded before
    scoring.

1. Commit this protocol, the case files, `cases.py`, `run_stage4.py`, `score_stage4.py` and `diag_walsh.py`; tag
   `stage4-protocol`.
2. `run_stage4.py` (laptop, Numba, 5 workers) runs everything and writes `runs/stage4/MANIFEST.json` (SHA-256 of
   every result and of the code, config and case files). It never opens `observed_validation.csv`.
3. Commit the results and the manifest; tag `stage4-runs`.
4. `score_stage4.py` checks every result against the manifest (refuses on any difference), opens
   `observed_validation.csv` for the first time, and writes `STAGE4_RESULTS.json` / `.md`. Commit; tag
   `stage4-results`. Report in `RUNS.md` and the handoff, whatever the outcome.

### 6b. Addendum, 2026-11-09 (before any IMPACT_2C-02 run and before scoring; tag `stage4-protocol-2c`)

All 28 other runs finished on 2026-11-09 (2.0 h, 0 errors, 0 censored; manifest written); no result was looked at.
IMPACT_2C-02 case file: inflow constant 1,100 m3 / 2690 s = 0.409 m3/s (s.8 e). Initial lake level = notch invert
(4.90 m), not the 4.10 m of Wu (2016) Table 6.1: by the case rule (s.2) the lake starts at the notch invert unless the
source gives the level at breach, and 4.10 m is the DLBreach simulation start level. The only inflow record covers the
breach period (T = 0-2690 s), so model t = 0 (start of overtopping) is taken as record T = 0; starting at 4.10 m with
0.41 m3/s would need about 12 h of filling in the assumed reservoir before any overtopping. This reading was chosen
from the inputs only. Crash check (120 s) passed. Then: `run_stage4.py` adds the three 2C-02 runs and rewrites the
manifest; commit and tag `stage4-runs`; score.

## 7. Files under the `stage4-protocol` tag

`validation/calibration/STAGE4_PROTOCOL.md`; `python/calibration/cases/{E1S2, E2S1, E2S3, Poerua, Yigong, LaurelRun,
IMPACT_1-02, WalshS1, WalshS3, WalshS5}.json` (IMPACT_2C-02 under `stage4-protocol-2c`, s.6a); `python/calibration/{cases.py, run_stage4.py,
score_stage4.py, diag_walsh.py}`. The engine, `fast_hydro.py`, `fast_morph.py`, `cal-2.json` and
`cal2_config.json` are unchanged since `cal-2`.

## 8. Disclosure: what has been seen

a. The validation sources were read on 2026-10-31 (previous sessions) to compile `cases_validation_inputs.csv` and
   `observed_validation.csv`; the observations were written to the separate file then and have not been used since.
   In building the stage-4 case files (2026-11-08) only input sections were extracted, by line range or by figure.
b. While locating Hanson et al. (2005) Table 3, a text search printed one sentence of the results section giving
   peak discharges "6.5 and 1.8 m3/s for soils 1 and 2" (6.5 m3/s is E1S1, a calibration case; 1.8 m3/s is probably
   E1S2 or E2S1). Seen by the modeller; no input or rule was changed after it.
c. `observed_validation.csv`: the header line (column names) and the row ids were printed with every digit masked,
   to write the scorer. No values were seen.
d. E2S3's outcome "no breach" has been known since `ASSIGNMENT.md` (split-2): it is part of the case description.
e. IMPACT_2C-02: T04-08-04 gives no inflow hydrograph for this test (Fig. 7 shows outflows only). The inflow volume
   over 0-2690 s is stated in a volume-balance paragraph that also gives the observed outflow volume. On 2026-11-09
   the modeller extracted only the period end and the inflow volume with a pattern match on the sentence "...from
   time T=0 to T=<n> seconds. The inflow volume for this period of time is approximately <v> m3" (result: 2690 s,
   1,100 m3); no other part of the paragraph was displayed.
f. T04-08-04 Fig. 2 (inflow, IMPACT_1-02) was cropped to its own area before viewing; Fig. 3 (water level) on the
   same page was not viewed.
g. Walsh (seen cases): all observations listed in split-5 have been seen. While building the stage-4 runner, Walsh
   S3 was run once at the stage-4 settings (frozen cal-2, H/16, 300 s; peak 0.388 m3/s at 208 s, B* at peak 1.58 m,
   observed 0.24 m3/s, 73 s, 1.40 m). Nothing was changed after it; the scored Walsh runs are the ones made by
   `run_stage4.py`.
h. Crash check (2026-11-08): each blind case was run for 120 s of model time (frozen cal-2) to catch setup errors;
   only the stop cause, step count and balance errors were printed (no outflow, width or lowering).
