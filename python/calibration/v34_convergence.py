"""V3.4 grid convergence: three grids, four metrics, observed order and GCI.

Two grids can only tell you that two numbers are close. Three tell you whether the solution is
actually settling, and at what rate. This runs F1-F7 (the `f567` configuration) at H/9, H/12 and
H/15 on both cases and reports, for each metric:

    Qp              peak outflow            [m3/s]
    B               breach width            [m]
    Tp_h            time to peak            [h]
    max_lowering_m  deepest cut in the dam  [m]

    change          successive-grid percentage changes
    p               observed order of convergence, from the three grids (Roache / ASME)
    extrapolated    Richardson value at zero cell size
    GCI_fine        grid convergence index on the finest pair: a +/- band on the H/15 value

Why those extra columns. A metric can change by less than 10 % between two grids and still be
drifting; a metric with a clean observed order near 1-2 and a small GCI is genuinely converging.
The script also flags OSCILLATORY convergence, where the value goes up then down - the signs of the
successive differences disagree, the order cannot be computed, and a small percentage change
between the last two grids is then not evidence of anything.

The H/9 and H/12 f567 results already exist in runs/v34_isolation_f567. They are reused as-is, so
only the two H/15 runs are new. Nothing is recomputed unless it is missing.

Grid ratios here are NOT uniform (12/9 = 1.333, 15/12 = 1.25), so the order is solved iteratively
rather than with the equal-ratio shortcut.

2026-11-19 additions:
    B_eq     grid-independent breach width: eroded cross-section area / deepest cut (= average
             width for a trapezoid, the Wahl / Froehlich definition). Reported next to B.
    cell     variant: F1-F7 with headcut_gate = cell (the one-cell rule, overfall 'any') - the
             closest-to-observed row of the 2026-11-19 law sweep.
    --tag    writes to runs/v34_convergence_<tag> and does NOT reuse old results (they have no
             B_eq). Without --tag the original folder and its results are used as before.
    p guard  a GCI verdict is only given when 0.5 <= p <= 3; outside that range the three grids
             are not in the asymptotic range and the GCI is meaningless (it collapses to ~0 as
             r^p explodes). Saturated metrics (max_lowering = dam height) are labelled as such.

Usage (from the python folder):
    python -u calibration\\v34_convergence.py --workers 2 --desktop <folder>
    python -u calibration\\v34_convergence.py --tag beq --variants f567 cell --workers 6
    python -u calibration\\v34_convergence.py --with-base          # also run F1-F4 at H/15
    python -u calibration\\v34_convergence.py --summary-only       # re-print, run nothing
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import shutil
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "runs" / "v34_convergence"
SRC_ISO = ROOT / "runs" / "v34_isolation_f567"          # existing H/9 and H/12 results

CASES = ("LaurelRun", "Castlewood")
GRIDS = (9, 12, 15)                                      # coarse -> fine
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}
MAX_CPU_S = 4 * 3600.0                                   # H/15 is ~2x H/12; do not censor early

BASE = {
    "hydrostatic_reconstruction": "chen_noelle",   # F1
    "headcut_overfall": "free",                    # F2
    "adaptation_dx_floor": False,                  # F3
    "collapse_to_repose": True,                    # F4
}
F567 = {**BASE, "collapse_mode": "bank_wedge", "sediment_face_flux": "hydro", "headcut_face_slope": 1.0}
VARIANTS = {
    "f567": dict(F567),
    "base": dict(BASE),
    # F1-F7 with the one-cell headcut rule (law-sweep 'headcut_gate = cell'): no face-slope gate,
    # overfall 'any' because the one-cell rule predates the overfall test.
    "cell": {**{k: v for k, v in F567.items() if k != "headcut_face_slope"},
             "headcut_mode": "cell", "headcut_overfall": "any"},
}
# 2026-11-19 overfall isolation: 'cell' changed the gate AND the overfall test at once.
VARIANTS["cell_free"] = {**VARIANTS["cell"], "headcut_overfall": "free"}   # one-cell rule, overfall as F1-F7
VARIANTS["f567_any"] = {**F567, "headcut_overfall": "any"}                 # scarp gates, overfall as 'cell'
VARIANT_LABEL = {"f567": "F1-F7", "base": "F1-F4", "cell": "F1-F7, headcut_gate = cell",
                 "cell_free": "one-cell rule, overfall = free",
                 "f567_any": "F1-F7 scarp gates, overfall = any"}
METRICS = (("Qp", "m3/s", 1), ("B", "m", 1), ("B_eq", "m", 1), ("Tp_h", "h", 2), ("max_lowering_m", "m", 2))
P_RANGE = (0.5, 3.0)        # observed order must sit here for a GCI verdict to mean anything


def path_for(case, gd, var, out=None):
    return Path(out or OUT) / f"{case}__H{gd}__{var}.json"


def case_limits(case):
    """Dam height and section width, for labelling saturated metrics."""
    try:
        d = json.loads((HERE / "cases" / f"{case}.json").read_text())
        return float(d.get("H", 0.0)), float(d.get("section_width", 0.0))
    except Exception:
        return 0.0, 0.0


def seed_from_isolation():
    """Copy the existing H/9 and H/12 results in rather than recomputing them."""
    n = 0
    for case in CASES:
        for gd in (9, 12):
            for var in VARIANTS:
                src, dst = SRC_ISO / f"{case}__H{gd}__{var}.json", path_for(case, gd, var)
                if src.exists() and not dst.exists():
                    try:
                        d = json.loads(src.read_text())
                    except Exception:
                        continue
                    if "error" in d:
                        continue
                    shutil.copyfile(src, dst)
                    n += 1
    return n


def worker(task):
    case_id, gd, var, out_dir = task
    path = path_for(case_id, gd, var, out_dir)
    if path.exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    try:
        ov = dict(VARIANTS[var])
        r = C.run(C.load_case(case_id), dict(NEUTRAL), grid_divisor=float(gd), model="cal-2",
                  post_peak_stop=True, overrides=ov, max_cpu_seconds=MAX_CPU_S)
        out = {"id": case_id, "grid": gd, "variant": var, "overrides": ov,
               "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"], "B_eq": r.get("B_eq"),
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"],
               "censored": r["censored"], "cpu_s": r["cpu_s"],
               "max_balance": max(abs(x) for x in r["balances"]), "cells": r.get("grid")}
    except Exception as exc:
        import traceback
        out = {"id": case_id, "grid": gd, "variant": var, "error": repr(exc),
               "trace": traceback.format_exc()}
    path.write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


# --------------------------------------------------------------------------- convergence maths

def observed_order(f3, f2, f1, r21, r32, tol=1e-12, iters=200):
    """Observed order p from three grids, coarse f3 -> fine f1 (Roache; ASME V&V 20).

    Solves  p = |ln|eps32/eps21| + q(p)| / ln(r21),  q(p) = ln((r21^p - s)/(r32^p - s)),
    s = sign(eps32/eps21). Returns (p, status). Non-uniform r21 != r32 is handled.
    """
    eps21, eps32 = f2 - f1, f3 - f2
    if abs(eps21) < tol or abs(eps32) < tol:
        return None, "converged (differences at round-off)"
    ratio = eps32 / eps21
    if ratio < 0:
        return None, "OSCILLATORY (signs disagree)"
    s = 1.0 if ratio > 0 else -1.0
    p = 2.0
    for _ in range(iters):
        try:
            q = math.log((r21 ** p - s) / (r32 ** p - s))
            p_new = abs(math.log(abs(ratio)) + q) / math.log(r21)
        except (ValueError, ZeroDivisionError):
            return None, "not computable"
        if abs(p_new - p) < 1e-10:
            p = p_new
            break
        p = p_new
        if p > 20 or p < 1e-6:
            return None, "out of range"
    return p, "ok"


def gci(f3, f2, f1, r21, r32, Fs=1.25):
    """Returns (p, status, f_extrapolated, gci_fine_percent)."""
    p, status = observed_order(f3, f2, f1, r21, r32)
    if p is None or abs(f1) < 1e-12:
        return p, status, None, None
    try:
        f_ext = (r21 ** p * f1 - f2) / (r21 ** p - 1.0)
        e21a = abs((f1 - f2) / f1)
        g = Fs * e21a / (r21 ** p - 1.0) * 100.0
    except (ZeroDivisionError, OverflowError):
        return p, "not computable", None, None
    return p, status, f_ext, g


def load(case, gd, var):
    p = path_for(case, gd, var)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        return None if "error" in d else d
    except Exception:
        return None


def summary(variants):
    rows = ["V3.4 GRID CONVERGENCE - three grids, observed order and GCI",
            f"grids H/9, H/12, H/15 (h ratios r21 = 15/12 = 1.250, r32 = 12/9 = 1.333); "
            f"neutral factors, cal-2.  Results: {OUT.name}",
            "GCI_fine is a +/- band on the H/15 value. 'p' is the observed order of convergence.",
            ""]
    r21, r32 = 15.0 / 12.0, 12.0 / 9.0
    verdicts = []
    for var in variants:
        rows.append("=" * 104)
        rows.append(f"VARIANT {var}   ({VARIANT_LABEL.get(var, var)})")
        rows.append("=" * 104)
        for case in CASES:
            H_dam, W_sec = case_limits(case)
            res = {g: load(case, g, var) for g in GRIDS}
            missing = [g for g in GRIDS if res[g] is None]
            rows.append(f"--- {case} " + "-" * (96 - len(case)))
            if missing:
                rows.append(f"    waiting on: {', '.join('H/' + str(g) for g in missing)}")
                have = [g for g in GRIDS if res[g] is not None]
                if len(have) < 2:
                    rows.append("")
                    continue
            cens = [g for g in GRIDS if res[g] and res[g].get("censored")]
            head = (f"  {'metric':20s}" + "".join(f"{'H/' + str(g):>11s}" for g in GRIDS)
                    + f"{'9->12':>9s}{'12->15':>9s}{'p':>7s}{'extrap':>11s}{'GCI%':>8s}   verdict")
            rows.append(head)
            for key, unit, dp in METRICS:
                vals = {g: (res[g].get(key) if res[g] else None) for g in GRIDS}
                line = f"  {key + ' [' + unit + ']':20s}"
                for g in GRIDS:
                    line += f"{vals[g]:11.{dp}f}" if vals[g] is not None else f"{'-':>11s}"
                c1 = (vals[12] / vals[9] - 1) * 100 if vals[9] and vals[12] else None
                c2 = (vals[15] / vals[12] - 1) * 100 if vals[12] and vals[15] else None
                line += f"{c1:+8.1f}%" if c1 is not None else f"{'-':>9s}"
                line += f"{c2:+8.1f}%" if c2 is not None else f"{'-':>9s}"
                if all(vals[g] is not None for g in GRIDS):
                    p, status, f_ext, g_pct = gci(vals[9], vals[12], vals[15], r21, r32)
                    line += f"{p:7.2f}" if p is not None else f"{'-':>7s}"
                    line += f"{f_ext:11.{dp}f}" if f_ext is not None else f"{'-':>11s}"
                    line += f"{g_pct:7.1f}%" if g_pct is not None else f"{'-':>8s}"
                    cap = H_dam if key == "max_lowering_m" else (W_sec if key in ("B", "B_eq") else 0.0)
                    if cap > 0 and all(abs(vals[g] - cap) <= 0.01 * cap for g in GRIDS):
                        verdict = "SATURATED (equals the physical limit; not a convergence test)"
                    elif status != "ok":
                        verdict = status
                    elif not (P_RANGE[0] <= p <= P_RANGE[1]):
                        verdict = (f"p out of asymptotic range {P_RANGE[0]}-{P_RANGE[1]}"
                                   f" - convergence not established")
                    elif g_pct is not None and g_pct < 5:
                        verdict = "CONVERGED"
                    elif g_pct is not None and g_pct < 15:
                        verdict = "marginal"
                    else:
                        verdict = "NOT converged"
                    verdicts.append((var, case, key, verdict, g_pct))
                else:
                    line += f"{'-':>7s}{'-':>11s}{'-':>8s}"
                    verdict = "incomplete"
                rows.append(line + f"   {verdict}")
            if cens:
                rows.append(f"    NOTE: censored (hit the CPU cap) at {', '.join('H/' + str(g) for g in cens)}"
                            f" - treat those numbers as lower bounds.")
            rows.append("")
    rows.append("=" * 104)
    rows.append("READING THIS")
    rows.append("=" * 104)
    rows.append("  p           observed order. Around 1-2 is a normally converging scheme. Much")
    rows.append("              above 2 usually means the three points are not yet in the asymptotic")
    rows.append("              range, not that the scheme is unusually good.")
    rows.append("  GCI_fine    uncertainty band on the H/15 value. Under ~5 % is a converged metric.")
    rows.append("  OSCILLATORY the metric rose then fell (or fell then rose) across the three grids.")
    rows.append("              The order cannot be computed, and a small 12->15 change is NOT")
    rows.append("              evidence of convergence - the solution is still moving.")
    rows.append(f"  p range     a GCI verdict is only given for {P_RANGE[0]} <= p <= {P_RANGE[1]}. A huge p makes")
    rows.append("              (r^p - 1) explode and GCI collapse to ~0 whatever the real behaviour.")
    rows.append("  B vs B_eq   B is the half-max-lowering span, counted in whole cells. B_eq is eroded")
    rows.append("              area / deepest cut, which changes smoothly with cell size. If B oscillates")
    rows.append("              and B_eq does not, the B oscillation was measurement, not physics.")
    rows.append("")
    bad = [v for v in verdicts if v[3] != "CONVERGED" and not v[3].startswith("SATURATED")]
    if verdicts and not bad:
        rows.append("  All metrics converged on all cases.")
    elif bad:
        rows.append("  Not yet converged:")
        for var, case, key, verdict, g_pct in bad:
            extra = f" (GCI {g_pct:.1f} %)" if g_pct is not None else ""
            rows.append(f"    {var:6s} {case:11s} {key:16s} {verdict}{extra}")
    rows.append("")
    return "\n".join(rows)


def main():
    global OUT, CASES
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--with-base", action="store_true", help="also run the F1-F4 baseline at H/15")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--desktop", default=None)
    ap.add_argument("--tag", default=None,
                    help="write to runs/v34_convergence_<tag>; old results are not reused")
    ap.add_argument("--variants", nargs="+", default=None, choices=sorted(VARIANTS),
                    help="variants to run (default: f567, plus base with --with-base)")
    ap.add_argument("--cases", nargs="+", default=None, choices=CASES)
    a = ap.parse_args()

    if a.tag:
        OUT = ROOT / "runs" / f"v34_convergence_{a.tag}"
    if a.cases:
        CASES = tuple(a.cases)
    OUT.mkdir(parents=True, exist_ok=True)
    variants = a.variants or (["f567"] + (["base"] if a.with_base else []))

    if not a.tag:
        n = seed_from_isolation()
        if n:
            print(f"reused {n} existing H/9 and H/12 results from {SRC_ISO.name}", flush=True)

    tasks = [(c, g, v, str(OUT)) for v in variants for g in GRIDS for c in CASES]
    # biggest runs first so the pool does not end on one long H/15 straggler
    tasks.sort(key=lambda t: (-t[1], t[0] != "LaurelRun"))
    todo = [t for t in tasks if not path_for(*t).exists()]

    if not a.summary_only:
        print(f"V3.4 convergence: {len(tasks)} runs, {len(todo)} to do, {a.workers} workers, "
              f"cap {MAX_CPU_S / 3600:.0f} h/run", flush=True)
        if todo:
            print("  new runs: " + ", ".join(f"{c} H/{g} {v}" for c, g, v, _ in todo), flush=True)
            t0 = time.time()
            with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
                for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                    c, g, v, _ = task
                    print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} {c:11s} H/{g:<3d} {v:6s} "
                          f"{status:5s} {wall / 60:6.1f} min   "
                          f"elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)
        else:
            print("  nothing to run - all results present", flush=True)

    text = summary(variants)
    print("\n" + text, flush=True)
    (OUT / "SUMMARY.txt").write_text(text + "\n")
    if a.desktop:
        tag = f"_{a.tag}" if a.tag else ""
        Path(a.desktop, f"v34_convergence{tag}_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
