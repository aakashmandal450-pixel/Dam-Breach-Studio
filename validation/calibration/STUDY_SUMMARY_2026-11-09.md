# Dam Breach Studio: calibration and blind validation of the 2-D breach engine (summary, 2026-11-09)

Pre-registered calibration (stage 3) and blind validation (stage 4) of the Python 2-D shallow-water breach engine
(`python/breach_engine_2d_v3_2.py`), 2026-10-31 to 2026-11-09. Details: `RUNS.md`, `validation/calibration/*.md`,
`python/calibration/CHANGELOG.md`, `python/V3_2_CHANGELOG.md`. Git tags mark each step (listed at the end).

## 1. Design

- **Cases.** Assembled from USDA-ARS lab embankments (Hanson et al. 2005), the DLBreach test set (Wu 2016), the IMPACT
  field tests (Norway) and the Walsh (2019) sand flume tests. Exclusion rules (piping, zoned dams, < 2 observations,
  missing geometry or reservoir data) and a split rule were fixed before any run (`SPLIT.md`, split-1 to split-5).
- **Calibration (6):** E1S1, E1S3 (no breach), E2S2 (USDA, jet-test kd); Goose Creek (cohesive field); Castlewood,
  South Fork (non-cohesive field).
- **Blind validation (8):** E1S2, E2S1, E2S3 (no breach); IMPACT 1-02, IMPACT 2C-02; Laurel Run; Poerua, Yigong.
  Observations kept in a separate file, opened once at scoring.
- **Seen validation:** Walsh S1, S3, S5 (split-5; their data shaped the engine changes).
- **Reconstruction only:** Dig Tsho 1985 (stage 5).
- **Calibrated factors (global, one value each):** f_kd (jet-test kd multiplier, measured-kd cases), C_h (headcut
  coefficient multiplier), f_t (non-cohesive transport capacity multiplier). Everything else fixed in writing first.
- **Objective J:** sum over cases of squared log errors of Qp and Tp plus squared relative width error; no-breach
  penalty. Leave-one-out (LOO) refits; a factor is stable if its LOO max/min <= 3.
- **Acceptance limits (stage 4):** peak within x1.5, time to peak within x2, width within +/-50 %, lake drawdown
  within +/-25 %, each met in >= 2/3 of the cases where it applies; mass balance < 1e-6 of the volume released.

## 2. cal-1: engine V3.2.2 (2026-11-01 to 2026-11-07)

- Grid: 204 runs (log-spaced factors). Runner problems were fixed under written amendments (protocol amendments 1,
  1a, 2): post-peak stop, CPU-time budget instead of wall clock, checkpoints, a memory fix. Final: 204 / 204 complete.
- **Fit: J = 8.34 at f_kd 3.16, C_h 0.316, f_t 10 (top of range). All three factors unstable** (LOO ranges 31x,
  31x, 3.2x).
- Diagnosis:
  - E1S1 and E2S2 need f_kd 100x apart.
  - The headcut was nearly inactive (J flat in C_h).
  - Non-cohesive breaches came out too wide (Castlewood +21 %, South Fork +38 %), through a lateral-erosion law
    with arbitrary defaults (tau_c 1 Pa).
  - Goose Creek's peak was 3x low.
- Walsh S3 diagnostics: the engine could not lower the breach lip (headcut threshold) and could not widen the
  channel (banks collapsed only as "dry cell over wet toe"). With both added as patches, Walsh was reproduced at
  f_t about 3.
- Decision (amendment 2, "option A"): stage 4 is not spent on cal-1; fix the engine first, under a pre-registered
  proposal.

## 3. Engine V3.3 and cal-2 (2026-11-07 to 2026-11-08)

- Pre-registered proposal (`CAL2_PROPOSAL.md`: changes C1-C5, tests T1-T3, predictions P1-P7). All changes are
  options; the defaults reproduce V3.2.2 exactly.
  - C1: scarp-based headcut (runs of steep drops, total height, 4 directions, whole-face retreat at R = C (q H)^1/3).
  - C2: collapse of every neighbour pair steeper than the friction angle (dry and submerged).
  - C3: no lateral excess-shear law for non-cohesive soil.
  - C4: lateral erosion of banks facing x and y.
  - C5: Numba kernels; morphology bit-identical or round-off equal to NumPy, 1.1-2x faster.
- The T3 replays found that the pre-registered scarp threshold (0.1) made every dam face a headcut (Dig Tsho
  14,000 m3/s). Walsh no longer needed it once C2 existed. `CAL2_AMENDMENT_1`: threshold 0.5, adopted before the
  grid.
- Grid: 234 runs, 10.4 h, all complete. **Fit: J = 6.47 at f_kd 1, C_h 10 (top of range), f_t 3.16.**
- **Predictions:**

  | # | Prediction | Result |
  |---|---|---|
  | P1 | Stable factors | Fail (31.6x / 10x / 3.2x) |
  | P2 | One f_kd for the lab tests | Fail (best 10 / 0.1 / 1) |
  | P3 | Headcut identifiable | Fail (E2S2 J range 0.25-0.65) |
  | P4 | f_t inside 1-6 | Pass (3.16) |
  | P5 | Non-cohesive widths within 25 % | Pass (-4 %, +4 %) |
  | P6 | Goose Creek Qp within 2x | Fail (2.7x low) |
  | P7 | J below cal-1 | Pass (6.47 < 8.34) |

- Frozen as `cal-2.json` with the P1-P7 record.

## 4. Stage 4: blind validation of frozen cal-2 (2026-11-08 to 2026-11-09)

Protocol `STAGE4_PROTOCOL.md`, tagged before any run:
- case files built from inputs only, with disclosures of everything seen;
- a result manifest (SHA-256) written before scoring;
- the scorer refuses to run if any result changed.

31 runs: 8 cases x (F_all, LOO_1, LOO_2), an inflow sensitivity run, and Walsh at H/16 and H/24.

| Case | Qp ratio (model/obs) | Tp ratio | Width error | Pass |
|---|---|---|---|---|
| E1S2 | 2.23 | - | -61 % | no |
| E2S1 | 0.74 | - | -7 % | **yes** |
| E2S3 | no breach (correct) | - | -100 % | no (width) |
| IMPACT 1-02 | 1.13 | 0.97 | - | **yes** |
| IMPACT 2C-02 | 0.42 | 2.33 | -29 % | no |
| Laurel Run | 0.52 | - | -22 % | no |
| Poerua | 0.018 (no breach) | - | -100 % | no |
| Yigong | 0.13 | 3.08 | +45 % | no |

- **2 of 8 cases pass.**
- Limits: peak 2/7, time to peak 1/3, width 4/7 (all fail); no breach 1/1 and balance 8/8 (pass); drawdown n/a.
- J over the 8 blind cases: 27.2 (6.47 on the calibration cases).
- Walsh (seen): peak x1.4-2.0 at H/16 and x2.0-3.2 at H/24; not grid-converged.

## 5. What the results mean

1. **Peaks are too low at field scale.** Laurel Run x0.52, 2C-02 x0.42, Yigong x0.13, Poerua no breach; the
   calibration field cases were also low (Castlewood x0.56, South Fork x0.65, Goose Creek x0.37). Widths fitted, so
   the calibration did not show it. The engine erodes too slowly at high flow and large scale.
2. **The factors do not transfer across scale.** Yigong: f_t 3.16 -> 10 raises the peak 6x (x0.13 -> x0.75).
   Walsh (small sand dams) is over-predicted with C_h = 10, which the field cases pushed up.
3. **Cohesive lab tests:** one f_kd cannot fit tests of the same soil series (E1S1 vs E2S2, 100x). The likely cause
   is initiation and headcut formation under low flow, not the erosion law. The LOO envelope is as wide as the
   error but brackets the observation only once (E1S2), so the factor spread understates the real uncertainty.
4. **Poerua is a setup artefact.** At H/6 (13.3 m cells) the 3 m pilot notch becomes a 13 m cell, and the
   cell-averaged crest sits 0.2 m below the nominal crest. The lake spills as a thin sheet over the whole crest and
   then drains through a weak notch flow that never exceeds the critical shear.
5. **Standing of the model.** As calibrated, the engine is a screening tool with wide uncertainty, not a validated
   predictor at these limits. It is reasonable for small and medium inflow-driven cases (IMPACT 1-02, E2S1) and
   biased low for large field breaches. Outputs should carry the factor-range band and a "screening" label.
6. **Method.** The pre-registered chain (frozen rules, amendments before runs, manifest before scoring) shows that
   these failures are real and not tuned away. That is the main methodological result.

## 6. Next steps (2026-11-09)

1. **Reserve new blind data (split-6)** before any engine work: all 14 current cases are now seen
   (`SPLIT6_PROPOSAL.md`, draft).
2. **Stage 5:** Dig Tsho with frozen cal-2, an ensemble over F_all / LOO_1 / LOO_2, reported as screening with the
   known low-peak bias.
3. **V3.4**, each change pre-registered and tested once on the split-6 hold-out:
   - the field-scale peak bias (transport at high flow, breach-control section, lake coupling);
   - the grid and notch rule at prototype scale (Poerua);
   - scale-dependent transport and headcut factors;
   - cohesive initiation under low flow (including the hypothesis "SM soils with a transport law").
4. **Probabilistic layer** (under discussion):
   - an empirical-regression baseline (Froehlich, Xu & Zhang) on the same cases;
   - Gaussian-process emulators from the grid runs;
   - hierarchical Bayesian calibration with a scale-dependent discrepancy term, checked by interval coverage on
     split-6.

**Tags:** split-2 ... split-5, protocol-amend-1 / 1a / 2, cal-1, cal2-proposal, cal2-amend-1, cal-2, stage4-protocol,
stage4-protocol-2c, stage4-runs, stage4-results.
