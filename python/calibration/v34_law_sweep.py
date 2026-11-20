"""V3.4 law sweep: is the physics wrong in the ARCHITECTURE, or in the FORMULA?

The engine has several interchangeable published laws behind one architecture. If the pathology
(breach never opens, width 0, peak collapses, peak depends on cell size) survives EVERY formula on
every axis, then no single law is at fault and the problem is in how the rules are composed. If one
axis makes it go away, that law - or the gate in front of it - is the suspect.

Axes swept, one at a time, around a fixed reference configuration (default: F1-F7, the broken one):

    headcut_method       energy | temple | sites           the headcut RATE law
    headcut_gate         scarp_cum | scarp_percell | cell  how a scarp is DETECTED (see note)
    headcut_min_slope    0.3 | 0.4 | 0.5 | 0.7             the C1 cumulative gate threshold
    headcut_face_slope   off | 0.4 | 0.6 | 1.0             the F7 per-cell gate threshold
    transport            hanson | wu | vanRijn | mpm | partheniades
    collapse_mode        unsupported | all_pairs | bank_wedge
    sediment_face_flux   centred | hydro
    lateral_noncohesive  off | excess_shear
    hydrostatic_recon    audusse | chen_noelle

Note on headcut_gate, which is the distinction the architecture report flagged:
    scarp_percell  headcut_mode='scarp' + headcut_face_slope set -> _migrate_scarp_volume, which
                   requires EACH CELL of the face to be steeper than the threshold.
    scarp_cum      headcut_mode='scarp', face_slope unset -> _migrate_scarp, which gates on the
                   scarp's OVERALL slope against headcut_min_slope.
    cell           headcut_mode='cell' -> the V3.2.2 one-cell rule.
The as-built faces are 1:2.5 (slope 0.40) and 1:1 (1.00), so these three read the same geometry
very differently. Sweeping the threshold alongside the formula separates "the law is wrong" from
"the law never gets asked".

Each run is one case at one grid. Keep it to a fast case (Castlewood H/9 is ~1 min) while
exploring, then confirm on the slow one.

Writes runs/v34_law_sweep/*.json and a summary (also to --desktop). Resumable.

Usage (from the python folder):
    python -u calibration\\v34_law_sweep.py --case Castlewood --grid 9 --workers 6
    python -u calibration\\v34_law_sweep.py --case Castlewood --grid 9 --axes headcut_gate headcut_face_slope
    python -u calibration\\v34_law_sweep.py --case LaurelRun --grid 9 --grid2 12 --workers 6
    python -u calibration\\v34_law_sweep.py --list-axes
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
OUT = HERE.parent.parent / "runs" / "v34_law_sweep"
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}

# Factors the sweep runs at. The width defect is INVISIBLE at neutral factors (B looked fine at
# 44-59 m against an observed 54.9) and only appears at calibration scale, so the default here is
# cal-2's fitted point, where Castlewood's width blew out to 136.8 m on the F1-F7 engine.
CAL2_FIT = {"f_kd": 1.0, "C_h": 10.0, "f_t": 3.162}
NAMED_FACTORS = {
    "cal2":     CAL2_FIT,                                   # the current official factors
    "neutral":  dict(NEUTRAL),                              # f = 1, the old default
    "f14best":  {"f_kd": 1.0, "C_h": 1.0, "f_t": 31.62},    # F1-F4's Castlewood optimum
    "f567best": {"f_kd": 1.0, "C_h": 0.3162, "f_t": 10.0},  # F1-F7's Castlewood optimum
}
_FTAG = "cal2"          # factor tag the summary reads; main() sets it


def ftag_of(fac):
    return f"Ch{fac['C_h']:g}_ft{fac['f_t']:g}"
MAX_CPU_S = 5400.0

# Reference configuration the axes are swept around: the full F1-F7 set.
REFERENCE = {
    "hydrostatic_reconstruction": "chen_noelle",   # F1
    "headcut_overfall": "free",                    # F2
    "adaptation_dx_floor": False,                  # F3
    "collapse_to_repose": True,                    # F4
    "collapse_mode": "bank_wedge",                 # F5
    "sediment_face_flux": "hydro",                 # F6
    "headcut_face_slope": 1.0,                     # F7
}

# axis -> {option label: overrides merged onto REFERENCE}
AXES = {
    "headcut_method": {
        "energy": {"headcut_method": "energy"},
        "temple": {"headcut_method": "temple"},
        "sites": {"headcut_method": "sites"},
    },
    "headcut_gate": {
        "scarp_percell": {"headcut_mode": "scarp", "headcut_face_slope": 1.0},
        "scarp_cum": {"headcut_mode": "scarp", "headcut_face_slope": None},
        # the one-cell rule predates the overfall test, so drop 'free' with it
        "cell": {"headcut_mode": "cell", "headcut_face_slope": None, "headcut_overfall": "any"},
    },
    "headcut_min_slope": {
        f"min{v}": {"headcut_face_slope": None, "headcut_min_slope": v}
        for v in (0.3, 0.4, 0.5, 0.7)
    },
    "headcut_face_slope": {
        "off": {"headcut_face_slope": None},
        **{f"face{v}": {"headcut_face_slope": v} for v in (0.4, 0.6, 1.0)},
    },
    "transport": {
        n: {"transport": n} for n in ("hanson", "wu", "vanRijn", "mpm", "partheniades")
    },
    "collapse_mode": {
        n: {"collapse_mode": n} for n in ("unsupported", "all_pairs", "bank_wedge")
    },
    "sediment_face_flux": {
        n: {"sediment_face_flux": n} for n in ("centred", "hydro")
    },
    "lateral_noncohesive": {
        n: {"lateral_noncohesive": n} for n in ("off", "excess_shear")
    },
    "hydrostatic_reconstruction": {
        n: {"hydrostatic_reconstruction": n} for n in ("audusse", "chen_noelle")
    },
}


def opt_is_reference(axis: str, opt: str) -> bool:
    """True when this option reproduces REFERENCE exactly, so it is skipped as a duplicate."""
    return all(REFERENCE.get(k) == v for k, v in AXES[axis][opt].items())


def _case_json(case_id):
    try:
        return json.loads((HERE / "cases" / f"{case_id}.json").read_text())
    except Exception:
        return {}


def section_width(case_id):
    return float(_case_json(case_id).get("section_width", 0.0))


def detachment_on_noncohesive(case_id, axis, opt):
    """Partheniades / Hanson on a non-cohesive case run with MaterialProps defaults
    (kd = 1e-4, tau_c = 1 Pa, n = 1): the two laws are then algebraically identical and kd is a
    placeholder, not a measurement - the row says nothing about either law."""
    return (axis == "transport" and opt in ("hanson", "partheniades")
            and _case_json(case_id).get("material", {}).get("class") != "cohesive")


def overrides_for(axis: str, opt: str) -> dict:
    ov = dict(REFERENCE)
    ov.update(AXES[axis][opt])
    # a None face slope means "unset", not "pass None through"
    if ov.get("headcut_face_slope", "keep") is None:
        ov.pop("headcut_face_slope")
    return ov


def stem_for(case_id, gd, axis, opt, ftag=None):
    return f"{case_id}__H{gd}__{ftag or _FTAG}__{axis}__{opt}"


def worker(task):
    case_id, gd, axis, opt, factors, ftag = task
    path = OUT / f"{stem_for(case_id, gd, axis, opt, ftag)}.json"
    if path.exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    import breach_engine_2d_v3_2 as E
    try:
        ov = overrides_for(axis, opt)
        E.Headcut.event_log = []
        r = C.run(C.load_case(case_id), dict(factors), grid_divisor=float(gd), model="cal-2",
                  post_peak_stop=True, overrides=ov, max_cpu_seconds=MAX_CPU_S)
        out = {"id": case_id, "grid": gd, "axis": axis, "option": opt, "overrides": ov,
               "factors": dict(factors), "ftag": ftag,
               "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"], "B_eq": r.get("B_eq"),
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"],
               "censored": r["censored"], "cpu_s": r["cpu_s"],
               "max_balance": max(abs(x) for x in r["balances"])}
    except Exception as exc:
        out = {"id": case_id, "grid": gd, "axis": axis, "option": opt,
               "factors": dict(factors), "ftag": ftag, "error": repr(exc)}
    path.write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def load(case_id, gd, axis, opt, ftag=None):
    p = OUT / f"{stem_for(case_id, gd, axis, opt, ftag)}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def summary(case_id, grids, axes, obs=None):
    fac = NAMED_FACTORS.get(_FTAG) or {}
    facs = (f"C_h {fac.get('C_h'):g}, f_t {fac.get('f_t'):g}" if fac
            else f"tag {_FTAG}")
    rows = ["V3.4 law sweep: architecture fault or formula fault?",
            f"case {case_id}, grids {', '.join('H/' + str(g) for g in grids)}, cal-2 options.",
            f"FACTORS: {facs}   [{_FTAG}]",
            "Reference = F1-F7. Each row changes ONE option from that reference.",
            "B = 0 means the breach never opened. 'grid' column = Qp change between the two grids.",
            "",
            "*** OVER-WIDENING: compare the B column within each axis. Castlewood's observed  ***",
            "*** B is 54.9 m. On F1-F7 at cal-2's factors B reached 136.8 m; F1-F4 gave 94.7. ***",
            "*** RESULT (2026-11-19, Castlewood H/6 cal2): the HEADCUT machinery dominates.   ***",
            "*** Width span per axis: headcut_gate 91 m, headcut_method 88, face_slope 88,    ***",
            "*** min_slope 70, sediment_face_flux 60, transport 56, collapse_mode only 35,    ***",
            "*** lateral 3.5. An earlier note here named collapse_mode (F5) as the leading    ***",
            "*** suspect - that was WRONG. headcut_gate=cell gives B 45.6 (J 0.176), the only ***",
            "*** option in the sweep near the observation; every scarp gate gives 101-137.    ***",
            ""]
    opened_any = False
    for axis in axes:
        rows.append(f"--- {axis} " + "-" * (74 - len(axis)))
        head = f"  {'option':16s}"
        for g in grids:
            head += f" {'H/' + str(g) + ' Qp':>12s} {'B':>7s} {'B_eq':>7s}"
        if len(grids) > 1:
            head += f" {'grid':>8s}"
        rows.append(head + "   verdict")
        for opt in AXES[axis]:
            res = {g: load(case_id, g, axis, opt) for g in grids}
            line = f"  {opt:16s}"
            ok = True
            for g in grids:
                r = res[g]
                if r is None:
                    line += f" {'(reference)' if opt_is_reference(axis, opt) else '(not run)':>12s} {'':>7s} {'':>7s}"; ok = False
                elif "error" in r:
                    line += f" {'ERROR':>12s} {'':>7s} {'':>7s}"; ok = False
                else:
                    beq = r.get("B_eq")
                    line += f" {r['Qp']:12.1f} {r['B']:7.1f} " + (f"{beq:7.1f}" if beq is not None else f"{'-':>7s}")
                    if r["B"] > 0.5 and r["Qp"] > 1.0:
                        opened_any = True
            verdict = ""
            if ok and len(grids) > 1:
                a, b = res[grids[0]], res[grids[1]]
                if a["Qp"] > 0:
                    ch = b["Qp"] / a["Qp"] - 1
                    line += f" {ch * 100:+7.1f}%"
                    verdict = "converged" if abs(ch) < 0.10 else "NOT converged"
            elif ok:
                r = res[grids[0]]
                verdict = "breach opened" if (r["B"] > 0.5 and r["Qp"] > 1.0) else "NO BREACH"
                if detachment_on_noncohesive(case_id, axis, opt):
                    verdict += "  [INVALID: detachment law on non-cohesive, default kd; tau_c=1 Pa makes it = Hanson]"
                elif section_width(case_id) and r["B"] >= 0.99 * section_width(case_id):
                    verdict += "  [B = whole section width: saturated]"
            rows.append(line + f"   {verdict}")
        rows.append("")

    rows.append("=" * 88)
    rows.append("READING THIS")
    rows.append("=" * 88)
    if not opened_any:
        rows.append("  No option on any swept axis produced a breach. No single formula is at fault:")
        rows.append("  the fault is in the architecture - how the rules are composed and gated.")
    else:
        rows.append("  At least one option produced a breach, so the configuration space is not")
        rows.append("  uniformly dead. Compare rows WITHIN an axis: an axis where one option opens")
        rows.append("  the breach and the others do not has isolated the responsible law or gate.")
        rows.append("  An axis whose options all behave the same is not involved.")
    if obs:
        rows.append(f"  Observed Qp for {case_id}: {obs} m3/s - compare magnitudes, not just whether")
        rows.append("  the breach opened.")
    rows.append("")
    allr = [load(case_id, g, ax, o) for g in grids for ax in axes for o in AXES[ax]]
    allr = [r for r in allr if r]
    errs = [r for r in allr if "error" in r]
    rows.append(f"runs complete: {len(allr) - len(errs)} / {len(grids) * sum(len(AXES[a]) for a in axes)}")
    for r in errs:
        rows.append(f"ERROR {r['axis']}/{r['option']} H/{r['grid']}: {r['error'][:110]}")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default="Castlewood")
    ap.add_argument("--grid", type=int, default=9)
    ap.add_argument("--grid2", type=int, default=None,
                    help="second grid, to also test convergence of each option")
    ap.add_argument("--axes", nargs="+", default=None, help="subset of axes (default: all)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--desktop", default=None)
    ap.add_argument("--factors", default="cal2",
                    help="named set (" + " | ".join(NAMED_FACTORS) + ") or 'C_h,f_t' e.g. 1,31.62")
    ap.add_argument("--list-axes", action="store_true")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()

    if a.list_axes:
        print("Reference configuration (F1-F7):")
        for k, v in REFERENCE.items():
            print(f"    {k:30s} {v!r}")
        print("\nAxes and options:\n")
        for ax, opts in AXES.items():
            print(f"  {ax}")
            for o, ov in opts.items():
                print(f"      {o:16s} {ov}")
        return

    if a.factors in NAMED_FACTORS:
        factors, ftag = dict(NAMED_FACTORS[a.factors]), a.factors
    else:
        try:
            ch, ft = (float(x) for x in a.factors.replace(" ", "").split(","))
        except Exception:
            raise SystemExit(f"--factors must be one of {list(NAMED_FACTORS)} or 'C_h,f_t'")
        factors, ftag = {"f_kd": 1.0, "C_h": ch, "f_t": ft}, ftag_of({"C_h": ch, "f_t": ft})
    global _FTAG
    _FTAG = ftag

    axes = a.axes or list(AXES)
    bad = [x for x in axes if x not in AXES]
    if bad:
        raise SystemExit(f"unknown axis/axes: {bad}\nknown: {list(AXES)}")
    grids = [a.grid] + ([a.grid2] if a.grid2 else [])

    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [(a.case, g, ax, o, factors, ftag)
             for ax in axes for o in AXES[ax] for g in sorted(grids, reverse=True)]
    # de-duplicate options that resolve to the identical override set
    seen, uniq = {}, []
    for t in tasks:
        key = (t[0], t[1], json.dumps(overrides_for(t[2], t[3]), sort_keys=True, default=str))
        if key in seen:
            continue
        seen[key] = t
        uniq.append(t)
    todo = [t for t in uniq
            if not (OUT / f"{stem_for(t[0], t[1], t[2], t[3], t[5])}.json").exists()]

    obs = None
    try:
        sys.path.insert(0, str(HERE))
        import cases as C
        obs = C.load_case(a.case).get("obs", {}).get("Qp")
    except Exception:
        pass

    if not a.summary_only:
        print(f"V3.4 law sweep: {len(uniq)} unique runs ({len(tasks) - len(uniq)} duplicate configs "
              f"skipped), {len(todo)} to do, {a.workers} workers", flush=True)
        t0 = time.time()
        if todo:
            with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
                for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                    _c, g, ax, o, _f, _ft = task
                    print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} H/{g:<3d} {ax:26s} "
                          f"{o:16s} {status:5s} {wall / 60:6.1f} min   "
                          f"elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)

    text = summary(a.case, grids, axes, obs)
    print("\n" + text, flush=True)
    (OUT / f"SUMMARY_{a.case}_{ftag}.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop, f"v34_law_sweep_{a.case}_{ftag}_"
             f"{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
