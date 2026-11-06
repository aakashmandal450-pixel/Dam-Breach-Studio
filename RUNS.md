# Run index: Python 2D breach engine (v3.2)

Each run folder in `runs/` holds `summary.json`, `preregistered_criterion.json` (all CLI args), `history_thinned.csv`, `final_bed.npz` (z_b, z0, h, x, y) and `run.npz` (not in git).
Dig Tsho, 7,200 s, dx 2.5 m, dy 5 m, dam width 220 m, Hanson (TS erodibility) unless noted. Published peak about 1,600 m3/s (1,375-2,000); screening only.

| Run | Setup | Peak Q (m3/s) at t | Width lowered >=50% of max | Collapse m3 | Note |
|---|---|---|---|---|---|
| 2026-10-25_dt_wave300 | 300 s wave only | 2,604 at 102 s | full | | crest stripped about 1.45 m |
| 2026-10-25_dt_wave7200 | flat crest, transmissive | 6,841 at 2,677 s | full | | lake stalls at 6.77 m (boundary artifact) |
| 2026-10-25_dt_wu5 | Wu | 29.9 post-wave | none | | no breach |
| 2026-10-25_dt_n0.1_s1-3 | crest noise 0.1 m, seeds 1-3 | 5,706 / 5,354 / 5,882 | 220 m (full) | 112k-147k | |
| 2026-10-31_dt_dip_outfall | crest dip 0.5 m x 15 m, outfall, c = 0 | 3,569 at 1,987 s | 160 m | 139,928 | reservoir balance err +1.54e6 m3 |
| 2026-10-31_dt_dip_c5000_outfall | same, c = 5 kPa | 3,418 at 1,892 s | 90 m | 31,391 | reservoir balance err +0.82e6 m3 |
| 2026-10-31_dt_dip_c20000_outfall | same, c = 20 kPa, **t_end 1,800 s (default; --t-end omitted)** | 2,998 at 1,619 s | 60 m at 1,800 s | 12,598 | stopped early; rerun to 7,200 s |

Runs before V3.2.1 that drain the lake with a displacement (both dip_outfall runs) carry phantom inflow after the stage froze at 2.43 m; their peaks stand, their tails and outflow volumes do not.

### V3.2.1 (reservoir positivity limit), crest dip 0.5 m, outfall, 7,200 s

| Run | Cohesion | Peak Q (m3/s) at t | Width >=50% max lowering | Collapse m3 | Outflow m3 | Reservoir balance err |
|---|---|---|---|---|---|---|
| 2026-10-31_dt_dip_c0_outfall_v321 | 0 | 3,569 at 1,987 s | 160 m | 131,701 | 5.68e6 | +5e-08 |
| 2026-10-31_dt_dip_c5000_outfall_v321 | 5 kPa | 3,418 at 1,892 s | 90 m | 30,291 | 5.68e6 | +6e-08 |
| 2026-10-31_dt_dip_c20000_outfall_v321 | 20 kPa | 2,998 at 1,619 s | 70 m | 35,155 | 5.68e6 | -8e-08 |

### Sweep S1: erodibility and roughness SENSITIVITY (registered 2026-10-31, before running)

Purpose: sensitivity only. Not calibration (no value will be picked to fit Dig Tsho) and not validation.
Base: crest dip 0.5 m, outfall, cohesion 5 kPa, hanson_ts, V3.2.1, t_end 14,400 s (low kd may peak after 7,200 s).
Varied one at a time: kd-scale 1 / 0.5 / 0.25 / 0.1 (n = 0.035); Manning n 0.025 / 0.05 (kd-scale 1).
Reported: post-wave peak Q and time, breach width (columns >=50% of max lowering), max lowering, collapse volume, outflow volume, balances.
Run folders: runs/2026-10-31_S1_*

#### S1 results (5 kPa, 14,400 s; width = columns lowered >=50% of max)

| Run | kd scale | Manning n | Peak Q (m3/s) at t | Q > 100 m3/s from | Width | Collapse m3 | Lake empty at | Outflow m3 |
|---|---|---|---|---|---|---|---|---|
| S1_kd1_n0.035 | 1 | 0.035 | 3,418 at 1,892 s | 510 s | 90 m | 30,291 | 4,091 s | 5.72e6 |
| S1_kd0.5_n0.035 | 0.5 | 0.035 | 2,252 at 3,470 s | 1,616 s | 60 m | 15,723 | 6,486 s | 5.72e6 |
| S1_kd0.25_n0.035 | 0.25 | 0.035 | 1,484 at 6,499 s | 4,062 s | 50 m | 12,316 | 11,024 s | 5.72e6 |
| S1_kd0.1_n0.035 | 0.1 | 0.035 | 331 at 14,371 s (still rising, NOT a peak) | 12,992 s | 20 m | 0 | not empty (17.0 m) | 0.76e6 |
| S1_kd1_n0.025 | 1 | 0.025 | 2,402 at 3,079 s | 1,534 s | 60 m | 22,564 | 5,994 s | 5.72e6 |
| S1_kd1_n0.05 | 1 | 0.05 | 4,502 at 1,141 s | 241 s | 120 m | 24,731 | 3,028 s | 5.71e6 |

All balances <= 2e-7 m3, no speed clips. S1_kd1 reproduces the 7,200 s v321 run exactly up to 7,200 s.
Equifinality: kd 0.5 / n 0.035 and kd 1 / n 0.025 give near-identical peak, timing and width.

### V3.2.2 (Step 0) notes
From V3.2.2 the Dig Tsho script defaults to `--geometry westoby2015 --erosion-shear grain`. Every run above used
`ts18` with total shear; add `--geometry ts18 --erosion-shear total` to reproduce them. Widths in the summaries are
now >=50% of max lowering; the initiation check uses the final channelization index.

### Grid check and first Westoby-geometry runs (V3.2.2, 5 kPa, crest dip 0.5 m, outfall)

| Run | Setup | Peak Q (m3/s) at t | Width (>=50%) | Deepest lowering | Lake lowering | Collapse m3 | Wall time |
|---|---|---|---|---|---|---|---|
| dt_dip_c5000_outfall_v321 | ts18, total shear, dy 5 m | 3,418 at 1,892 s | 90 m | 18.0 m | 15.8 m | 30,291 | 4 min |
| ts18_c5000_dy2.5 | same, dy 2.5 m | 3,407 at 1,769 s | 88 m | 18.0 m | 15.8 m | 55,001 | 7.5 min |
| W15_c5000_n0.025 | westoby2015, grain shear, n 0.025 | 3,511 at 4,020 s | 90 m | 39.8 m | 14.4 m | 1,075,323 | 82 min |
| W15_c5000_n0.035 | same, n 0.035 (interrupted at 12,602 s, from checkpoint) | 3,656 at 4,396 s | - | - | 14.3 m | - | >2.5 h |
| W15_c5000_n0.035_v2 | rerun with drained-stop | 3,656 at 4,396 s | 90 m | 39.9 m | 14.3 m | 919,406 | 12 min |
| W15_c5000_n0.05 | n 0.05, drained-stop | 3,452 at 6,143 s | 90 m | 39.9 m | 14.3 m | 889,744 | 15 min |

Grid: halving dy changes peak by -0.3 %, time to peak by -6.5 %, width by -2 m; the split between collapse and transport is not converged (+82 % collapse).
Westoby geometry: the lake drains to the debris-top stage (25.8 m) by about 7,000 s; after that the runs only pass the 5 m3/s inflow. From V3.2.2+ the script stops 600 s after the lake is drained (--stop-drained-after).

Roughness with grain shear (Westoby geometry, 5 kPa): peak 3,511 / 3,656 / 3,452 m3/s for n 0.025 / 0.035 / 0.05 (within +/-3 %), time to peak 67 / 73 / 102 min.
The wave-window overtopping peak falls with n (4,570 / 2,848 / 1,411 m3/s). The rerun at n 0.035 reproduces the interrupted run's peak exactly.

## Calibration (stage 3) diagnostics and batch runs

### Setup diagnostics before the cal-1 grid (`runs/diag_setup.json`, `runs/diag_suspended.json`; default factors, not scored)

| Check | Model Qp (m3/s) / Tp (h) / B (m) | Observed Qp / Tp / B | Note |
|---|---|---|---|
| E1S1 default, 7,200 s | 1.73 / 2.0 / 2.9 | 6.5 / 0.67 / 6.9 | breaches, but slower and smaller; f_kd expected > 1 |
| Castlewood default, 3 h | 0 / - / 0 | 3,570 / - / 54.9 | no flow: notch lost on an even grid; fixed by the odd-cell, centred-notch rule and depth-scaled Ls |
| Castlewood 1 h, bed load only / + wu2000 suspended | 163 / 0.71 / 80.7 and 162 / 0.72 / 80.7 | 3,570 / - / 54.9 | after the notch fix; suspended load changes little at 1 h |
| WalshS3 default (H/8), f_t = 10, bed / + suspended | about 4e-4 / - / 0 | 0.24 / 73 s / - | no breach |
| WalshS3 H/24 | 0 | | no flow over the crest |

### Walsh (2019) S3 diagnostics (`python/calibration/diag_walsh.py`, `runs/diag_walsh/`, 2026-11-03; read-only, not scored)

| Run | Setup | Result |
|---|---|---|
| WalshS3_H8 | cal-1 setup, 12.5 cm cells, 1,800 s | about 0.26 L/s over the one-cell notch; flow falls below h_dry = 1 mm on the face and spreads as a sheet; notch lowered 0.2 mm; no breach |
| WalshS3_H24 | 4 cm cells, 120 s | notch walls (about 63 deg, c = 0) collapse in seconds; invert rises 31 mm above the lake; no flow |
| WalshS3_H24_c0.5kPa_hdry0.1mm | 0.5 kPa, h_dry 0.1 mm, 300 s | notch stays open, about 0.1 L/s reaches the toe; 32 mm scour hole at the crest edge, refilled by a fan downstream; headcut never triggers (slope 0.38-0.43 < 0.5); stalls after about 220 s |
| WalshS3_H8_pilot0.37m | stage-3 start, V pilot 0.37 x 0.12 m, 300 s | 2.5 L/s, constant; upstream lip does not erode (1 mm) and controls the flow |
| WalshS3_H16_pilot0.37m | same, 6 cm cells, 300 s | lip erodes about 15 cm; Q 13 L/s at 300 s and still rising; breach width 0.76 m; observed 0.24 m3/s at 73 s |
| WalshS3_H16_pilot0.37m_t900 | same, 900 s, cross-section snapshots every 30 s | peak 22 L/s at 450 s, then falls as the lake drains (30.3 -> 19.1 m3); breach width 0.82 m. The lip (breach control section) always sits on the un-eroded upstream face: the channel head creeps up the face at about 1.2 mm/s, so the inlet lowers only about 0.4 mm/s (0.880 -> 0.523 m in 900 s); Fr 0.4-0.7 over the lip; mid-crest flowing width 0.3-0.5 m |
| WalshS3_H16_pilot0.37m_t900_a_uphill1 | (a) slope-factor lower clip 0.3 -> 1.0 (no capacity reduction where flow runs uphill), diagnostic patch | peak 20 L/s at 520 s, width 0.82 m: no change, so the uphill slope factor is not the lip bottleneck |
| WalshS3_H16_pilot0.37m_t900_c_hc0.1 | (c) headcut_min_slope 0.5 -> 0.1 | peak 50 L/s at 320 s, width 1.08 m; lip lowers about 6x faster (0.880 -> 0.493 m by 270 s). At the peak the lip could pass about 125 L/s but 47 L/s flows: the narrow channel (flowing 0.44-0.63 m, top about 1.0 m) now controls. Outflow stops at 540 s when the closed flume end (downstream wall) fills to lake level |

Conclusion: Walsh stays excluded (EXCLUDED.md). The initiation stage is set by grid and threshold artefacts; from stage 3,
erosion and widening at the upstream breach lip are too weak. Candidate engine changes are listed in the handoff of 2026-11-03.
Sensitivity (2026-11-05, diagnostic overrides only, engine file unchanged): the headcut scarp threshold, not the uphill
slope factor, holds the lip back; with it lowered, channel widening becomes the limit (peak still about 5x low vs 0.24 m3/s).
The threshold compares a cell-to-cell drop with dx, so it is partly grid-dependent; a cal-2 change should address that.
Widening tests, both with (c): (d) near_bank_shear_factor 1.5 -> peak 57 L/s at 290 s, width 0.95 m;
(e) lateral_model force_balance -> 48 L/s at 290 s, width 1.01 m. Neither widens the channel: bank erosion strength and
the lateral law are not the limit. Cross-sections show why: dry cliffs up to 36 cm high at 70-80 deg and submerged banks
at about 54 deg (phi = 33 deg, c = 0) stand for minutes. BankStability._collapse_pairs collapses only a dry cell above a
wet toe ("unsupported" pairs); dry-dry and wet-wet pairs steeper than phi never fail, so the channel cannot widen by
bank failure. Next diagnostic: an angle-of-repose avalanche rule for all pairs.
(f) (c) + angle-of-repose collapse for all neighbour pairs (diagnostic patch of BankStability._collapse_pairs, phi = 33 deg
dry and wet, half the excess moved per pass, mass conserved; balances <= 4e-13 m3): peak 94 L/s at 230 s (160 s after Q
first reached 5 % of the peak), breach width 1.33 m; the channel widens to the full 2.09 m flume width by 240 s with banks
at about phi, and the rising limb becomes a sharp single rise. Peak still about 2.6x low (0.24 m3/s) and rise about 2x slow.
Literature (Barlow et al. 2024, XBeach on the same tests): avalanching off -> width growth stops, peak 0.05 vs 0.16 m3/s;
on -> 0.13 m3/s. Standard 2D practice (XBeach, BASEMENT, Wu 2D, Swartenbroekx) collapses all pairs above a critical
angle, with separate dry and submerged angles.

Follow-up, all with (c) + (f) and the same pilot (0.37 x 0.12 m), H/16 unless noted (2026-11-05):

| Run | Change | Peak Q | Rise (5 % -> peak) | Breach width |
|---|---|---|---|---|
| (f) | reference, f_t = 1, phi 33 deg | 94 L/s | 160 s | 1.33 m |
| (g1) | f_t = 3 | 222 L/s | 70 s | 1.58 m |
| (g2) | f_t = 10 | 353 L/s | 20 s | 2.09 m (flume walls) |
| (h1) | phi 30.5 deg (measured repose angle, Beddoe & Take 2016) | 100 L/s | 160 s | 1.58 m |
| (h2) | phi 30.5, dry pairs up to 45 deg, wet/dry switch depth 0.1 m | 87 L/s | 170 s | 1.27 m |
| (i) | H/24 (4 cm cells), f_t = 1 (rerun 2026-11-06; first attempt hit MemoryError at 840 s) | 118 L/s | 140 s | 1.43 m |
| (i2) | H/24, f_t = 3 | 252 L/s | 50 s | 1.68 m |
| Walsh observed | | 240 L/s | 73 s | about 1.6 m |

With the lip (c) and widening (f) processes in place, the remaining gap is the erosion rate: f_t = 3 matches peak, rise
and width together; f_t = 10 overshoots all three. The repose / dry-wet angles change the peak by a few %. H/16 -> H/24
raises the peak 26 % at f_t = 1 and 13 % at f_t = 3 and shortens the rise by about 20 s (vs about 9x from H/8 to H/16
before (c) and (f)). At H/24, f_t = 3 still matches Walsh: peak +5 %, width +5 %, rise 23 s faster. Balances <= 4e-13 m3. Walsh is excluded and its observations
are seen, so f_t ~ 3 is diagnostic, not a calibration. A XBeach-style submerged angle of 16.7 deg (wetslp 0.3) without a
rate limit flattens the submerged 30 deg upstream face within seconds and was not used.
Note: (i) and 11 E2S2 re-runs failed with MemoryError while the five diagnostics ran alongside the re-run (per-step
history held as Python dicts, about 2-4 GB per long run); see the calibration section.

### cal-1 grid (`python/calibration/run_grid.py`, `runs/calibration_grid/`)

- Pre-registered log grid, 204 runs over the 6 calibration cases; run 2026-11-02 to 2026-11-04 with 11 workers and a
  5,400 s wall-clock cap. 117 runs completed, 87 capped (E1S3 27, E2S2 40, Goose Creek 6, South Fork 10, Castlewood 4),
  0 errors. About 326 worker-hours; several multi-hour machine pauses (sleep) were counted against the wall cap.
- Protocol amendment 1 / 1a (`validation/calibration/PROTOCOL_AMENDMENT_1.md`, tags `protocol-amend-1`,
  `protocol-amend-1a`), written before any fit: capped runs are censored, not failed; post-peak stop; CPU-time budget;
  re-run of the capped set. Runner tag `amend1-runner`.
- Reproducibility check (2026-11-04): E1S1 and Castlewood runs repeated with the new runner match the stored Qp, Tp, B
  exactly (relative difference 0). Original capped files are kept in `runs/calibration_grid/_capped_v1/`.
- Amendment-1 re-run of the 87 runs started 2026-11-04 17:16, 5 workers, 1 thread each, checkpoints every 30 min CPU.
