# Dam Breach Studio — breach_engine_2d_v3_2.py

Built from the uploaded `breach_engine_2d_v3.py` (1,482 lines; `_v3_1` was an identical copy). The file is now about 1,880 lines.
It is a rebuild of the missing items from the earlier chat's 64-item list, not a recovery of that sandbox file.

## Defaults and compatibility

| Setting | v3.0 (uploaded) | v3.2 default | Why |
|---|---|---|---|
| `cfl_interior_only` | True | **False** | v2 included ghost states in the CFL estimate |
| `detachment_rate_cap` | 1e-3 m/s | **None** | v2 had no ceiling; 0.02 m/s is an uncalibrated placeholder |
| `positivity_fix` | n/a | **True** | the one intended default change (S can no longer go negative) |

Legacy preset reproducing v3.0 exactly: `cfl_interior_only=True, detachment_rate_cap=1e-3, positivity_fix=False`.
On the demo run this gives 3,173 steps, peak 0.675972 and the same final-bed hash as the uploaded v3.0.
With the new defaults the demo takes 3,175 steps and peaks at 0.675984 m³/s.
The 3,175 steps matches the v2 golden step count from the earlier chat.
The v2 golden Qmax (0.523 m³/s) was not reproduced; I don't know which metric or run arguments produced it.

## Added (all switches default to old behaviour except positivity)

- **Defect and run control**
  - `positivity_fix`, `legacy_negative_S`.
  - Reservoir hold-level (`hold_reservoir_level`; the water added is tracked in `hold_added_m3` and in the balance).
  - Stop criteria: `max_wall_seconds` (checkpoint written, `wall_time_pause`), `stop_on_balance_error_m3`, and a NaN guard.
  - `run_status`, timing split, checkpoint version 6.
- **Diagnostics**
  - History now carries per-morph lateral, headcut, collapse, toe-scour and net transport volumes, plus `min_bank_FS`.
  - `diagnostics_summary()` and `write_diagnostics_csv()` expose sediment sources, Chen and detachment-cap activity, clip stats and balance errors.
- **Transport and material**
  - `threshold_D` (D50, geometric, D90) and `threshold_factor`.
  - Depth-scaled Ls and `active_layer_cap_m` (numerical only).
  - `detachment_load_saturation`, and `chen_apply_to_detachment`.
  - `material_class='mixed'` is reserved (warns, behaves as noncohesive).
  - `make_floor` with erodible depth and mask.
- **Lateral erosion and banks**
  - `lateral_model='force_balance'` is an Ikeda-type grain balance (lift/drag 0.85).
  - `bank_threshold_factor` and `bank_n_exp` are new bank parameters.
  - `LateralForceBalance` is renamed `LateralErosion` (old name kept as an alias).
  - `bank_fs_trigger` and `bank_fs_target` give an FS-based Culmann collapse. The defaults equal the old rule.
- **Headcut and hydrodynamics**
  - `headcut_retardation` and `headcut_max_rate`.
  - `downstream_boundary='wall'`.
- **Wave and lake**
  - `LakeGeometry` (configurable dimensions, depth profile, stage-volume curve, Green factor) and `impulse3d()` for cross-checks.
  - `LakeWaveBoundary(..., lake=...)`.
- **Initiation**
  - `InitiationMonitor`, `InitiationCriterion` and `initiation_success()`.
  - `perturb_crest`, `weak_spot` and `auto_seed_notch`.
  - These change the bed, so call them before building the engine.

## Status against the 64-item list

- **Built in the engine** (covered by `v3_2_feature_tests.py` or the uploaded regression, which I have not re-run on v3.2): 2, 6, 7, 12, 13, 15, 17, 20–24, 26, 29, 32–35, 37, 39–41, 44, 45 (FS trigger), 49–50, 52, 54–55. Item 8 is built but has an open balance question (see note).
- **Built, partial:**
  - 14: analytic travel-time and Green's-law routing only.
  - 27: numerical cap only.
  - 28: screening spread.
  - 38: toe-scour factor, default 0.
  - 42–43: multi-scarp, but mesh independence is unproven.
- **You run (not code):** 2b, 4, 5 (grid test), 25, 30, 31, 40 (comparison), 44 (runs), 51, 53. Item 25 needs a sweep runner, which is not delivered.
- **Not built:**
  - Item 9 (Numba).
  - Item 16 (run-up cross-check, a design rule only).
  - Item 18 (run-up test).
  - Item 36 (sub-cell wall retreat).
  - Item 43 (face-shear law).
  - Items 56–58 (UI inputs, GeoTIFF, variable mesh).
  - Numerical 1-D lake routing.
- **Deferred:** 11, 46–48 (Bishop/Spencer raise `NotImplementedError`).
- **Open or not delivered:** 3 (`engine.ts` repair script), 19 (side walls are reflective), 59–63 (documentation wording), 64 (validation plan).

Item 8 note: the MUSCL water-balance error is not resolved here. A depth clip to zero at dry fronts is a plausible cause.
It is untested.

## Verification state

- Syntax check passes. In a short sandbox run, the 16 checks in `v3_2_feature_tests.py` passed, and the demo run completed.
- `v3_engine_regression.py` was **not** run against v3.2. It is the uploaded file with the import changed to `breach_engine_2d_v3_2` and a `tmp` folder created.
- Run both suites with `run_v3_tests.ps1`.


## V3.2.1 (2026-10-31): reservoir positivity limit

* Bug: with a slide displacement, an emptied lake kept the debris-top stage (2.43 m at Dig Tsho)
  and kept feeding the prism. `Reservoir.update` clipped the deficit, so phantom water entered
  the prism: +1.54e6 m3 (c = 0) and +0.82e6 m3 (c = 5 kPa) in the 7,200 s outfall runs, equal to
  the inflow drawn after the stage froze. Peaks occur before emptying and are not affected;
  tails, total outflow volume and late-time erosion are.
* Fix: `Hydrodynamics.step(inflow_available=(V, Qin))` limits upstream-face inflow per step to
  storage plus external inflow; the blocked fraction acts as a wall (pressure only). Mass is exact.
* `Reservoir.legacy_unlimited_draw=True` restores the old behaviour. Not applied with hold_level.
* New diagnostics: `reservoir_clipped_m3`, `reservoir_empty`, `inflow_limit_events` (also checkpointed).
* New test: `tests/v3_2_1_reservoir_tests.py` (6 checks).


## V3.2.2 (2026-10-31): Step 0 of the calibration and validation plan

* `EngineConfig.erosion_shear = "total" | "grain"` (engine default "total" = V3.2.1). With "grain", erosion
  (Exner, lateral, initiation monitor) uses skin-friction shear tau' = rho g n'^2 U^2 / h^(1/3), capped at the
  total shear; n' = `grain_manning_n` or Strickler D50^(1/6)/21.1. Hydraulics keep the total roughness.
  Reason: with total shear a rougher bed eroded faster (S1 sweep), opposite to Westoby et al. (2015).
* Breach width now counts columns lowered by >= `breach_width_fraction` (0.5) of the maximum lowering;
  0 restores the old rule (any column lowered about 0.18 m), which reported 220 m for every Dig Tsho run.
* `InitiationCriterion.channelization_basis = "final"` (last record in the window); "best" restores the old
  maximum-at-any-time rule, which reported success for runs that ended full-width.
* Dig Tsho script: `--geometry westoby2015` (default; 40 m dam, 250 x 30 m crest, faces 1:15.2 / 1:3.1,
  7.3e6 m3 lake, lake bed ASSUMED 24 m) or `ts18` (all earlier runs; reproduces them bit for bit with
  `--erosion-shear total`). New options: --erosion-shear (default grain), --lake-bed, --lake-volume,
  --storage-exp, --floor.
* New test: `tests/v3_2_2_step0_tests.py` (11 checks).


## V3.3 (in progress, from 2026-11-07): cal-2 engine changes (validation/calibration/CAL2_PROPOSAL.md)

All options default to V3.2.2 behaviour; the four V3.2 suites must pass unchanged. New checks: `tests/v3_3_tests.py`.

* C2 `collapse_mode = "all_pairs"` (default `"unsupported"` = V3.2.2): every x / y neighbour pair is checked, dry,
  submerged or mixed, not only a dry cell above a wet toe. A pair fails when its Culmann factor of safety, computed
  with the critical angle for its state, is below `bank_fs_trigger` (for c = 0: steeper than that angle). Half the
  excess moves per pass, material lands on the lower bed (dry) or in its sediment store (wet); mass conserved.
  `collapse_phi_dry`, `collapse_phi_wet` [deg] (None = material phi) and `collapse_hswitch` [m] (None = h_dry).
  Checked: 13 unit checks (x and y steps, submerged steps, slopes below phi untouched, cohesive banks below and
  above the Culmann height, separate dry / wet angles, mass to 1e-16 m3); identical to the Walsh diagnostic patch
  (`diag_walsh.py --avalanche`) on WalshS3 H/8: same Qp, width and balances.
