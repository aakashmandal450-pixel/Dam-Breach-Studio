# split-6 proposal: a new blind hold-out set for V3.4 (DRAFT, 2026-11-09)

**Status:** draft for review. To be committed and tagged `split-6` **before** any V3.4 engine work, any new
calibration, and any reading of the new sources beyond what section 4 allows.

**Why.** Stage 4 spent the blind set: all 14 calibration and validation cases, plus Walsh, have now been seen. A
V3.4, or a probabilistic layer, judged on these cases would be judged on data that shaped it. New cases have to be
chosen and locked before the engine is touched.

## 1. Inventory of candidates

| Source | Cases | Scale / material | Seen? | Inputs available? | Fit for the engine |
|---|---|---|---|---|---|
| Taiwan field tests (Chao, Hung & Chen 2025; Zenodo 10.5281/zenodo.17828278, CC BY 4.0) | CP_1, CP_2, NCP_1, NCP_2 (+ any further tests in the archive) | field, non-cohesive (to be checked) | **unseen** (only the README field list was read: `readme_discharge.txt`, `readme_DEM.txt`) | DEM, inflow, reservoir storage in HDF5; material to be checked | frontal overtopping; likely fits |
| Li, Yang, Zhou, Zhang & Fan (2021), Front. Earth Sci. 9:660408 (open access) | large-scale field tests of non-cohesive landslide dams in a natural river | field, non-cohesive | unseen | to be checked (geometry, grain size, inflow) | frontal overtopping of a landslide dam; targets the field-scale peak bias |
| O'Donal (2023), MSc thesis, Univ. South Carolina (open access) | lab embankments 10-45 cm high, fine sand and sand-silt | lab, non-cohesive / silty | unseen | to be checked | frontal overtopping; varies dam height and silt content (scale, cohesion) |
| Walsh (2019) S2, S4, S6, W1-W5 | 8 | lab sand | **seen** (split-5 disclosure) | S partly; W needs beach geometry | seen checks only, never blind |
| DLBreach IMPACT lab #2, #4-#7, #10, #15, #16 | 8 | lab | **possibly seen** (Tables 6.2 / 6.4 were read in 2026-10 sessions) | reservoir curves not held (Morris et al. 2005) | not blind; excluded unless the curves are found |
| Lijiaju (DLBreach #18) | 1 | field cohesive | possibly seen | yes | excluded (only the peak observed: rule 2) |
| Rifai et al. 2019 / Schmitz et al. 2021-2023 (fluvial dikes) | 54+ | lab | unseen | yes (open data) | not usable: flow along the dike needs a channel-side boundary the engine lacks (G10) |

## 2. Proposed hold-out (split-6)

1. **Taiwan G9: all tests that pass the exclusions** (none was ever calibrated, so all are hold-out).
2. **Li et al. (2021) field tests** that pass the exclusions.
3. **O'Donal (2023) lab tests** that pass the exclusions, kept as their own group (lab scale; reported separately).

The exclusion rules are those of `SPLIT.md` (rules 1-4), applied to **inputs only**:
- piping;
- zoned dams;
- fewer than two observed quantities (counted from the list of reported variables, not their values);
- missing primary geometry or reservoir data;
- for non-cohesive cases, missing grain size.

No calibration case is drawn from the new data: split-6 is entirely hold-out. If a later V3.4 calibration needs more
cases, a separate split rule is written then.

## 3. Use

- One test, once, of whatever model is frozen next (V3.4 and / or the probabilistic layer), with the stage-4 limits
  and the same scoring code (`score_stage4.py`, generalised).
- The probabilistic layer is also judged on interval coverage: the share of observations inside the 50 % and 90 %
  predictive intervals.
- The empirical-regression baseline (Froehlich 2008, Xu & Zhang 2009) is scored on the same cases.

## 4. Blind handling of new sources

- **Machine-readable data (Taiwan HDF5).** A script written and committed before download separates inputs
  (geometry, DEM, inflow, storage curve, material) from outputs (`peak_Q`, `peak_Q_time`, `Qout_OR`, `endtime`,
  `WL`, final DEM, velocities). Inputs go to `cases_split6_inputs.csv`; outputs go to the locked file
  `observed_split6.csv`. The script prints only the input fields and the list of output field names. Nobody looks
  at plots such as `*_hyd.png` before scoring.
- **PDF sources (Li 2021, O'Donal 2023).** The project lead extracts the observed values into `observed_split6.csv`.
  The modeller reads only the sections that describe the set-up (geometry, material, inflow, reservoir). This is
  recorded per case.
- Disclosures are kept per case, as in `STAGE4_PROTOCOL.md` s.8.

## 5. Actions after approval

1. Commit this file (final) and tag `split-6`.
2. Write `split6_extract.py` (Taiwan) and commit it before the download.
3. Project lead: download the Taiwan archive (browser), Li et al. 2021 and O'Donal 2023 into
   `validation/sources/split6/`.
4. Apply the exclusions on the inputs, write `ASSIGNMENT_split6.md`, and lock the observations.
