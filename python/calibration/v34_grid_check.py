"""V3.4 grid-convergence check (diagnostic, seen cases; ENGINE_FINDINGS_2026-11-10.md).

Runs Castlewood (non-cohesive) and Laurel Run (cohesive) at grid divisors H/6, H/9, H/12 with neutral factors
(f_kd = C_h = f_t = 1, so no calibration compensation) and the cal-2 engine options plus:
    F12  = F1 (Chen-Noelle reconstruction) + F2 (headcut only at a free overfall)
    F123 = F12 + F3 (no dx floor on the adaptation length)
    F1234 = F123 + F4 (slope collapse to the repose angle every morph step)
    F12345 = F1234 + F5 (Culmann on whole banks, wedge removed by volume; cohesive soil only)
New runs also save the first and last bed to runs/v34_gridcheck/beds/.
Writes one JSON per run to runs/v34_gridcheck/ and a summary table (also to the Desktop when --desktop is given).
Target for V3.4: peak within 10 % between H/9 and H/12.

Usage (from the python folder):  python -u calibration\\v34_grid_check.py --workers 5 --desktop <folder>
Finished runs are skipped when the script is run again.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "runs" / "v34_gridcheck"
CASES = ("Castlewood", "LaurelRun")
GRIDS = (6, 9, 12)
SETUPS = {
    "F12": {"hydrostatic_reconstruction": "chen_noelle", "headcut_overfall": "free"},
    "F123": {"hydrostatic_reconstruction": "chen_noelle", "headcut_overfall": "free", "adaptation_dx_floor": False},
    "F1234": {"hydrostatic_reconstruction": "chen_noelle", "headcut_overfall": "free", "adaptation_dx_floor": False,
              "collapse_to_repose": True},
    "F12345": {"hydrostatic_reconstruction": "chen_noelle", "headcut_overfall": "free", "adaptation_dx_floor": False,
               "collapse_to_repose": True, "collapse_mode": "bank_wedge"},
}
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}


def worker(task):
    cid, gd, setup = task
    path = OUT / f"{cid}__H{gd}__{setup}.json"
    if path.exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    import numpy as np
    kept = {}
    _build = C.build

    def build(*a, **k):                      # keep the mesh of this run to save its first and last bed
        out = _build(*a, **k)
        kept["mesh"], kept["z0"] = out[0], out[0].z_b.copy()
        return out
    C.build = build
    try:
        r = C.run(C.load_case(cid), dict(NEUTRAL), grid_divisor=float(gd), model="cal-2", post_peak_stop=True,
                  overrides=dict(SETUPS[setup]), max_cpu_seconds=4 * 3600.0)
        out = {"id": cid, "grid": gd, "setup": setup, "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"],
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"], "censored": r["censored"],
               "cpu_s": r["cpu_s"], "max_balance": max(abs(x) for x in r["balances"]), "cells": r["grid"]}
        import breach_engine_2d_v3_2 as E
        out["collapse"] = dict(getattr(E.BankStability, "stats", {}))   # calls, passes, max_passes, limit_hits, ...
        if "mesh" in kept:
            (OUT / "beds").mkdir(exist_ok=True)
            m = kept["mesh"]
            np.savez_compressed(OUT / "beds" / f"{cid}__H{gd}__{setup}.npz", z0=kept["z0"], z_end=m.z_b, h_end=m.h,
                                dx=m.dx, dy=m.dy)
    except Exception as exc:          # recorded, run again to retry
        out = {"id": cid, "grid": gd, "setup": setup, "error": repr(exc)}
    path.write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def summary():
    rows = ["V3.4 grid check (neutral factors f = 1, cal-2 options + fixes); peak Qp [m3/s], width B [m], Tp [h]",
            f"{'case':11s} {'setup':6s} " + "  ".join(f"{'H/' + str(g):>22s}" for g in GRIDS) + "   H9->H12 Qp   verdict"]
    for cid in CASES:
        for setup in SETUPS:
            res = {}
            for g in GRIDS:
                p = OUT / f"{cid}__H{g}__{setup}.json"
                res[g] = json.loads(p.read_text()) if p.exists() else None
            cells = []
            for g in GRIDS:
                r = res[g]
                if r is None:
                    cells.append(f"{'(not run)':>22s}")
                elif "error" in r:
                    cells.append(f"{'ERROR':>22s}")
                else:
                    cells.append(f"{r['Qp']:7.0f} B{r['B']:5.0f} T{r['Tp_h']:4.2f}{'*' if r['censored'] else ' '}")
            a, b = res[9], res[12]
            if a and b and "error" not in a and "error" not in b:
                ch = b["Qp"] / a["Qp"] - 1
                verdict = "converged (<10 %)" if abs(ch) < 0.10 else "NOT converged"
                cells.append(f"   {ch * 100:+6.1f} %   {verdict}")
            rows.append(f"{cid:11s} {setup:6s} " + "  ".join(cells))
            if SETUPS[setup].get("collapse_to_repose"):
                st = [(g, res[g]["collapse"]) for g in GRIDS if res[g] and "collapse" in res[g]]
                if st:
                    rows.append("            collapse passes per call, mean / max (calls ended at the cap): " + ";  ".join(
                        f"H/{g} {c['passes'] / max(c['calls'], 1):.1f} / {c['max_passes']} ({c['limit_hits']})"
                        for g, c in st))
                if SETUPS[setup].get("collapse_mode") == "bank_wedge" and st:
                    rows.append("            bank failures, fallen volume [m3], first collapse [s]: " + ";  ".join(
                        f"H/{g} {c.get('wedge_failures', 0)}, {c.get('wedge_volume_m3', 0.0):.0f}, "
                        + ("-" if c.get('first_collapse_time_s') is None else f"{c['first_collapse_time_s']:.0f}")
                        for g, c in st))
    bal = [json.loads(p.read_text()).get("max_balance", 0) for p in OUT.glob("*.json")]
    rows.append(f"max |balance error| over all runs: {max(bal) if bal else float('nan'):.1e} m3   (* = censored)")
    rows.append("Reference, V3.3 as calibrated (cal-2 factors), Qp at H/6 / 9 / 12: Castlewood 2,119 / 374 / 345; "
                "Laurel Run 609 / 1,046 / 1,184 m3/s")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--desktop", default=None, help="folder for the summary file")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [(c, g, s) for c in CASES for s in SETUPS for g in GRIDS]
    todo = [t for t in tasks if not (OUT / f"{t[0]}__H{t[1]}__{t[2]}.json").exists()]
    print(f"V3.4 grid check: {len(tasks)} runs, {len(todo)} to do, {a.workers} workers", flush=True)
    t0 = time.time()
    if todo:
        # longest runs first (fine grids)
        todo.sort(key=lambda t: -t[1])
        with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
            for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} {task[0]:11s} H/{task[1]:<3d} {task[2]:6s} {status:5s} "
                      f"{wall / 60:6.1f} min   elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)
    text = summary()
    print("\n" + text, flush=True)
    (OUT / "SUMMARY.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop, f"v34_gridcheck_summary_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
