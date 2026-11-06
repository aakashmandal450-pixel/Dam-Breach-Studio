# Calibration tooling changelog (`python/calibration/`)

The engine (`breach_engine_2d_v3_2.py`) has its own changelog in `python/V3_2_CHANGELOG.md`.

## amend1-runner (2026-11-04)

Implements `validation/calibration/PROTOCOL_AMENDMENT_1.md` (amendments 1 and 1a). The engine is unchanged, and
every new option defaults to off, so `cases.run()` without them behaves exactly as for the cal-1 grid.

* `cases.run()`:
  * `post_peak_stop` (with `post_peak_window_s`, `post_peak_frac`): stop as completed once the model has breached and,
    for the last 1,800 s of physical time, Q <= Q_in + 0.05 (Q_max - Q_in). Not applied to no-breach cases (E1S3).
  * `max_cpu_seconds`: CPU-time budget (`time.process_time`), so sleep and core sharing do not count.
    `max_wall_safety_seconds`: hang guard; such runs are recorded as errors.
  * `checkpoint_dir`, `checkpoint_every_cpu_s`: restart points at chunk boundaries. Engine state via
    `save_checkpoint` (history left out), history in numbered `.npz` parts, runner state (acceleration switch,
    CPU and wall used, post-peak tracking) in `runner.json`, written last. Resuming gives bit-identical results
    (tested with two kills, before and after the acceleration switch, on Linux and Windows).
  * New result fields: `censored`, `stop_cause` (`t_end`, `post_peak`, `reservoir_drained`, `cpu_budget`,
    `wall_cap`, `wall_safety`), `cpu_s` and `wall_s` (cumulative over restarts), `restarts`, `lake_volume_end_m3`,
    `runner` (options used). `capped` is kept, equal to `censored`.
* `run_grid.py`: `--rerun-capped` (selects capped or error runs from the old runner, moves them to `_capped_v1/`,
  turns on `--post-peak`, `--max-cpu 28800`, `--checkpoint-every 1800`), `--max-cpu`, `--wall-safety`, `--post-peak`,
  `--checkpoint-every`. One thread per worker (`OMP/MKL/OPENBLAS/NUMEXPR_NUM_THREADS = 1`). Checkpoint folders
  (`_ckpt/<run>/`) are deleted once a run's result is written.
* `fit.py`: runs classed as completed, censored or error; censored and error runs keep J = 25 (primary rule);
  sensitivity fit with every factor set removed if any included case is censored for it; `censoring_sensitive`
  flags and per-case run counts written to `cal-1_candidate.json`.
* New: `repro_check.py` (amendment s.5 reproducibility check), `smoke_amend1.py` (short tests incl. kill / resume).

Known, not changed: in `cases.run()` the physical-time mapping `phys()` maps history entries recorded before the
acceleration switch as if they were after it. No calibration case uses a Q-fraction Tp datum and peaks occur after
the switch, so cal-1 scores are not affected; the post-peak stop uses a corrected mapping (`phys_h`).

## memfix (2026-11-05)

`cases.run()` no longer keeps the engine's per-step history as Python dicts. After every chunk the runner moves the
entries into float64 columns of the three keys it uses (`time`, `Q_in_prism`, `Q_prism_outlet`) and empties
`eng.history`. The engine only appends to `history` and never reads it during a run, so results are unchanged.
Reason: 13 E2S2 re-runs and a Walsh diagnostic failed with MemoryError on 2026-11-05 (about 0.8 kB per step held in
memory; 2-4 GB per long lab run, more with 5 workers plus diagnostics).

* Tests (Linux): identical Qp, Tp, B, steps, stop time, lake volume, max lowering and all three balances vs the
  previous runner for E1S1 H/4 with post-peak stop, WalshS3 H/8 (reservoir discharge, Q-fraction Tp datum) and E1S1
  H/8 to 7,200 s; kill/resume twice with the new runner; and a checkpoint written by the previous runner resumed by
  the new one (the situation of the failed runs). Peak memory 162 -> 52 MB (145k steps) and 374 -> 76 MB (393k steps).
* Checkpoint history parts now hold only the three keys; parts written by the previous runner (all keys) are still read.
