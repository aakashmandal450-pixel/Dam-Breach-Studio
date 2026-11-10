"""V3.4 isolation test (diagnostic, seen case): which process carries the remaining grid dependence?

Castlewood, neutral factors (f = 1), cal-2 options + F1 + F2 + F3, grid divisors H/9 and H/12, four variants:
    base        as F1+F2+F3 (collapse_iterations 3 per morph step, as cal-2)
    repose      slope collapse repeated until every pair is at the critical angle each morph step
                (collapse_iterations 500; the loop stops as soon as nothing moves)
    noheadcut   headcut switched off
    both        repose + noheadcut
The variant whose H/9 and H/12 peaks agree (< 10 %) points to the grid-dependent process.
Writes runs/v34_isolation/*.json and a summary (also to --desktop).

Usage (from the python folder):  python -u calibration\\v34_isolation.py --workers 5 --desktop <folder>
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
OUT = HERE.parent.parent / "runs" / "v34_isolation"
CASE = "Castlewood"
GRIDS = (9, 12)
FIXES = {"hydrostatic_reconstruction": "chen_noelle", "headcut_overfall": "free", "adaptation_dx_floor": False}
VARIANTS = {
    "base": {},
    "repose": {"collapse_iterations": 500},
    "noheadcut": {"headcut_enabled": False},
    "both": {"collapse_iterations": 500, "headcut_enabled": False},
}
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}


def worker(task):
    gd, var = task
    path = OUT / f"{CASE}__H{gd}__{var}.json"
    if path.exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    try:
        ov = dict(FIXES); ov.update(VARIANTS[var])
        r = C.run(C.load_case(CASE), dict(NEUTRAL), grid_divisor=float(gd), model="cal-2", post_peak_stop=True,
                  overrides=ov, max_cpu_seconds=4 * 3600.0)
        out = {"id": CASE, "grid": gd, "variant": var, "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"],
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"], "censored": r["censored"],
               "cpu_s": r["cpu_s"], "max_balance": max(abs(x) for x in r["balances"])}
    except Exception as exc:
        out = {"id": CASE, "grid": gd, "variant": var, "error": repr(exc)}
    path.write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def summary():
    rows = [f"V3.4 isolation test: {CASE}, neutral factors, F1+F2+F3; Qp [m3/s], B [m], Tp [h]",
            f"{'variant':10s} {'H/9':>24s} {'H/12':>24s}   H9->H12 Qp   verdict"]
    for var in VARIANTS:
        res = {}
        for g in GRIDS:
            p = OUT / f"{CASE}__H{g}__{var}.json"
            res[g] = json.loads(p.read_text()) if p.exists() else None
        cells = []
        for g in GRIDS:
            r = res[g]
            if r is None:
                cells.append(f"{'(not run)':>24s}")
            elif "error" in r:
                cells.append(f"{'ERROR':>24s}")
            else:
                cells.append(f"{r['Qp']:8.0f} B{r['B']:5.0f} T{r['Tp_h']:5.2f}{'*' if r['censored'] else ' '}")
        a, b = res[9], res[12]
        if a and b and "error" not in a and "error" not in b:
            ch = b["Qp"] / a["Qp"] - 1
            cells.append(f"   {ch * 100:+6.1f} %   {'converged (<10 %)' if abs(ch) < 0.10 else 'NOT converged'}")
        rows.append(f"{var:10s} " + " ".join(cells))
    errs = [json.loads(p.read_text()) for p in OUT.glob("*.json")]
    bal = [e.get("max_balance", 0) for e in errs if "error" not in e]
    rows.append(f"max |balance error|: {max(bal) if bal else float('nan'):.1e} m3   (* = censored)")
    for e in errs:
        if "error" in e:
            rows.append(f"ERROR {e['variant']} H/{e['grid']}: {e['error']}")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--desktop", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [(g, v) for g in sorted(GRIDS, reverse=True) for v in VARIANTS]
    todo = [t for t in tasks if not (OUT / f"{CASE}__H{t[0]}__{t[1]}.json").exists()]
    print(f"V3.4 isolation test: {len(tasks)} runs, {len(todo)} to do, {a.workers} workers", flush=True)
    t0 = time.time()
    if todo:
        with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
            for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} H/{task[0]:<3d} {task[1]:10s} {status:5s} "
                      f"{wall / 60:6.1f} min   elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)
    text = summary()
    print("\n" + text, flush=True)
    (OUT / "SUMMARY.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop, f"v34_isolation_summary_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
