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

## 5. Full run after decisions 6-19 to 6-21 (2026-11-27)

Commit `944c33d`, `run_onedim_phaseB.ps1` (full grids), 119 cases, 12 workers, 3997 s. Log:
`docs/logs/onedim_phaseB_20261126_221044_full.log`. **27 pass, 3 fail, 1 known limitation.**

| gate | result | measured |
|---|---|---|
| B1 lake at rest (10⁵ steps, (6.14a)) | PASS | max\|U\| = 4.0e-14 m/s, max\|Δη\| = 2.3e-13 m, water error 1.8e-16 |
| B2 L1(h) decreasing | PASS | observed order 0.77 |
| B2 exact front within 1 % | KNOWN (6-20) | −20.2, −16.2, −13.4, −10.6 % (N = 400…3200) |
| B2 same-threshold front (h_th = 1 mm) falls | PASS | −19.4, −15.1, −11.1, −7.7 % |
| B3 Stoker | PASS | shock −0.26 %, h_m −0.010 %, u_m −0.072 % |
| B9, B13 | PASS | as the baseline |
| B12b rectangle / trapezoid | PASS | errors to −5.6e-6 / −7.3e-6 at N = 80, decreasing |
| B12a expansions vs relation / Borda | PASS | 0.1 % / 2.6 % |
| B12a contractions vs relation | FAIL (6-16 open) | −76, −80, −83, −90 % |
| B12a conduit → open | FAIL | +248 %, not steady |
| B12a no net gain | PASS | |
| B12c refinement, four items × four cases | PASS (16/16) | e.g. 2→10: max local gain 4.3e-3, 2.4e-3, 9.6e-4 m; loss 0.0104, 0.0064, 0.0036 m |
| B12d steady state | FAIL | none of the four cases steady after 10⁴ s; submerged loss 0.2375 m vs Borda 0.0692 m (+243 %); free outlet: outlet flux constant to 9e-9 but stage residual 2.8e-6 |

Observations:

- B12c: over a fixed 2.5 m transition, local gains and the total loss both fall roughly in proportion
  to Δs, i.e. the loss converges towards zero, as expected for a frictionless gradual transition
  computed at first order. The finest 2 → 10 case did not meet the steady tolerance (reported
  conv = False) but was included.
- B12d diagnosis (container, submerged outlet, 200 s): the stage in the last two conduit cells next
  to the outlet oscillates between 0.53 and 1.02 m while the open channel is steady to 10⁻⁴ m and the
  conduit 30 m upstream is steady to about 1 cm. The upstream conduit stage settles about 0.1 m above
  the relation value; that extra head is the excess loss. The oscillation sits at the interface
  between the slot (width g·b·a/a_s² ≈ 6e-6 m) and the 1 m open section. Cause not yet established;
  candidates: the slot celerity a_s (C6 sensitivity not yet run), the treatment of the crown level
  on the interface section, and the absence of any damping in a frictionless pressurised reach.

## 6. B12d conduit-outlet diagnosis (2026-11-27)

Plan by the user (D1 a_s, D2 2a_s, D3 4a_s frictionless; D4 a_s with Manning n = 0.012; geometry,
IC, BC, CFL and the steady criterion unchanged). Commit `3b4e20e`, user's PC, t_max = 10⁴ s. Log:
`docs/logs/onedim_b12d_diagnosis_20261127_104701.log`. 14 of 16 runs completed; both D3 submerged
runs were terminated by the operating system after ~5.5 h (BrokenProcessPool; no Python error).
Both directions gave identical numbers in every completed run.

Last conduit cell, last 20 % of each run:

| case | steady | stage oscillation | period | slot depth (crown pressure head) | upstream stage | E_up − E_dn |
|---|---|---|---|---|---|---|
| D1 submerged | no | 0.742 m, flat over all 20 windows of 500 s | 0.031 s | 0.30 – 1.04 m | 0.768 m (relation 0.600) | 0.237 m (Borda 0.069) |
| D2 submerged | no | 0.807 m, flat | 0.014 s | 0.28 – 1.10 m | 0.738 m, range 0.79 m | 0.207 m |
| D3 submerged | — | not completed | | | | |
| D4 submerged | no | 0.730 m, flat | 0.031 s | 0.30 – 1.03 m | 0.916 m | 0.385 m, of which friction 0.151–0.154, junction 0.231–0.234 |
| D1 free | no (decaying) | 4.6e-5 m; window ranges fall from 7.6e-2 to 9.7e-6 | — | −0.015 m (not pressurised) | 0.185 m | (includes the 0.5 m drop) |
| D2 free | no (decaying) | 4.6e-5 m, same decay | — | −0.015 m | 0.185 m | |
| D3 free | **yes, at 2879 s** | 3.7e-7 m | — | −0.016 m | 0.184 m | |
| D4 free | no | 3.7e-5 m, **flat** from 500 s on | 0.178 s | −0.014 to −0.002 m (touches the crown) | 0.345 m | |

Water balance < 3.2e-11 in every run.

Reading against the user's criteria:

- Submerged (pressurised) outlet: the oscillation persists, undamped, at a_s and 2a_s, with an
  amplitude (0.73–0.81 m) almost independent of a_s and of friction. Its period scales with 1/a_s
  (0.031 → 0.014 s), i.e. a few slot-wave crossings of one cell (Δs/a_s = 0.005 s at D1): a grid-scale
  mode. Friction does not reduce it (D4 0.730 m vs D1 0.742 m). By the user's rule this points to the
  interface flux and section treatment, not to the slot stiffness.
- Free outlet: the conduit runs just below the crown (−1.5 cm) and the transient decays, slowly in
  D1/D2 and to steady in D3. Not a sustained oscillation. With friction (D4) the free surface rises
  to within 2 mm of the crown and a small (3.7e-5 m) flat oscillation persists — the crown is
  touched intermittently.

Isolation runs in the container (submerged, D1, 200 s, oscillation in the last conduit cell over the
last 50 s; reference 0.742 m, loss 0.238 m):

| change (one at a time) | oscillation | upstream stage | loss |
|---|---|---|---|
| open 0.2 m rectangle → 1 m (no crown) | 7.6e-3 m | 0.608 | 0.0068 |
| conduit with a 2 m crown (never pressurised) | 7.6e-3 m | 0.608 | 0.0068 |
| conduit → larger conduit 1 × 1 m | 0.745 m | 0.766 | 0.235 |
| Δs/2 | 0.696 m | 0.768 | 0.237 |
| CFL 0.45 | 0.130 m | 0.628 | 0.098 |
| face rule "own" (draft 1) | 0.105 m | 0.218 | −0.313 (energy gain) |
| reconstruction (6.14) instead of (6.14a) | 0.016 m | 2.527 | 1.99 |

What this establishes: the mode appears only when the upstream cell is pressurised (in the slot);
the open downstream section is not needed for it; it does not shrink with Δs; it shrinks strongly
with the time step; it is sensitive to the reconstruction and to the face rule. What it does not yet
establish: the mechanism. Working hypothesis (unproven): in the slot the reconstructed areas on the
two sides of the interface are nearly equal (the slot width is ~6e-6 m) while the stages differ by
decimetres, so the HLL mass flux hardly responds to the pressure difference across the interface —
a low-Mach (flow speed ≪ a_s) decoupling of pressure and mass flux, confined to the interface where
(6.14a) and (6.16b) meet the slot.

## 7. Time-step (CFL) series, B12d submerged (2026-11-27)

D1 configuration (a_s = 50 m/s, frictionless), CFL varied only; t_max = 1000 s; user's PC, commit
`fc83feb`. Log: `docs/logs/onedim_b12d_diagnosis_20261127_210729_cfl.log`. Both directions identical.

| run | CFL | Δt | oscillation, last conduit cell | period | upstream stage | E_up − E_dn |
|---|---|---|---|---|---|---|
| T1 | 0.9 | 4.38e-3 s | 0.736 m | 0.031 s | 0.7676 m | 0.2368 m |
| T2 | 0.45 | 2.19e-3 s | 0.130 m | 0.020 s | 0.6284 m | 0.0976 m |
| T3 | 0.225 | 1.10e-3 s | 0.027 m | 0.012 s | 0.6005 m | 0.0698 m |
| T4 | 0.1125 | 5.48e-4 s | 1.3e-8 m (decayed from 5.4e-4 m in the first 500 s) | — | 0.6000 m | 0.0692 m |

Reference: relation 0.0692 m and upstream stage 0.6000 m; Borda 0.0693 m.

Finding: at CFL 0.1125 the oscillation is gone and the conduit outlet reproduces the junction
relation and Borda to four decimals. The interface reconstruction (6.14a) and loading (6.16b) give the
right steady state; the explicit step at CFL 0.9 (with (6.21) as written) is not stable at a
pressurised outlet. The stability limit lies between CFL 0.1125 and 0.225 for this case. Mechanism
checks M1–M4 (`run_b12d_mechanism.ps1`) follow. The B12d steady criterion (10⁻¹¹ over 500 steps)
was not met by T4 within 1000 s, although its residual oscillation is 10⁻⁸ m.

## 8. Mechanism checks M1–M4 (2026-11-27)

Commit `68da86d`, user's PC, 364 s. Log: `docs/logs/onedim_b12d_mechanism_20261127_221209.log`.

- **M1 interface flux response** (change per metre of stage difference across one interface):
  free surface (0.2 m open, 0.5 m deep): mass flux 0.21, momentum flux 0.57; pressurised
  conduit | conduit: mass flux 0.0039 (54 × weaker), momentum flux 0.20; conduit | open 1 m outlet:
  identical to conduit | conduit (the outlet interface is the conduit section). The mass flux hardly
  sees a stage difference in the slot, as hypothesised; but the outlet interface itself is no different
  from an interior conduit interface.
- **M2 no section change** (120 s, CFL 0.9, oscillation in cell 79): uniform pressurised conduit
  2.4e-3 m (residual start-up pressure wave between two reflecting boundaries, frictionless);
  pressurised 0.2 → pressurised 0.4 × 0.4 conduit 8.1e-2 m; pressurised 0.2 → 1 × 1 m conduit with a free
  surface 0.74 m (= the outlet case). The full instability needs a pressurised cell next to a
  free-surface cell; the open channel and the crown geometry are not needed.
- **M3 term trace** (last conduit cell): the step-face contribution W is exactly zero in that cell (its
  section equals the interface section), so (6.16b) is not involved. At CFL 0.9 the cell runs a
  7-step sawtooth: stage jumps 0.51 → 1.22 m in two steps and relaxes over five, driven by mass-flux
  imbalances of ~3e-3 m³/s, which in the slot (T_s ≈ 6e-6 m) move the stage by decimetres per step.
  At CFL 0.1125 every term is steady (residual 1e-11).
- **M4 contractions** (open channels): losses identical to five figures at CFL 0.9 and 0.1125
  (−76.1, −80.4, −83.4, −89.6 % against the relation). The contraction result is not a time-step
  effect; 6-16 is unaffected.

Conclusion so far: the outlet failure is a stability limit of the explicit update at a cell where
a slot (tiny storage width) meets a free-surface neighbour (large storage width); the standard CFL
(6.21) does not capture it. Not yet established: the limit itself and a rule for it.
