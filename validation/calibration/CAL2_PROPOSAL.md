# cal-2 proposal: engine changes, tests, predictions (`cal2-proposal`)

**Status:** DRAFT, 2026-11-07. Written after cal-1 was fitted (`cal-1_candidate.json`, J = 8.34) and before any cal-2
code exists. Commit and tag `cal2-proposal` before any cal-2 engine code is used on a calibration case.
Validation observations (`observed_validation.csv`) are still unopened (amendment 2).

**Basis:** cal-1 fit (2026-11-07), Walsh S3 diagnostics (`RUNS.md`, 2026-11-03 to 2026-11-06), the engine profile and
Numba backend check (2026-11-07), and the literature on breach slope collapse (Barlow et al. 2024; Wu 2016 DLBreach
report; Wu et al. 2D model; BASEMENT, Volz et al. 2012; Swartenbroekx et al. 2010).

---

## 1. What cal-1 and Walsh showed

| Finding | Evidence |
|---|---|
| F1. One `f_kd` cannot fit the cohesive lab tests | per-case best f_kd: E1S1 10 (grid edge), E2S2 0.1, E1S3 about 3.16; LOO range of f_kd 31x |
| F2. Headcut migration is almost inactive | cohesive-case J barely changes across C_h 0.03-10, yet E2S2 spent about 18 h in Hanson stage 2 (headcut migration); E2S2 breaches at 2.3 h vs 22.5 h observed; LOO range of C_h 31x |
| F3. The headcut trigger is a cell-to-cell slope | `HeadcutMigration.migrate`: drop between neighbour cells / dx >= `headcut_min_slope` (0.5); the drop H in the rate law is also the one-cell drop, so a scarp spread over several cells is not seen and its rate is underestimated; x-direction only |
| F4. Banks fail only as "dry cell above wet toe" | `BankStability._collapse_pairs`: dry-dry and wet-wet pairs steeper than phi never fail; Walsh run (c) kept 36 cm dry cliffs at 70-80 deg and wet banks at 54 deg in c = 0 sand; widening stalled at about 1 m |
| F5. With (c) + (f) Walsh is reproduced with one rate factor | headcut threshold 0.1 + angle-of-repose collapse, f_t = 3: peak 222-252 L/s (obs 240), rise 50-70 s (73), width 1.58-1.68 m (about 1.6), H/16 and H/24 |
| F6. Non-cohesive bank law uses defaults unrelated to the material | lateral erosion for Castlewood / South Fork / Walsh uses kd = 1e-4 m/(s Pa) and tau_c = 1 Pa for every D50 (Shields tau_c: about 76 Pa at 100 mm, 11 Pa at 14 mm, 0.09 Pa at 0.12 mm) |
| F7. Non-cohesive breaches too wide, transport factor at the grid edge | cal-1: Castlewood B 66.7 vs 54.9 m, South Fork 176 vs 128 m, both at f_t = 10 (top of the range) |
| F8. Lateral erosion acts across the flume only | `LateralErosion.apply` compares y-neighbours only and divides by dy |
| F9. Goose Creek too small whatever the factors | Qp 180 vs 565 m3/s, B 14 vs 30.5 m; J 1.48-1.63 over the whole C_h range |
| F10. The second-order scheme is chaotic | a 1e-15 change in Manning n moves Qp by 3-4.5 % at spatial order 2 (7e-15 at order 1) |

## 2. Engine changes (V3.3)

Every change is a new `EngineConfig` option. **Defaults reproduce V3.2.2 exactly** (regression suites must pass
unchanged with defaults); cal-2 switches them on through `cal2_config.json`.

### C1. Scarp-based headcut trigger (F2, F3, F5)
- Along each column and each flow direction, a **scarp** is a run of consecutive downstream drops whose individual
  cell-to-cell slope exceeds `headcut_seg_slope` (0.1). Its height H_s is the sum of the drops and its length L_s
  the horizontal extent of the run.
- A scarp is active if H_s / L_s >= `headcut_min_slope` and H_s >= `headcut_min_height` (default 0, the cell-size-free
  form), the downstream cell is wet and the unit discharge exceeds 1e-6 m2/s.
- Retreat uses the scarp height: rate = C_h * headcut_C * (q * H_s)^(1/3) (energy method, unchanged law), applied to the
  top cell of the scarp; the removed volume goes to the cell below it, as now.
- Both x and y flow directions are checked (flow direction from the sign of qx, qy).
- cal-2 value of `headcut_min_slope`: **0.1** (from F5; this value was chosen on Walsh, whose observations have been
  seen, and is fixed before any cal-2 calibration run).
- Old behaviour: `headcut_mode = "cell"` (default); new: `"scarp"`.

### C2. General slope collapse (F4, F5)
- Every neighbour pair (x and y) is checked, not only dry-above-wet. A pair fails if its slope exceeds the critical
  angle for its state, or if the Culmann factor of safety is below the trigger (cohesive soils, unchanged formula).
- Critical angles: dry pair `collapse_phi_dry` and submerged pair `collapse_phi_wet` (a pair is submerged if both
  cells are deeper than `collapse_hswitch`). cal-2: both = the material friction angle, hswitch = h_dry. (An
  XBeach-style 16.7 deg submerged angle flattened the stable 30 deg submerged upstream face of Walsh in seconds and
  is not used.)
- Each pass moves half the excess so the two cells meet at the critical slope; up to `collapse_passes` (3, as now)
  passes per morph step; material lands in the lower cell (bed if dry, suspended store if wet); mass conserved.
- Old behaviour: `collapse_mode = "unsupported"` (default); new: `"all_pairs"`.

### C3. Material-consistent bank thresholds for non-cohesive soil (F6, F7)
- For non-cohesive material the excess-shear lateral law is **switched off**; banks retreat by bed erosion at the
  toe plus slope collapse (C2), as in XBeach, BASEMENT and the Wu 2D model. This removes the arbitrary kd = 1e-4 and
  tau_c = 1 Pa.
- Cohesive material keeps the lateral law with its measured kd and tau_c (unchanged).
- Option `lateral_noncohesive = "excess_shear"` (default, V3.2.2) or `"off"`.

### C4. Lateral erosion in both directions (F8)
- For cohesive material, `LateralErosion.apply` also compares x-neighbours (dividing by dx). Option
  `lateral_directions = "y"` (default) or `"xy"`.

### C5. Numba backend for calibration runs (speed)
- `fast_hydro.py` (verified bit-identical to the NumPy step on the calibration laptop, 2026-11-07) is used for every
  cal-2 run, together with Numba versions of the new C1/C2 kernels. Each new kernel is verified against a NumPy
  reference implementation of the same rule (tolerance 1e-9 relative on all scored quantities).

Not changed: transport laws, Hanson / Chen detachment, reservoir, boundaries, first-order hydraulics (F10: order 2
stays off), grid rule, adaptation length, morph acceleration, objective.

## 3. Tests before any cal-2 calibration run

T1. The four V3.2 suites pass unchanged with all new options at their defaults (NumPy and Numba).
T2. New unit tests (`tests/v3_3_tests.py`):
  - C1: the same physical scarp (height 0.3 m, slope 0.5) is detected and retreats at the same rate (within 10 %) at
    dx and dx/2; a gentle slope below the threshold is not active; y-direction scarps are found; mass conserved.
  - C2: a dry 60 deg step and a submerged 50 deg step relax to phi in both directions; a 25 deg slope with phi = 33
    deg is untouched; cohesive bank with c = 5 kPa below its Culmann height is untouched; mass conserved to 1e-12.
  - C3: non-cohesive with `"off"` produces no lateral-law erosion; cohesive unchanged.
  - C4: an x-facing cohesive bank retreats at the same rate as a y-facing one; mass conserved.
  - C5: Numba and NumPy agree for C1/C2 on random states and on full runs (as `compare_fast.py`).
T3. Diagnostic replays (not scored): Walsh S3 stage 3 (H/16, pilot) with C1-C3 should reproduce the diagnostic-patch
    result (f_t = 3: peak within 20 % of 222 L/s); Dig Tsho Westoby geometry runs and conserves mass. Large departures
    are investigated before the grid, not tuned.

## 4. cal-2 calibration grid

- Cases, split, objective, penalties, LOO and stability rule: as cal-1 (amendments 1, 1a, 2).
- Factor ranges, widened at the edges cal-1 hit (log10): f_kd [-2, 1.5], C_h [-1.5, 1], f_t [-1.5, 1.5], step 0.5.
- Runner: amendment-1 runner + memfix + Numba (C5); post-peak stop, CPU budget 8 h, checkpoints, 1 thread per worker.
- Early no-breach stop (new, pre-registered): for a case whose observation is a breach, a run that has not detected
  initiation by 3x the observed time to peak (or by t_end) stops as completed and is scored from its state at that
  time. Not applied to E1S3 (observation: no breach), which runs to t_end.

## 5. Predictions and success criteria (checked after the cal-2 fit, reported whatever the outcome)

| # | Prediction | cal-1 value | cal-2 criterion |
|---|---|---|---|
| P1 | Factors are stable | LOO ranges 31x, 31x, 3.2x | each factor's LOO max/min <= 3 |
| P2 | One f_kd fits the cohesive lab tests | per-case best 0.1 to 10 (100x) | per-case best f_kd of E1S1, E2S2, E1S3 within 10x |
| P3 | Headcut is identifiable | cohesive J nearly flat in C_h | for E2S2, J varies by >= 1.0 across the C_h range at the best f_kd |
| P4 | Transport factor near Walsh's | f_t = 10 (edge) | best f_t inside the range, between 1 and 6 |
| P5 | Non-cohesive widths improve | +21 % (Castlewood), +38 % (South Fork) | both within +/- 25 % |
| P6 | Goose Creek improves | Qp 3.1x low | Qp within a factor 2 |
| P7 | Better fit overall | J = 8.34 | J < 8.34 |

Whatever P1-P7 show, **cal-2 is frozen and stage 4 is run on it once**. No further engine change is made between the
cal-2 fit and stage 4; any further idea goes to a later version and is tested on new data.

## 6. Walsh (split-5 amendment, proposed)

Walsh S3 (and S1, S5 if their B* at T = 0 can be read from the thesis) is re-admitted as a **seen** validation-type
case: stage-3 start with the pilot channel (width = B* at T = 0), scored on Qp, rise time from Walsh's T = 0, and width.
It is reported separately from the blind stage-4 cases, because its observations shaped C1 and C2. The measured
repose angle of the Walsh sand (30.5 deg, Beddoe & Take 2016) replaces the assumed 33 deg in its case file.

## 7. Order of work

1. Freeze cal-1 (tag `cal-1`).
2. Review and commit this proposal (tag `cal2-proposal`); write the split-5 amendment for Walsh.
3. Implement C1-C5 behind options (engine V3.3); tests T1-T2; replays T3.
4. Write `cal2_config.json`; run the cal-2 grid; `fit.py`; check P1-P7; freeze cal-2 (tag `cal-2`).
5. Stage 4: blind validation on the 8 cases with cal-2.
6. Stage 5: Dig Tsho reconstruction ensemble.
