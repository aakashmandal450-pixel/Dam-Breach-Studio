"""V3.4 Castlewood factor refit: how far did F1-F7 move the calibration optimum?

cal-2's factors (f_kd 1, C_h 10, f_t 3.162) were fitted to an engine WITHOUT F1-F7. That engine
under-eroded, so the fit had to compensate. F1-F7 erodes far more at the same factors - at neutral
factors Castlewood went from Qp 39 (old) to 874 (F1-F7), and its objective from J 20.45 to 1.99 -
so the old factors are stale and will tend to overshoot.

This sweeps C_h x f_t on the F1-F7 engine using the SAME grid (H/6, the protocol's field-case
calibration grid), the SAME log-spaced factor values and the SAME objective as the original cal-2
study, so the two surfaces are comparable cell by cell. The difference between them is the effect
of F1-F7 on the calibration, which is what decides whether a full refit is needed.

Objective is cases.score() verbatim - the CALIBRATION_PROTOCOL objective, not a stand-in:

    J = ln(Qp_model / Qp_obs)^2 + ((B_model - B_obs) / B_obs)^2        [+ Tp term where observed]

Castlewood observations: Qp 3570 m3/s, B 54.9 m. f_kd is inert here (it scales measured kd only,
and Castlewood is non-cohesive), so C_h x f_t is the complete factor space for this case.

### Read the warning in the summary before acting on the result

Castlewood's own optimum on the OLD engine was C_h 0.3162, f_t 31.62 (J 0.011) while cal-2 chose
C_h 10, f_t 3.162 (J 0.347 for this case). The difference is the cost of fitting six cases jointly.
Tuning the factors to Castlewood alone would move C_h down ~30x and f_t up ~10x and would very
likely wreck the other five. This sweep tells you WHERE the optimum moved; it is not a licence to
adopt a single-case fit.

Writes runs/v34_castlewood_refit/*.json and a summary (also to --desktop). Resumable.

Usage (from the python folder):
    python -u calibration\\v34_castlewood_refit.py --workers 2 --desktop <folder>
    python -u calibration\\v34_castlewood_refit.py --full              # all 42 cells of the old grid
    python -u calibration\\v34_castlewood_refit.py --grid 9            # confirm the best cells finer
    python -u calibration\\v34_castlewood_refit.py --summary-only
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "runs" / "v34_castlewood_refit"
OLD = ROOT / "runs" / "calibration_grid_cal2"        # pre-F1-F7 surface, same grid and factors

CASE = "Castlewood"
GRID = 6                                              # protocol field-case calibration grid
MAX_CPU_S = 2 * 3600.0

# Fix sets, exactly as in v34_isolation_f567.py / v34_convergence.py
BASE_F14 = {
    "hydrostatic_reconstruction": "chen_noelle",   # F1
    "headcut_overfall": "free",                    # F2
    "adaptation_dx_floor": False,                  # F3
    "collapse_to_repose": True,                    # F4
}
VARIANTS = {
    "f567": {**BASE_F14,
             "collapse_mode": "bank_wedge",        # F5
             "sediment_face_flux": "hydro",        # F6
             "headcut_face_slope": 1.0},           # F7
    "base": dict(BASE_F14),                        # F1-F4 only
}
F567 = VARIANTS["f567"]          # kept for anything importing the old name
_VAR = "f567"                    # variant the summary reads; main() sets it

# the original cal-2 study's log-spaced values
ALL_CH = (0.03162, 0.1, 0.3162, 1.0, 3.162, 10.0)
ALL_FT = (0.03162, 0.1, 0.3162, 1.0, 3.162, 10.0, 31.62)
# default: the live region. F1-F7 erodes more, so the optimum should move to LOWER f_t than the
# old engine's 31.62 - this range brackets both.
DEF_CH = (0.1, 0.3162, 1.0, 3.162, 10.0)
DEF_FT = (0.3162, 1.0, 3.162, 10.0, 31.62)

CAL2_FIT = (10.0, 3.162)
OBS_Q, OBS_B = 3570.0, 54.9


def g(v):
    return f"{v:g}"


def path_for(ch, ft, grid, var=None):
    return OUT / f"{CASE}__H{grid}__{var or _VAR}__Ch{g(ch)}_ft{g(ft)}.json"


def old_path(ch, ft):
    return OLD / f"{CASE}__fkd1_Ch{g(ch)}_ft{g(ft)}.json"


def J_of(Qp, B):
    """Fallback objective, identical to cases.score() for this case (no Tp observed)."""
    if Qp is None or B is None:
        return None
    return math.log(max(Qp, 1e-9) / OBS_Q) ** 2 + ((B - OBS_B) / OBS_B) ** 2


def worker(task):
    ch, ft, grid, var = task
    path = path_for(ch, ft, grid, var)
    if path.exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    try:
        case = C.load_case(CASE)
        factors = {"f_kd": 1.0, "C_h": ch, "f_t": ft}
        r = C.run(case, factors, grid_divisor=float(grid), model="cal-2",
                  post_peak_stop=True, overrides=dict(VARIANTS[var]), max_cpu_seconds=MAX_CPU_S)
        try:                                    # the protocol objective, verbatim
            sc = C.score(case, r)
            Jv, terms = sc["J"], sc["terms"]
        except Exception as exc:
            Jv, terms = J_of(r.get("Qp"), r.get("B")), {"_score_error": repr(exc)}
        out = {"case": CASE, "grid": grid, "variant": var, "C_h": ch, "f_t": ft, "f_kd": 1.0,
               "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"],
               "max_lowering_m": r["max_lowering_m"], "J": Jv, "terms": terms,
               "stop_cause": r["stop_cause"], "censored": r["censored"], "cpu_s": r["cpu_s"],
               "max_balance": max(abs(x) for x in r["balances"])}
    except Exception as exc:
        import traceback
        out = {"case": CASE, "grid": grid, "variant": var, "C_h": ch, "f_t": ft,
               "error": repr(exc), "trace": traceback.format_exc()}
    path.write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def load(ch, ft, grid, var=None):
    p = path_for(ch, ft, grid, var)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        return None if "error" in d else d
    except Exception:
        return None


def load_old(ch, ft):
    p = old_path(ch, ft)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
        if "error" in d or d.get("Qp") is None:
            return None
        d.setdefault("J", J_of(d.get("Qp"), d.get("B")))
        return d
    except Exception:
        return None


def table(rows, chs, fts, grid, key, fmt, title, old_too=False):
    out = [title, "   C_h\\f_t" + "".join(f"{t:>12g}" for t in fts)]
    for c in chs:
        line = f"{c:9g}"
        for t in fts:
            d = load(c, t, grid)
            v = d.get(key) if d else None
            cell = (fmt % v) if v is not None else "-"
            if old_too:
                o = load_old(c, t)
                ov = o.get(key) if o else None
                cell = f"{cell}/{(fmt % ov) if ov is not None else '-'}"
            line += f"{cell:>12s}"
        out.append(line)
    return out


def summary(chs, fts, grid):
    rows = [f"V3.4 CASTLEWOOD FACTOR REFIT - variant {_VAR} "
            f"({'F1-F7' if _VAR == 'f567' else 'F1-F4 only'})",
            f"grid H/{grid} (protocol field-case grid), f_kd = 1 (inert for this case).",
            f"observed: Qp {OBS_Q:.0f} m3/s, B {OBS_B:.1f} m.   "
            f"J = ln(Qp/Qp_obs)^2 + ((B-B_obs)/B_obs)^2, lower is better.", ""]

    done = [(c, t) for c in chs for t in fts if load(c, t, grid)]
    rows.append(f"cells complete: {len(done)} / {len(chs) * len(fts)}")
    rows.append("")

    rows += table(None, chs, fts, grid, "Qp", "%.0f",
                  "Qp [m3/s]   (observed 3570)")
    rows.append("")
    rows += table(None, chs, fts, grid, "B", "%.1f",
                  "B [m]   (observed 54.9)")
    rows.append("")
    rows += table(None, chs, fts, grid, "max_lowering_m", "%.1f",
                  "max lowering [m]   (dam height 21.34)")
    rows.append("")
    rows += table(None, chs, fts, grid, "J", "%.3f",
                  "J   NEW (F1-F7) / OLD (pre-F1-F7)", old_too=True)
    rows.append("")

    # best cells
    cells = [(load(c, t, grid)["J"], c, t, load(c, t, grid)) for c in chs for t in fts
             if load(c, t, grid) and load(c, t, grid).get("J") is not None]
    if cells:
        cells.sort()
        rows.append("-" * 92)
        rows.append("BEST CELLS on the F1-F7 engine (Castlewood alone)")
        rows.append("-" * 92)
        rows.append(f"  {'C_h':>9s} {'f_t':>9s} {'Qp':>9s} {'B':>8s} {'maxlow':>8s} {'J':>8s}   "
                    f"{'J old':>8s}  shift")
        for Jv, c, t, d in cells[:6]:
            o = load_old(c, t)
            oj = o.get("J") if o else None
            shift = ""
            if oj is not None and oj > 0:
                shift = f"x{Jv / oj:.2f}" if Jv > 0 else "->0"
            rows.append(f"  {c:9g} {t:9g} {d['Qp']:9.0f} {d['B']:8.1f} "
                        f"{d['max_lowering_m']:8.2f} {Jv:8.3f}   "
                        f"{(f'{oj:8.3f}' if oj is not None else '       -')}  {shift}")
        rows.append("")

        # where cal-2's fit now lands
        d = load(*CAL2_FIT, grid)
        o = load_old(*CAL2_FIT)
        rows.append("-" * 92)
        rows.append(f"cal-2's FITTED point  C_h = {CAL2_FIT[0]:g}, f_t = {CAL2_FIT[1]:g}")
        rows.append("-" * 92)
        if d:
            rows.append(f"  on F1-F7 : Qp {d['Qp']:8.0f}   B {d['B']:6.1f}   J {d['J']:7.3f}")
            if o:
                rows.append(f"  on old   : Qp {o['Qp']:8.0f}   B {o['B']:6.1f}   J {o['J']:7.3f}")
                if d["Qp"] and o["Qp"]:
                    rows.append(f"  F1-F7 changes Qp here by x{d['Qp'] / o['Qp']:.2f}")
                if d["J"] > o["J"]:
                    rows.append("  -> the old fit is now WORSE for Castlewood: the factors are stale "
                                "and need refitting on this engine.")
                else:
                    rows.append("  -> the old fit still holds up for Castlewood on this engine.")
        else:
            rows.append("  (not run yet)")
        rows.append("")

        best = cells[0]
        rows.append("-" * 92)
        rows.append("WARNING - do not adopt this as the model's factors")
        rows.append("-" * 92)
        rows.append(f"  The best cell here (C_h {best[1]:g}, f_t {best[2]:g}, J {best[0]:.3f}) is the "
                    f"optimum for CASTLEWOOD ALONE.")
        rows.append("  cal-2 deliberately did not sit at Castlewood's optimum: it chose "
                    f"C_h {CAL2_FIT[0]:g}, f_t {CAL2_FIT[1]:g} as the")
        rows.append("  compromise across all six cases. On the old engine, Castlewood alone wanted "
                    "C_h 0.3162, f_t 31.62")
        rows.append("  - roughly 30x lower C_h and 10x higher f_t than the joint fit. Adopting a "
                    "single-case optimum")
        rows.append("  would almost certainly break the other five.")
        rows.append("")
        rows.append("  Use this surface to answer: HOW FAR has the optimum moved, and is the old fit "
                    "still defensible?")
        rows.append("  If it has moved materially, the next step is a JOINT refit over the cal-2 case "
                    "set on the F1-F7")
        rows.append("  engine (fit.py), not adopting the number above.")
        rows.append("")

    cens = [(c, t) for c in chs for t in fts
            if load(c, t, grid) and load(c, t, grid).get("censored")]
    if cens:
        rows.append(f"  censored (hit the {MAX_CPU_S / 3600:.0f} h cap), treat as lower bounds: "
                    + ", ".join(f"({g(c)},{g(t)})" for c, t in cens))
    errs = [p for p in OUT.glob(f"{CASE}__H{grid}__*.json")
            if "error" in json.loads(p.read_text())]
    for p in errs:
        d = json.loads(p.read_text())
        rows.append(f"  ERROR C_h {d.get('C_h')} f_t {d.get('f_t')}: {str(d.get('error'))[:100]}")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--grid", type=int, default=GRID)
    ap.add_argument("--full", action="store_true", help="all 42 cells of the original cal-2 grid")
    ap.add_argument("--ch", nargs="+", type=float, default=None)
    ap.add_argument("--ft", nargs="+", type=float, default=None)
    ap.add_argument("--variant", default="f567", choices=sorted(VARIANTS),
                    help="f567 = F1-F7 (default); base = F1-F4 only")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--desktop", default=None)
    a = ap.parse_args()

    global _VAR
    _VAR = a.variant

    chs = tuple(a.ch) if a.ch else (ALL_CH if a.full else DEF_CH)
    fts = tuple(a.ft) if a.ft else (ALL_FT if a.full else DEF_FT)

    OUT.mkdir(parents=True, exist_ok=True)
    # coarse factors first so the shape of the surface appears early
    tasks = [(c, t, a.grid, a.variant) for t in fts for c in chs]
    todo = [t for t in tasks if not path_for(*t).exists()]

    if not a.summary_only:
        print(f"V3.4 Castlewood refit [{a.variant}]: H/{a.grid}, {len(chs)} x {len(fts)} = "
              f"{len(tasks)} cells, {len(todo)} to do, {a.workers} workers, "
              f"cap {MAX_CPU_S / 3600:.0f} h/run", flush=True)
        print(f"  overrides: {VARIANTS[a.variant]}", flush=True)
        print(f"  C_h: {', '.join(g(c) for c in chs)}", flush=True)
        print(f"  f_t: {', '.join(g(t) for t in fts)}", flush=True)
        if todo:
            t0 = time.time()
            with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
                for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                    c, t, _, _v = task
                    d = load(c, t, a.grid)
                    note = (f"Qp {d['Qp']:7.0f}  B {d['B']:5.1f}  J {d['J']:6.3f}"
                            if d and d.get("J") is not None else "")
                    print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} "
                          f"C_h {g(c):>7s} f_t {g(t):>7s} {status:5s} {wall / 60:5.1f} min  {note}"
                          f"   elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)
        else:
            print("  nothing to run - all cells present", flush=True)

    text = summary(chs, fts, a.grid)
    print("\n" + text, flush=True)
    (OUT / f"SUMMARY_{a.variant}_H{a.grid}.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop,
             f"v34_castlewood_refit_{a.variant}_H{a.grid}_"
             f"{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
