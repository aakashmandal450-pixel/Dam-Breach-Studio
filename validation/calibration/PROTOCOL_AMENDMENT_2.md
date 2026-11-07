# Calibration protocol — amendment 2 (`protocol-amend-2`)

**Written:** 2026-11-07, after the cal-1 grid finished (204 / 204 runs) and **before `fit.py` was run**. No score,
fit, LOO result or comparison of model output with observations for the grid had been looked at.
Commit and tag `protocol-amend-2` before running `fit.py`.

**Amends:** `CALIBRATION_PROTOCOL.md` with amendment 1 / 1a. Objective, factor grid, split, engine (V3.2.2) and
`cal1_config.json` are unchanged.

## 1. Order of stages: blind validation waits for cal-2 (decision "option A")

The Walsh (2019) S3 diagnostics (`RUNS.md`, 2026-11-03 to 2026-11-06; Walsh is excluded and was never scored) showed
that the V3.2.2 engine lacks two processes for non-cohesive breaching: headward retreat of the breach lip
(headcut slope threshold) and slope collapse of dry and submerged banks steeper than the repose angle. With both
added as diagnostic patches and f_t = 3, the model matched Walsh's peak, rise and width within about 5-30 %.

Decision:
- cal-1 is fitted, reviewed and frozen as planned, as the documented **baseline** of the V3.2.2 engine.
- **Stage 4 (blind validation) is not run on cal-1.** The 8 validation observations (`observed_validation.csv`)
  stay unopened. Stage 4 is run once, on cal-2, after cal-2 is fitted and frozen.
- Reason: running stage 4 on a model already known to lack these processes would spend the blind set, and cal-2
  could then only be judged against seen data.
- cal-2 will be specified in a separate pre-registered proposal (engine changes, tests, predictions) before any
  cal-2 code is used for calibration.

## 2. Execution record of the cal-1 grid (results unaffected)

- Original grid (2026-11-02 to 2026-11-04): 117 completed, 87 capped, 0 errors.
- Amendment-1 re-run 1 (2026-11-04 to 2026-11-05, runner tag `amend1-runner`): 44 completed; 13 E2S2 runs failed
  with MemoryError while five Walsh diagnostics ran alongside; the batch then stopped (laptop) with 30 runs left.
- Runner memory fix (2026-11-06, `CHANGELOG.md` "memfix"; history kept as columns, results verified identical,
  including resume from a checkpoint written by the previous runner).
- Amendment-1 re-run 2 (2026-11-06 to 2026-11-07, 19.9 h): the remaining 43 runs; checkpointed runs resumed.
- Final state: 204 / 204 results, **0 censored, 0 errors**; largest |balance error| 2.5e-6 m3.
- The Numba backend (`fast_hydro.py`, verified bit-identical on this laptop, 2026-11-07) was **not** used for cal-1.

## 3. Fit

`fit.py` is run as specified by amendment 1 / 1a. With no censored runs, the censoring-sensitivity fit equals the
primary fit by construction.
