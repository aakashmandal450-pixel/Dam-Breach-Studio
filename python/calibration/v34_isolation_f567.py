"""V3.4 isolation test 3 (regression hunt): which of F5 / F6 / F7 collapses the breach?

The F1-F7 grid check is not a convergence failure, it is a broken run. Against the F1-F4 isolation
baseline the peaks fall off a cliff, and breach_width is 0.0 on all six F1-F7 runs:

    case              F1-F4 base        F1-F7
    LaurelRun  H/9         401            0.2      breach never opens
    LaurelRun  H/12        512            1.4      breach never opens
    Castlewood H/9         837            193
    Castlewood H/12        889             80

This script finds the fix that does it. Baseline is F1+F2+F3+F4 (cal-2 options, neutral factors,
f = 1), then one fix is added per rung:

    base    F1+F2+F3+F4                                       (reference)
    f5      + collapse_mode = "bank_wedge"                     F5
    f56     + sediment_face_flux = "hydro"                     F6
    f567    + headcut_face_slope = 1.0                         F7  == full F1-F7

and two leave-one-out variants off the full set, to separate a single fix from an interaction:

    no_f5   F6 + F7, collapse_mode left at cal-2 "all_pairs"
    no_f6   F5 + F7, sediment_face_flux left at "centred"

`no_f7` is not run: it is the same configuration as `f56`.

What each rung changes, precisely (cal-2 already sets headcut_mode="scarp",
collapse_mode="all_pairs", headcut_min_slope=0.5):
  * F5 switches the collapse law from all-pairs Culmann to whole-bank wedges (cohesive only; both
    cases have c > 0, so both take the new path).
  * F6 moves sediment with the flow solver's own face discharges instead of centred differences.
  * F7 is ONLY headcut_face_slope=1.0. That is the big one to watch: it swaps _migrate_scarp (C1,
    which gates on the scarp's OVERALL slope >= headcut_min_slope = 0.5) for
    _migrate_scarp_volume (F7, which gates on each CELL-TO-CELL slope >= 1.0). The dam faces are
    1:2.5 and 1:3 (slope 0.33-0.40) and the logged scarps never exceed 0.62, so a per-cell 1.0 gate
    can never fire while a cumulative 0.5 gate does. If the cliff is at f567, that is why.

Reads the F1-F4 reference from runs/v34_isolation_laurel and runs/v34_isolation where available.
Writes runs/v34_isolation_f567/*.json plus a summary (also to --desktop). Resumable: an existing
JSON is skipped, so the script can be stopped and restarted, and the ladder runs before the
leave-one-out pair so the answer usually lands early.

Usage (from the python folder):
    python -u calibration\\v34_isolation_f567.py --workers 6 --desktop <folder>
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
ROOT = HERE.parent.parent
OUT = ROOT / "runs" / "v34_isolation_f567"

CASES = ("LaurelRun", "Castlewood")
GRIDS = (9, 12)
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}
MAX_CPU_S = 7200.0          # 2 h per run; a pathological config is censored rather than left to burn

# F1+F2+F3+F4. headcut_mode="scarp" comes from cal-2, which is what makes headcut_overfall="free" legal.
BASE = {
    "hydrostatic_reconstruction": "chen_noelle",   # F1
    "headcut_overfall": "free",                    # F2
    "adaptation_dx_floor": False,                  # F3
    "collapse_to_repose": True,                    # F4
}
F5 = {"collapse_mode": "bank_wedge"}
F6 = {"sediment_face_flux": "hydro"}
F7 = {"headcut_face_slope": 1.0}

# Ordered: ladder first, then the leave-one-out pair.
VARIANTS = {
    "base": {},
    "f5": {**F5},
    "f56": {**F5, **F6},
    "f567": {**F5, **F6, **F7},
    "no_f5": {**F6, **F7},
    "no_f6": {**F5, **F7},
}
LADDER = ("base", "f5", "f56", "f567")

# F1-F4 reference peaks already on disk, for the "vs base" column when a rung has not been run yet.
REF = {("LaurelRun", 9): 401.0, ("LaurelRun", 12): 512.0,
       ("Castlewood", 9): 837.0, ("Castlewood", 12): 889.0}


def path_for(case: str, gd: int, var: str) -> Path:
    return OUT / f"{case}__H{gd}__{var}.json"


def worker(task):
    case, gd, var = task
    path = path_for(case, gd, var)
    if path.exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    try:
        ov = dict(BASE); ov.update(VARIANTS[var])
        r = C.run(C.load_case(case), dict(NEUTRAL), grid_divisor=float(gd), model="cal-2",
                  post_peak_stop=True, overrides=ov, max_cpu_seconds=MAX_CPU_S)
        out = {"id": case, "grid": gd, "variant": var, "overrides": ov,
               "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"],
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"],
               "censored": r["censored"], "cpu_s": r["cpu_s"],
               "max_balance": max(abs(x) for x in r["balances"])}
    except Exception as exc:
        out = {"id": case, "grid": gd, "variant": var, "error": repr(exc)}
    path.write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def load(case: str, gd: int, var: str):
    p = path_for(case, gd, var)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def summary() -> str:
    rows = ["V3.4 isolation test 3: which of F5 / F6 / F7 collapses the breach?",
            "Baseline F1+F2+F3+F4, neutral factors, cal-2 options. Qp [m3/s], B [m], Tp [h].",
            "'vs base' = Qp / Qp(base) at the same grid; B = 0 means the breach never opened.",
            ""]
    for case in CASES:
        rows.append(f"--- {case} " + "-" * (62 - len(case)))
        rows.append(f"{'variant':8s} " + " ".join(f"{'H/' + str(g):>26s}" for g in GRIDS)
                    + "   H9->H12 Qp   verdict")
        base = {g: load(case, g, "base") for g in GRIDS}
        for var in VARIANTS:
            res = {g: load(case, g, var) for g in GRIDS}
            cells = []
            for g in GRIDS:
                r = res[g]
                if r is None:
                    cells.append(f"{'(not run)':>26s}")
                elif "error" in r:
                    cells.append(f"{'ERROR':>26s}")
                else:
                    b = base[g]
                    ref = b["Qp"] if (b and "error" not in b and b["Qp"]) else REF.get((case, g))
                    rel = f" x{r['Qp'] / ref:5.2f}" if (ref and var != "base") else "      "
                    cells.append(f"{r['Qp']:8.1f} B{r['B']:5.0f} T{r['Tp_h']:5.2f}"
                                 f"{'*' if r['censored'] else ' '}{rel}")
            a, b2 = res[GRIDS[0]], res[GRIDS[1]]
            if a and b2 and "error" not in a and "error" not in b2 and a["Qp"]:
                ch = b2["Qp"] / a["Qp"] - 1
                cells.append(f"   {ch * 100:+7.1f} %   "
                             f"{'converged (<10 %)' if abs(ch) < 0.10 else 'NOT converged'}")
            rows.append(f"{var:8s} " + " ".join(cells))
        # where the ladder falls off
        drop = None
        for i in range(1, len(LADDER)):
            prev, cur = LADDER[i - 1], LADDER[i]
            for g in GRIDS:
                rp, rc = load(case, g, prev), load(case, g, cur)
                if rp and rc and "error" not in rp and "error" not in rc and rp["Qp"]:
                    if rc["Qp"] / rp["Qp"] < 0.5 and drop is None:
                        drop = (prev, cur, g, rp["Qp"], rc["Qp"])
        if drop:
            prev, cur, g, qp, qc = drop
            rows.append(f"  >> cliff: {prev} -> {cur} at H/{g}: {qp:.1f} -> {qc:.1f} m3/s "
                        f"(x{qc / qp:.2f}). The fix added at '{cur}' is the regression.")
        rows.append("")
    allr = [r for r in (load(c, g, v) for c in CASES for g in GRIDS for v in VARIANTS) if r]
    bal = [r.get("max_balance", 0.0) for r in allr if "error" not in r]
    done = sum(1 for r in allr if "error" not in r)
    rows.append(f"runs complete: {done} / {len(CASES) * len(GRIDS) * len(VARIANTS)}"
                f"   max |balance error|: {max(bal) if bal else float('nan'):.1e} m3   (* = censored)")
    for r in allr:
        if "error" in r:
            rows.append(f"ERROR {r['id']} H/{r['grid']} {r['variant']}: {r['error']}")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--desktop", default=None)
    ap.add_argument("--ladder-only", action="store_true",
                    help="run only base/f5/f56/f567 (16 runs) and skip the leave-one-out pair")
    ap.add_argument("--summary-only", action="store_true", help="re-print the summary, run nothing")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    wanted = LADDER if a.ladder_only else tuple(VARIANTS)
    # ladder first; inside a variant the slow H/12 starts first so the pool packs well
    tasks = [(case, gd, var) for var in wanted
             for gd in sorted(GRIDS, reverse=True) for case in CASES]
    todo = [t for t in tasks if not path_for(*t).exists()]

    if not a.summary_only:
        print(f"V3.4 isolation test 3: {len(tasks)} runs, {len(todo)} to do, {a.workers} workers, "
              f"cap {MAX_CPU_S / 3600:.0f} h/run", flush=True)
        t0 = time.time()
        if todo:
            with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
                for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                    case, gd, var = task
                    print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} {case:11s} H/{gd:<3d} "
                          f"{var:6s} {status:5s} {wall / 60:6.1f} min   "
                          f"elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)

    text = summary()
    print("\n" + text, flush=True)
    (OUT / "SUMMARY.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop, f"v34_isolation_f567_summary_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
