"""V3.4 diagnostic run (seen case): where do the H/9 and H/12 runs of Laurel Run part?

Laurel Run, neutral factors (f = 1), cal-2 options + F1-F4, grid divisors H/9 and H/12, three variants:
    nocollapse  bank collapse switched off (peaks agree between the grids: 389 / 391 m3/s)
    pairs       F1-F4, Culmann on cell pairs (401 / 512 m3/s)
    wedge       F1-F5, Culmann on whole banks (297 / 438 m3/s)
and the same three with F6 (sediment moved with the flow solver's face water flux): nocollapse_f6, pairs_f6, wedge_f6.
Every SAMPLE_S seconds of model time each run records the outflow, the lake level, the bed and the depth along the
crest line and along the breach axis, and the volumes moved by each process. Every whole-bank failure is recorded
with its time, place, height, number of drops, angle and factor of safety (wedge variant).
Writes runs/v34_diag_laurel/<run>.npz, <run>.json, <run>__events.json and SUMMARY.txt (also to --desktop).

Usage (from the python folder):  python -u calibration\\v34_diag_laurel.py --workers 5 --desktop <folder>
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
OUT = HERE.parent.parent / "runs" / "v34_diag_laurel"
CASE = "LaurelRun"
GRIDS = (9, 12)
SAMPLE_S = 20.0
F1234 = {"hydrostatic_reconstruction": "chen_noelle", "headcut_overfall": "free", "adaptation_dx_floor": False,
         "collapse_to_repose": True}
VARIANTS = {
    "nocollapse": {"bank_collapse_enabled": False},
    "pairs": {},
    "wedge": {"collapse_mode": "bank_wedge"},
    "nocollapse_f6": {"bank_collapse_enabled": False, "sediment_face_flux": "hydro"},
    "pairs_f6": {"sediment_face_flux": "hydro"},
    "wedge_f6": {"collapse_mode": "bank_wedge", "sediment_face_flux": "hydro"},
}
NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}
SRC = ("transport_net_erosion_m3", "headcut_m3", "lateral_m3", "collapsed_m3")
T_TABLE = (300, 600, 900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3600, 4200)


def worker(task):
    gd, var = task
    stem = f"{CASE}__H{gd}__{var}"
    if (OUT / f"{stem}.json").exists():
        return task, "skip", 0.0
    t0 = time.time()
    sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
    import numpy as np
    import fast_hydro
    fast_hydro.enable()
    import cases as C
    import breach_engine_2d_v3_2 as E
    kept = {"next": 0.0, "cum": np.zeros(len(SRC)), "Q": 0.0, "WL": float("nan")}
    rec = {k: [] for k in ("t", "Q", "WL", "xz", "xh", "lz", "lh", "cum")}
    E.BankStability.event_log = []
    _init, _step = E.UltimateBreachEngine.__init__, E.Morphology.step

    def init(self, *a, **k):
        _init(self, *a, **k)
        kept["eng"] = self
        z0 = self._initial_bed
        kept["ic"] = int(np.argmax(z0.max(axis=1)))           # crest line (row of the highest bed)
        kept["jc"] = int(np.argmin(z0[kept["ic"]]))           # breach axis (column of the pilot notch)

    def sample(eng, mesh):
        if eng.history:
            kept["Q"], kept["WL"] = float(eng.history[-1]["Q_prism_outlet"]), float(eng.history[-1]["WL_res"])
        ic, jc = kept["ic"], kept["jc"]
        rec["t"].append(eng.time); rec["Q"].append(kept["Q"]); rec["WL"].append(kept["WL"])
        rec["xz"].append(mesh.z_b[ic].copy()); rec["xh"].append(mesh.h[ic].copy())
        rec["lz"].append(mesh.z_b[:, jc].copy()); rec["lh"].append(mesh.h[:, jc].copy())
        rec["cum"].append(kept["cum"].copy())

    def step(self, mesh, *a, **k):
        eng = kept.get("eng")
        if eng is not None:
            E.BankStability.now = eng.time
        out = _step(self, mesh, *a, **k)
        kept["cum"] += [float(out.get(s, 0.0)) for s in SRC]
        if eng is not None and eng.time >= kept["next"]:
            kept["next"] = eng.time + SAMPLE_S
            sample(eng, mesh)
        return out

    E.UltimateBreachEngine.__init__, E.Morphology.step = init, step
    try:
        ov = dict(F1234); ov.update(VARIANTS[var])
        r = C.run(C.load_case(CASE), dict(NEUTRAL), grid_divisor=float(gd), model="cal-2", post_peak_stop=True,
                  overrides=ov, max_cpu_seconds=4 * 3600.0)
        eng = kept["eng"]
        sample(eng, eng.mesh)
        np.savez_compressed(OUT / f"{stem}.npz", t=np.array(rec["t"]), Q=np.array(rec["Q"]), WL=np.array(rec["WL"]),
                            xsec_z=np.array(rec["xz"]), xsec_h=np.array(rec["xh"]), long_z=np.array(rec["lz"]),
                            long_h=np.array(rec["lh"]), cum=np.array(rec["cum"]), z0=eng._initial_bed,
                            z_end=eng.mesh.z_b, h_end=eng.mesh.h, dx=eng.mesh.dx, dy=eng.mesh.dy,
                            ic=kept["ic"], jc=kept["jc"])
        (OUT / f"{stem}__events.json").write_text(json.dumps(E.BankStability.event_log))
        out = {"id": CASE, "grid": gd, "variant": var, "Qp": r["Qp"], "Tp_h": r["Tp_h"], "B": r["B"],
               "max_lowering_m": r["max_lowering_m"], "stop_cause": r["stop_cause"], "censored": r["censored"],
               "cpu_s": r["cpu_s"], "max_balance": max(abs(x) for x in r["balances"]), "cells": r["grid"],
               "collapse": dict(E.BankStability.stats), "samples": len(rec["t"]), "events": len(E.BankStability.event_log)}
    except Exception as exc:
        import traceback
        out = {"id": CASE, "grid": gd, "variant": var, "error": repr(exc), "trace": traceback.format_exc()}
    (OUT / f"{stem}.json").write_text(json.dumps(out, indent=1))
    return task, ("error" if "error" in out else "ok"), time.time() - t0


def xsec_stats(z0row, zrow, dy):
    """Crest line: deepest lowering, channel width at half of it, sheet lowering (median over the crest)."""
    import numpy as np
    low = np.maximum(z0row - zrow, 0.0)
    mx = float(low.max())
    w = float(np.count_nonzero(low >= 0.5 * mx) * dy) if mx > 0.05 else 0.0
    return mx, w, float(np.median(low))


def summary():
    import numpy as np
    rows = [f"V3.4 diagnostic run: {CASE}, neutral factors; model time in s",
            "variant        grid      Qp    Tp[h]   B[m]   samples  bank failures   highest rise[m]  cells risen >3 m  "
            "risen volume[m3]"]
    data = {}
    for var in VARIANTS:
        for g in GRIDS:
            pj, pn = OUT / f"{CASE}__H{g}__{var}.json", OUT / f"{CASE}__H{g}__{var}.npz"
            if not pj.exists():
                rows.append(f"{var:14s} H/{g:<4d} (not run)")
                continue
            r = json.loads(pj.read_text())
            if "error" in r:
                rows.append(f"{var:14s} H/{g:<4d} ERROR {r['error']}")
                continue
            data[(var, g)] = d = np.load(pn)
            rise = d["z_end"] - d["z0"]
            rows.append(f"{var:14s} H/{g:<4d} {r['Qp']:7.0f} {r['Tp_h']:7.2f} {r['B']:6.0f} {r['samples']:8d} {r['events']:8d} "
                        f"{float(rise.max()):17.2f} {int((rise > 3).sum()):17d} "
                        f"{float(rise[rise > 0].sum()) * float(d['dx']) * float(d['dy']):17.0f}")
    for var in VARIANTS:
        if not all((var, g) in data for g in GRIDS):
            continue
        rows.append("")
        rows.append(f"--- {var}: H/9 | H/12 at the same model time ---")
        rows.append("   t[s]     Q[m3/s]        lake[m]      deepest cut[m]   width at half[m]   crest sheet[m]"
                    "    eroded bed[m3]    headcut[m3]    lateral[m3]    collapse[m3]")
        for tt in T_TABLE:
            cells = []
            ok = True
            vals = []
            for g in GRIDS:
                d = data[(var, g)]
                if tt > d["t"][-1]:
                    ok = False
                    break
                k = int(np.searchsorted(d["t"], tt))
                k = min(k, len(d["t"]) - 1)
                mx, w, sh = xsec_stats(d["z0"][int(d["ic"])], d["xsec_z"][k], float(d["dy"]))
                vals.append((d["Q"][k], d["WL"][k], mx, w, sh, *d["cum"][k]))
            if not ok:
                continue
            a, b = vals
            fm = ("{:6.0f}|{:<6.0f}", "{:6.2f}|{:<6.2f}", "{:6.2f}|{:<6.2f}", "{:6.1f}|{:<6.1f}", "{:6.2f}|{:<6.2f}",
                  "{:7.0f}|{:<7.0f}", "{:6.0f}|{:<6.0f}", "{:6.0f}|{:<6.0f}", "{:6.0f}|{:<6.0f}")
            rows.append(f"{tt:7d}   " + "   ".join(f.format(x, y) for f, x, y in zip(fm, a, b)))
    for wv, g in [(w, g) for w in ("wedge", "wedge_f6") for g in GRIDS]:
        pe = OUT / f"{CASE}__H{g}__{wv}__events.json"
        if not pe.exists():
            continue
        ev = json.loads(pe.read_text())
        rows.append("")
        rows.append(f"--- {wv}, H/{g}: {len(ev)} bank failures; the first 15 (dir 0/1 = bank drops toward +x/-x, 2/3 = +y/-y) ---")
        rows.append("   t[s]  dir  line  drops    H[m]  angle[deg]    FS   depth at toe[m]  volume[m3]")
        for e in ev[:15]:
            rows.append(f"{e['t']:7.0f} {e['dir']:4d} {e['line']:5d} {e['drops']:6d} {e['H']:7.2f} {e['beta_deg']:10.1f} "
                        f"{e['FS']:6.2f} {e['h_foot']:12.2f} {e['volume_m3']:11.1f}")
        if ev:
            H = np.array([e["H"] for e in ev]); n = np.array([e["drops"] for e in ev])
            rows.append(f"   all failures: height median {np.median(H):.2f} m (min {H.min():.2f}, max {H.max():.2f}); "
                        f"single-step banks {np.mean(n == 1) * 100:.0f} %, two drops {np.mean(n == 2) * 100:.0f} %, "
                        f"three or more {np.mean(n >= 3) * 100:.0f} %; by direction "
                        + ", ".join(f"{k}: {int(np.sum(np.array([e['dir'] for e in ev]) == k))}" for k in range(4)))
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--desktop", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = [(g, v) for g in sorted(GRIDS, reverse=True) for v in VARIANTS]
    todo = [t for t in tasks if not (OUT / f"{CASE}__H{t[0]}__{t[1]}.json").exists()]
    print(f"V3.4 diagnostic run: {len(tasks)} runs, {len(todo)} to do, {a.workers} workers", flush=True)
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
        Path(a.desktop, f"v34_diag_laurel_summary_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")
    bad = [t for t in tasks if "error" in json.loads((OUT / f"{CASE}__H{t[0]}__{t[1]}.json").read_text())]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
