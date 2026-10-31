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
| W15_c5000_n0.05 | not run | | | | | | |

Grid: halving dy changes peak by -0.3 %, time to peak by -6.5 %, width by -2 m; the split between collapse and transport is not converged (+82 % collapse).
Westoby geometry: the lake drains to the debris-top stage (25.8 m) by about 7,000 s; after that the runs only pass the 5 m3/s inflow. From V3.2.2+ the script stops 600 s after the lake is drained (--stop-drained-after).
