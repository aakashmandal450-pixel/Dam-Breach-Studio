# Distributed 1-D engine — Phase B status, 2026-11-26

*Baseline record of the first phase B run, the user's decisions on it, and what changes next. Theory:
Part 6 draft 3.2 (`docs/theory/06_distributed_1d.md`, §6.0). Nothing below was tuned to make a test pass.*

## 1. Run conditions (baseline)

| item | value |
|---|---|
| code | branch `1D`, commit `5741ea6` (solver with reconstruction (6.14) as written; experimental variant run alongside) |
| command | `run_onedim_phaseB.ps1 -Quick` → `python -B -u -m onedim.verification.run_phase_b --quick` |
| machine | user's PC (legion-5), Windows, 12 workers; 99 cases; 1359 s |
| quick grids | B1 10⁴ steps (spec 10⁵); B2/B3 N = 400, 800, 1600 (spec up to 3200); B12b N = 10, 20, 40 crest cells (spec to 80); B12c spreads 5 and 20 cells (spec 5, 10, 20, 50) |
| full log | `docs/logs/onedim_phaseB_20261126_211146_quick.log` |

## 2. Result: 13 gates passed, 9 failed

| gate | result | measured |
|---|---|---|
| B1 lake at rest | PASS | max\|U\| = 8.9e-15 m/s, max\|Δη\| = 2.3e-14 m, water error 0 (10⁴ steps) |
| B2 Ritter: L1(h) decreasing | PASS | 6.05, 3.54, 2.09; observed order 0.76 |
| B2 Ritter: front within 1 % at finest | **FAIL** | −20.2 %, −16.2 %, −13.4 % (wet threshold 10⁻⁶ m) |
| B3 Stoker | PASS | finest: shock speed −0.40 %, h_m −0.020 %, u_m −0.140 % |
| B9 positivity | PASS | min A = 0.0207 m², no NaN; centre depth 0.0207 m against exact 0.0407 m (reported) |
| B13 passive scalar | PASS | bounded in all five sub-cases, solids exact; sub-case (e) not run (no sources in phase B) |
| B12b free overfall, rectangle | PASS | Q/Q_c − 1 = −7.2e-6, −6.5e-6, −6.0e-6; Fr_brink 1.0017–1.0023 |
| B12b free overfall, trapezoid | PASS | −8.6e-6, −8.1e-6, −7.6e-6; Fr_brink 1.0028–1.0033 |
| B12a (6.14) expansions vs relation, 1 % | **FAIL** | errors +298 % to +514 % |
| B12a (6.14) expansions vs Borda, 3 % | **FAIL** | up to +675 % |
| B12a (6.14) contractions vs relation, 1 % | **FAIL** | +315 %, +392 %, +414 %, +524 % |
| B12a (6.14) conduit → open, 1 % | **FAIL** | +2774 %, not steady |
| B12a (6.14) no net gain at any junction | PASS | all losses positive |
| B12c (6.14) no gain in any cell, 10⁻⁶ m | **FAIL** | max 2.0e-2 m |
| B12c (6.14) loss falls as the change is spread | PASS | e.g. 2→10: 0.0606 m (5 cells), 0.0207 m (20) — the 5-cell value is ~2 × the abrupt Borda head |
| B12a (6.14a, experimental) expansions vs relation | PASS | max 0.1 % |
| B12a (6.14a) expansions vs Borda | PASS | max 2.6 % |
| B12a (6.14a) contractions vs relation | **FAIL** | −76 %, −80 %, −83 %, −90 % |
| B12a (6.14a) conduit → open | **FAIL** | +248 %, not steady |
| B12a (6.14a) no net gain | PASS | |
| B12c (6.14a) no gain in any cell | **FAIL** | max 8.4e-3 m |
| B12c (6.14a) loss falls as spread | PASS | e.g. 2→10: 0.0156 m (5 cells), 0.0064 m (20) |

Both flow directions gave identical numbers in every junction case.

Checked in the container before the run, not in the quick run: B1 with (6.14a) at the full 10⁵ steps:
max\|U\| = 3.2e-14 m/s, max\|Δη\| = 1.2e-13 m (passes).

## 3. Decisions (user, 2026-11-26)

| item | decision |
|---|---|
| 6-19 width reconstruction | adopt (6.14a): discharge carried through a width change, velocity through a bed step; written into theory before continuing; no empirical loss coefficient; contraction and mixed-section cases stay as verification tests |
| 6-16 contraction loss | kept open. Borda–Carnot is an expansion benchmark only; contractions need a geometry- and regime-matched relation or data set. Candidates named by the user (not yet checked at source): HEC-RAS Hydraulic Reference Manual subcritical contraction coefficients (0.1 gradual, 0.6 abrupt, smaller for supercritical); Chaudhry, *Open-Channel Flow*, experimental coefficients ≈ 0.23 square-edged, 0.11 rounded, referenced to the narrow-section velocity; Wu and Molinas, short lateral contractions near choking, 186 experimental data sets. The current contraction result is unresolved, not judged wrong |
| 6-20 B2 front | accepted as a known first-order limitation at the tested resolution; the exact-front comparison and failed 1 % target stay in the report; a same-threshold front diagnostic is added and must fall with refinement; B2 does not block the baseline |
| 6-21 B12c criterion | strict per-cell test becomes a diagnostic; gate: local gains fall with refinement, no persistent or growing gain at the transition, net head change a loss, total transition loss converges with refinement |
| 6-18 brink fallback | B12b passed; not needed for the tested cases |
| conduit → open channel | unresolved; dedicated steady-state tests (B12d) |

## 4. Next

1. Code: (6.14a) as the solver default; (6.14) kept as `recon="velocity"` for comparison only.
2. Runner: B2 same-threshold diagnostic; B12c refinement series (fixed 2.5 m transition at
   Δs = 0.25, 0.125, 0.0625 m); B12d conduit outlets; B12a with (6.14) kept as a diagnostic.
3. Full run (`run_onedim_phaseB.ps1`, no `-Quick`), compared against this baseline.
4. Source check of the 6-16 candidates; then choose the contraction reference and geometry.
