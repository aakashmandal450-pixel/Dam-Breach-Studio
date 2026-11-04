"""Amendment-1 reproducibility check (PROTOCOL_AMENDMENT_1.md s.5).

Re-runs two completed, uncapped cal-1 grid runs with the new runner and the post-peak stop OFF:
the first such run of E1S1 and of Castlewood in run_grid.py --list order. Qp, Tp_h and B must match the stored
results to a relative difference of 1e-6. Results go to runs/calibration_grid/_repro/ (the grid files are not touched).

Usage (from the python folder):  python -u calibration\\repro_check.py
Takes as long as the two original runs (both run at once, one process each).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_grid import plan, run_name  # noqa: E402

OUT = HERE.parent.parent / "runs" / "calibration_grid"
TOL = 1e-6


def pick():
    chosen = {}
    for cid, fac in plan({"E1S1", "Castlewood"}):
        if cid in chosen:
            continue
        f = OUT / run_name(cid, fac)
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        if "error" in r or r.get("capped") or "score" not in r:
            continue
        chosen[cid] = (fac, r)
    return chosen


def one(args):
    cid, fac = args
    import cases as C
    t0 = time.time()
    r = C.run(C.load_case(cid), fac, chunk_s=60.0, max_cpu_seconds=None, max_wall_safety_seconds=86400.0,
              post_peak_stop=False)
    return cid, r, time.time() - t0


def main():
    chosen = pick()
    if set(chosen) != {"E1S1", "Castlewood"}:
        sys.exit(f"could not find a completed uncapped run for: {sorted({'E1S1', 'Castlewood'} - set(chosen))}")
    for cid, (fac, r) in chosen.items():
        print(f"{cid}: {run_name(cid, fac)}  stored Qp={r['Qp']:.6g} Tp_h={r['Tp_h']:.6g} B={r['B']:.6g}  "
              f"(original wall {r['wall_s'] / 60:.0f} min)", flush=True)
    print(f"started {time.strftime('%H:%M:%S')}; both runs in parallel, no progress lines until each finishes", flush=True)
    rep = OUT / "_repro"; rep.mkdir(exist_ok=True)
    ok_all = True
    with mp.get_context("spawn").Pool(2) as pool:
        for cid, r, wall in pool.imap_unordered(one, [(c, chosen[c][0]) for c in chosen]):
            old = chosen[cid][1]
            (rep / run_name(cid, chosen[cid][0])).write_text(json.dumps(r, indent=1, default=str))
            print(f"{cid}: finished in {wall / 60:.1f} min", flush=True)
            for k in ("Qp", "Tp_h", "B"):
                a, b = float(old[k]), float(r[k])
                rel = abs(a - b) / max(abs(a), 1e-12)
                ok = rel <= TOL
                ok_all &= ok
                print(f"   {k:5s} stored {a:.9g}  new {b:.9g}  rel diff {rel:.2e}  {'OK' if ok else 'MISMATCH'}", flush=True)
            if r["steps"] != old["steps"]:
                print(f"   note: steps differ ({old['steps']} vs {r['steps']})", flush=True)
    print("REPRODUCIBILITY CHECK PASSED" if ok_all else "REPRODUCIBILITY CHECK FAILED - investigate before any re-run",
          flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
