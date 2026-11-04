# Calibration protocol — amendment 1 (`protocol-amend-1`)

**Status:** committed 2026-11-04 as `protocol-amend-1`; §6 wording corrected the same day as `protocol-amend-1a`.
Both were written while the cal-1 grid was still running, before `fit.py` had been run or any score looked at.

**Amends:** `CALIBRATION_PROTOCOL.md` (2026-11-01). The objective, the factor grid, the calibration/validation
split, the engine version (V3.2.2) and every frozen model choice in `cal1_config.json` are **unchanged**.
This amendment only changes how runs are stopped, how runs cut short are treated, and how the batch is executed.

---

## 1. Why this amendment is needed

148 of 204 grid runs were inspected for run-time behaviour only (status, `capped`, `breached`, `t_end_phys_s`,
`t_switch_phys_s`, `steps`, `wall_s`). Findings:

1. **The wall-clock cap is not a reliable stop.** `--max-wall 5400` is measured with `time.perf_counter()`,
   which keeps counting while Windows is asleep or the process is starved. Runs that were running at the same
   time overshot the cap together (e.g. five E1S3 runs all ended at 29,63x s; seven E2S2 runs at 9,08x–9,107 s).
   Several E1S3 runs with different f_kd have **identical** step counts and physical end times but wall times
   of 11,454 s vs 29,630 s, i.e. the extra time was machine stalls, not computation. Clean throughput is
   about 2–3 ms per step; stalled runs show 9–117 ms per step.
2. **Whether a run was "capped" therefore depends on machine load, not on the physics.** 58 runs were capped
   (E1S3 27, E2S2 27 so far, Castlewood 4).
3. **`fit.py` treats every capped run as a failure (`PENALTY_MISSING = 25`)**, overriding the protocol's own
   no-breach rule for E1S3. A capped run is not a failed run: it is **censored** — its outcome after the cap
   is unknown. A fixed 25 for censored runs biases the fit toward fast-eroding factor sets.
4. **Runs continue long after the breach is over.** Lab cases have steady inflow and t_end = 72,000 s (E1S3)
   and 100,000 s (E2S2) with dt ≈ 0.01 s; runs that have already peaked keep simulating a drained lake for
   many hours. This costs time but does not change Qp or Tp.

**What was and was not seen.** Seen: the run-time fields above and the `_live/` heartbeat values (Q, lake level,
max lowering) of runs in progress. Not seen: any score `J`, any comparison of model Qp/Tp/B with observations,
any output of `fit.py`. No validation-tier observation has been opened.

---

## 2. Definitions

- **Breached** — unchanged: crest lowered below the notch invert by more than 50 % of the notch depth.
- **Peak** — the maximum of the scored discharge series (`Q_prism_outlet`, or `Q_in_prism` where the case says so).
- **Completed run** — reached the case `t_end`, or stopped by the post-peak rule (§3), or by
  `stop_reason = "reservoir_drained"`.
- **Censored run** — stopped by the compute budget (§4) before it completed.
- **Error run** — raised an exception or produced a non-finite result.

---

## 3. Post-peak stop rule (new)

Applies to cases whose observation is a breach (all calibration cases except E1S3). Checked after every chunk.

A run is stopped as **completed** when all of the following hold:

1. the model has breached;
2. the physical time is at least 1,800 s past the peak;
3. throughout the last 1,800 s of physical time,
   `Q ≤ Q_in + 0.05 · (Q_max − Q_in)`,
   where `Q_in` is the case's steady inflow (0 for field cases) and `Q_max` is the peak so far.

Rationale: Qp and Tp are fixed once the peak has passed and the discharge has fallen back to within 5 % of the
inflow-to-peak range for 30 min. B is taken at the stop time; widening after this point is expected to be small.
The B at the stop time and the remaining lake volume are recorded so this can be checked.

**E1S3 (observation = no breach)** is never stopped early. It must reach `t_end` = 72,000 s for the no-breach
term to be scored, because the observation is "no breach within the test duration".

---

## 4. Compute budget (replaces the wall-clock cap)

- The cap is measured in **CPU time of the run's own process** (`time.process_time()`), so sleep and waiting
  for a core do not count.
- **CPU budget: 8 h per run.** (Clean cost at 2.5 ms/step: about 1.6 h for 2.3 M steps; a full E2S2 run to
  100,000 s at dt ≈ 0.01 s is about 10 M steps ≈ 7 h. The post-peak rule should make that rare.)
- A wall-clock safety net of 24 h remains, only to catch hangs. A run stopped by it is an **error run**.
- `capped` in the result file is replaced by `censored` (bool) and `stop_cause` ∈
  {`t_end`, `post_peak`, `reservoir_drained`, `cpu_budget`, `wall_safety`}.

---

## 5. Re-run set

- Every run in the cal-1 grid that is `capped = true` or an error run is **re-run** under §3–§4, with the same
  engine, case file, factors and `cal1_config.json`.
- Runs that completed under the old settings are **kept as they are**. The post-peak rule cannot change their
  Qp/Tp, and their B is their B at `t_end` (the original rule).
- The original capped result files are moved, not deleted, to `runs/calibration_grid/_capped_v1/`.

**Reproducibility check (before the re-run).** Re-run two completed uncapped runs under the new runner — one
E1S1 run and one Castlewood run, chosen as the first in `run_grid.py --list` order for each case — with the
post-peak rule **disabled**. Qp, Tp and B must match the stored results to a relative difference of 1e-6. If
they do not, stop and investigate before re-running anything.

---

## 6. Scoring runs that are still censored after the re-run

Primary rule (used for cal-1):
- A censored run keeps `J = 25` (`PENALTY_MISSING`, as now).

Pre-registered sensitivity check (reported alongside, not used for the freeze unless stated below):
- Refit with every factor set **removed from the search** if any case included in the fit is censored for it.
  (Amendment 1a, 2026-11-04: the original wording, "excluded from that case's sum", would lower J for exactly the
  censored factor sets and bias the fit toward them, so the whole factor set is removed instead. Changed before any
  fit or score was looked at.)
- If the primary fit and the sensitivity fit choose a different grid value for any factor, that factor is
  recorded in `cal-1.json` as **censoring-sensitive**. It is still frozen at the primary value, but it is treated
  like an "unstable" factor in the protocol: the Dig Tsho ensemble samples the range spanned by both fits and
  by the LOO fits.

Report, per case: number of completed, censored and error runs, before and after the re-run.

---

## 7. Execution settings (do not affect results)

- `OMP_NUM_THREADS = MKL_NUM_THREADS = OPENBLAS_NUM_THREADS = 1` in every worker.
- Workers: number of physical cores minus 1 (7 on the Legion 5 if it has 8 physical cores; check first).
- Windows sleep disabled for the duration of the batch (Power → Sleep: Never).
- `run_grid.py` records per-run `cpu_s`, `wall_s`, `steps` and `stop_cause`.

---

## 8. Code changes this amendment requires

All in `python/calibration/`; the engine is not touched.

- `cases.py` `run()`: add `post_peak_stop` (default **off**, so existing behaviour is unchanged), `max_cpu_seconds`,
  `max_wall_safety_seconds`; record `censored`, `stop_cause`, `cpu_s`, `B_at_stop`, remaining lake volume.
- `run_grid.py`: `--rerun-capped` (selects §5's set and archives the old files), `--max-cpu`, thread environment
  variables set before the pool starts.
- `fit.py`: read `censored` (fall back to `capped` for old files); implement the §6 sensitivity fit and the
  per-case completed/censored/error counts; write the `censoring_sensitive` flag.
- `score()` is unchanged.

These changes are written and tested on a copy while the grid runs, and swapped in only after it finishes.

---

## 9. Order of work

1. Commit this file and tag `protocol-amend-1` (before the grid finishes).
2. Let the cal-1 grid finish under the old settings.
3. Swap in the §8 code; run the §5 reproducibility check.
4. Re-run the §5 set.
5. Run `fit.py`; review fit, LOO, stability and censoring sensitivity; freeze `cal-1`.
