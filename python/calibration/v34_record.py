"""V3.4 run recorder: run any case / grid / fix-set and record everything the viewer needs.

This generalises calibration/v34_diag_laurel.py (which was Laurel-Run-only and recorded two profile
lines) so that:
  * any case and grid divisor can be recorded, including the F7 configurations that the existing
    recordings do not cover;
  * the FULL 2-D bed and depth are stored at intervals, so the viewer's plan view animates instead
    of only being complete on the final frame;
  * the headcut gate log is always on, so every frame can say WHY the headcut did or did not act.

It records, per sample (SAMPLE_S of model time):
    t, Q, lake level, bed+depth along the crest line, bed+depth along the breach axis,
    cumulative volume moved by transport / headcut / lateral / collapse
and per field sample (FIELD_EVERY samples): the whole z_b and h.

Outputs runs/v34_record/<case>__H<grid>__<variant>.npz  (+ __headcut.json, __events.json, .json)
in the schema calibration/v34_view.py reads.

Variants are the same ladder as v34_isolation_f567.py, so a recording can be lined up against an
isolation result.

Usage (from the python folder):
    python -u calibration\\v34_record.py --case Castlewood --grids 9 --variants base f567
    python -u calibration\\v34_record.py --case LaurelRun --grids 9 12 --variants f56 f567 --workers 4
    python -u calibration\\v34_record.py --list-variants
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
OUT = HERE.parent.parent / "runs" / "v34_record"

SAMPLE_S = 20.0        # model seconds between line samples
FIELD_EVERY = 5        # store the full 2-D bed every Nth line sample
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}
SRC = ("transport_net_erosion_m3", "headcut_m3", "lateral_m3", "collapsed_m3")
MAX_CPU_S = 7200.0

BASE = {
    "hydrostatic_reconstruction": "chen_noelle",   # F1
    "headcut_overfall": "free",                    # F2
    "adaptation_dx_floor": False,                  # F3
    "collapse_to_repose": True,                    # F4
}
F5 = {"collapse_mode": "bank_wedge"}
F6 = {"sediment_face_flux": "hydro"}
F7 = {"headcut_face_slope": 1.0}

VARIANTS = {
    "cal2":  None,                                  # cal-2 only, no F-fixes at all
    "base":  {},                                    # F1-F4
    "f5":    {**F5},
    "f56":   {**F5, **F6},
    "f567":  {**F5, **F6, **F7},
    "no_f5": {**F6, **F7},
    "no_f6": {**F5, **F7},
    "f7only": {**F7},                               # F1-F4 + F7, to see F7 on its own
    "noheadcut": {"headcut_enabled": False},
    "nocollapse": {"bank_collapse_enabled": False},
}


def overrides_for(var: str) -> dict:
    v = VARIANTS[var]
    if v is None:
        return {}
    ov = dict(BASE)
    ov.update(v)
    return ov


def worker(task):
    case_id, gd, var = task
    stem = f"{case_id}__H{gd}__{var}"
    if (OUT / f"{stem}.json").exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import numpy as np
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    import breach_engine_2d_v3_2 as E

    kept = {"next": 0.0, "cum": np.zeros(len(SRC)), "Q": 0.0, "WL": float("nan"), "n": 0}
    rec = {k: [] for k in ("t", "Q", "WL", "xz", "xh", "lz", "lh", "cum", "ft", "fz", "fh")}
    E.BankStability.event_log = []
    E.Headcut.event_log = []
    _init, _step = E.UltimateBreachEngine.__init__, E.Morphology.step

    def init(self, *a, **k):
        _init(self, *a, **k)
        kept["eng"] = self
        z0 = self._initial_bed
        kept["ic"] = int(np.argmax(z0.max(axis=1)))       # crest line
        kept["jc"] = int(np.argmin(z0[kept["ic"]]))       # breach axis (pilot notch)
        E.Headcut.watch = kept["jc"]

    def sample(eng, mesh):
        if eng.history:
            kept["Q"] = float(eng.history[-1]["Q_prism_outlet"])
            kept["WL"] = float(eng.history[-1]["WL_res"])
        ic, jc = kept["ic"], kept["jc"]
        rec["t"].append(eng.time); rec["Q"].append(kept["Q"]); rec["WL"].append(kept["WL"])
        rec["xz"].append(mesh.z_b[ic].copy()); rec["xh"].append(mesh.h[ic].copy())
        rec["lz"].append(mesh.z_b[:, jc].copy()); rec["lh"].append(mesh.h[:, jc].copy())
        rec["cum"].append(kept["cum"].copy())
        if kept["n"] % FIELD_EVERY == 0:                  # full 2-D field, less often
            rec["ft"].append(eng.time)
            rec["fz"].append(mesh.z_b.astype(np.float32).copy())
            rec["fh"].append(mesh.h.astype(np.float32).copy())
        kept["n"] += 1

    def step(self, mesh, *a, **k):
        eng = kept.get("eng")
        if eng is not None:
            E.BankStability.now = E.Headcut.now = eng.time
            E.Headcut.log_now = bool(eng.time >= kept["next"])
        out = _step(self, mesh, *a, **k)
        kept["cum"] += [float(out.get(s, 0.0)) for s in SRC]
        if eng is not None and eng.time >= kept["next"]:
            kept["next"] = eng.time + SAMPLE_S
            sample(eng, mesh)
        return out

    E.UltimateBreachEngine.__init__, E.Morphology.step = init, step
    try:
        ov = overrides_for(var)
        r = C.run(C.load_case(case_id), dict(NEUTRAL), grid_divisor=float(gd), model="cal-2",
                  post_peak_stop=True, overrides=ov, max_cpu_seconds=MAX_CPU_S)
        eng = kept["eng"]
        sample(eng, eng.mesh)
        np.savez_compressed(
            OUT / f"{stem}.npz",
            t=np.array(rec["t"]), Q=np.array(rec["Q"]), WL=np.array(rec["WL"]),
            xsec_z=np.array(rec["xz"]), xsec_h=np.array(rec["xh"]),
            long_z=np.array(rec["lz"]), long_h=np.array(rec["lh"]),
            cum=np.array(rec["cum"]),
            field_t=np.array(rec["ft"]), field_z=np.array(rec["fz"]), field_h=np.array(rec["fh"]),
            z0=eng._initial_bed, z_end=eng.mesh.z_b, h_end=eng.mesh.h,
            dx=eng.mesh.dx, dy=eng.mesh.dy, ic=kept["ic"], jc=kept["jc"])
        (OUT / f"{stem}__events.json").write_text(json.dumps(E.BankStability.event_log))
        (OUT / f"{stem}__headcut.json").write_text(json.dumps(E.Headcut.event_log))
        out = {"id": case_id, "grid": gd, "variant": var, "overrides": ov,
               "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"],
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"],
               "censored": r["censored"], "cpu_s": r["cpu_s"],
               "max_balance": max(abs(x) for x in r["balances"]),
               "samples": len(rec["t"]), "fields": len(rec["ft"]),
               "collapse": dict(E.BankStability.stats),
               "headcut_logged": len(E.Headcut.event_log),
               "headcut_active": sum(1 for e in E.Headcut.event_log if e.get("active"))}
    except Exception as exc:
        import traceback
        out = {"id": case_id, "grid": gd, "variant": var, "error": repr(exc),
               "trace": traceback.format_exc()}
    (OUT / f"{stem}.json").write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def summary(tasks):
    rows = ["V3.4 recordings", f"{'run':38s} {'Qp':>9s} {'B':>7s} {'frames':>7s} {'fields':>7s} "
                               f"{'scarps':>7s} {'active':>7s}  stop"]
    for case_id, gd, var in tasks:
        p = OUT / f"{case_id}__H{gd}__{var}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text())
        name = f"{case_id}__H{gd}__{var}"
        if "error" in r:
            rows.append(f"{name:38s} ERROR {r['error'][:70]}")
            continue
        rows.append(f"{name:38s} {r['Qp']:9.1f} {r['B']:7.1f} {r['samples']:7d} {r['fields']:7d} "
                    f"{r['headcut_logged']:7d} {r['headcut_active']:7d}  {r['stop_cause']}")
    rows.append("")
    rows.append("View with:")
    for case_id, gd, var in tasks[:3]:
        rows.append(f"  python -u calibration/v34_view.py --run {case_id}__H{gd}__{var}")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", nargs="+", default=["Castlewood"])
    ap.add_argument("--grids", nargs="+", type=int, default=[9])
    ap.add_argument("--variants", nargs="+", default=["base", "f567"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--desktop", default=None)
    ap.add_argument("--list-variants", action="store_true")
    a = ap.parse_args()

    if a.list_variants:
        print("variants (all include cal-2 options and neutral factors):\n")
        for v in VARIANTS:
            ov = overrides_for(v)
            print(f"  {v:11s} {ov if ov else '(cal-2 only)'}")
        return

    bad = [v for v in a.variants if v not in VARIANTS]
    if bad:
        raise SystemExit(f"unknown variant(s): {bad}\nknown: {list(VARIANTS)}")

    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [(c, g, v) for v in a.variants for g in sorted(a.grids, reverse=True) for c in a.case]
    todo = [t for t in tasks if not (OUT / f"{t[0]}__H{t[1]}__{t[2]}.json").exists()]
    print(f"V3.4 recorder: {len(tasks)} runs, {len(todo)} to do, {a.workers} workers, "
          f"sample {SAMPLE_S:.0f}s, full field every {FIELD_EVERY} samples", flush=True)
    t0 = time.time()
    if todo:
        with mp.get_context("spawn").Pool(a.workers, maxtasksperchild=1) as pool:
            for i, (task, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                c, g, v = task
                print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} {c:11s} H/{g:<3d} {v:9s} "
                      f"{status:5s} {wall / 60:6.1f} min   "
                      f"elapsed {(time.time() - t0) / 60:6.1f} min", flush=True)
    text = summary(tasks)
    print("\n" + text, flush=True)
    (OUT / "SUMMARY.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop, f"v34_record_summary_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
