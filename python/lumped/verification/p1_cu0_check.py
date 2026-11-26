"""ARS P1: sensitivity of the debris bounds to the roof strength c_u0 (decision 2026-11-26), before D1/D5
are frozen.

c_u0 = 4, 5, 6, 7 kPa (5 kPa is the estimated baseline: GeoHazards 2024 model input; P1 has no measured
c_u), rho = 0; k_d = 3.16 cm3/(N s) (central value of the 5.4a band); debris 'level' and 'instant'; every
case at dt = 2, 1, 0.5 s. Every other input unchanged (tau_c 0, n_p 0.016, exit headcut off).
Reported per run: crater start, pipe size at collapse, outcome, every wall failure with its exposed height
H_w and critical height H_c (5.17), and for runs that do not hand over, the final wall heights against
H_c; budgets. A not-a-fit check of how robust the two bounds are to an estimated input.

Usage (from the python folder):  python lumped/verification/p1_cu0_check.py [--workers N] [--dt 2,1,0.5]
Writes p1_cu0_check.txt next to this script.
"""
import argparse
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from lumped import roof                              # noqa: E402
from lumped.geometry import Dam                      # noqa: E402
from lumped.piping_run import PipingCase, PipingRun  # noqa: E402
from lumped.stability_table import StabilityTable    # noqa: E402

G = 9.81
RHO_D, GS, W = 1696.0, 2.65, 0.1149
N = 1 - RHO_D / (GS * 1000)
KD = 3.16e-6
_T = None


def run(args):
    global _T
    cu, mode, dt, t_end = args
    if _T is None:
        _T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    soil = roof.Soil(c_u0=cu * 1000.0, rho=0.0, gamma_sat=(RHO_D + N * 1000) * G, gamma_moist=RHO_D * (1 + W) * G)
    case = PipingCase(dam=Dam(1.3, 1.83, 3.0, 3.0, 100.0), soil=soil, kd=KD, tau_c=0.0, b0=0.04, D0=0.04,
                      z_inv0=0.2, z_s0=1.1, porosity=N, debris=mode)
    r = PipingRun(case, _T, dt=dt).run(t_end)
    ev = r.events
    cra = next((e for e in ev if e["type"] == "crater_start"), None)
    walls = [f"{e['type'][5:]} t={e['t']:.1f} H_w {e['H_w']:.3f} H_c {e['H_c']:.3f}"
             for e in ev if e["type"].startswith("wall_")]
    end_walls = ""
    if r.s.crater is not None and not (r.stopped and r.stopped[0] == "handover"):
        wm = r.wall_margins(r.s, r.s.crater.level())
        end_walls = "; ".join(f"{k} H_w {hw:.3f} H_c {m + hw:.3f}" for k, (m, hw) in wm.items())
    cr = r.s.crater
    stall = ""
    if r.stall:
        st = r.stall
        stall = f"stall at t={st['t']:.1f}: min margin {st['min_M']:.4f} kPa"
        if "x1" in st:
            stall += (f"; crater [{st['x1']:.4f}, {st['x2']:.4f}] W {st['W']:.3f} z_d {st['z_d']:.3f} z_c {st['z_c']:.3f}; "
                      + "; ".join(f"{k} H_w {hw:.3f} H_c {hc:.3f}" for k, (hc, hw) in st["walls"].items()))
            for key in ("rc_up", "rc_dn"):
                if key in st:
                    q = st[key]
                    stall += (f"; {key} weakest section x {q['x']:.4f} M_c {q['M_c']:.4f} (neighbours "
                              + ", ".join(f"{x:.4f}:{m:.3f}" for x, m in q["neighbours"]) + ")")
    state = ""
    if cr is not None:
        h = r.hyd(r.s)
        zr1, zr2 = case.dam.z_dam(cr.x1), case.dam.z_dam(cr.x2)
        state = (f"z_s {r.s.z_s:.3f}, crater water {h['z_c']:.3f}, rim up {zr1:.3f} / down {zr2:.3f} m; Q_res "
                 f"{h['Q_res'] * 1e3:.3f} L/s, Q_out {h['Q_out_cr'] * 1e3:.3f}, spill {h['Q_spill'] * 1e3:.3f}; "
                 f"a_open {cr.a_open():.3f} m; upstream pipe b {r.s.pipe.b:.3f} D {r.s.pipe.D:.3f} vs crater W "
                 f"{cr.W:.3f} a_p {cr.a_p:.3f}")
    kinds = {}
    for e in ev:
        kinds[e["type"]] = kinds.get(e["type"], 0) + 1
    counts = ", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
    return dict(state=state, counts=counts, stall=stall, cu=cu, mode=mode, dt=dt, t_crater=cra["t"] if cra else None, b=cra["b"] if cra else None,
                outcome=r.stopped[0] if r.stopped else "running at t_end", why=r.stopped[1] if r.stopped else "",
                walls=walls, end_walls=end_walls, water=r.max_water_err, solids=r.max_solids_err,
                t_end=r.s.t, geom=("no crater" if cr is None else f"crater [{cr.x1:.2f}, {cr.x2:.2f}] W {cr.W:.2f} z_d {cr.z_d:.3f}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default="2,1,0.5")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--t_end", type=float, default=4 * 3600.0)
    a = ap.parse_args()
    dts = [float(v) for v in a.dt.split(",")]
    tasks = [(cu, m, dt, a.t_end) for cu in (4, 5, 6, 7) for m in ("level", "instant") for dt in dts]
    tasks.sort(key=lambda t: t[2])
    workers = a.workers or max(1, min((os.cpu_count() or 2) - 1, 8, len(tasks)))
    t0 = time.time()
    print(f"{len(tasks)} runs on {workers} workers", flush=True)
    res = {}
    with Pool(workers, maxtasksperchild=4) as pool:
        for k, r in enumerate(pool.imap_unordered(run, tasks), 1):
            res[(r["cu"], r["mode"], r["dt"])] = r
            print(f"  [{k:2d}/{len(tasks)}] c_u0 {r['cu']} kPa {r['mode']:7s} dt {r['dt']:g}: crater "
                  f"{r['t_crater']} s, {r['outcome']} ({time.time() - t0:.0f} s)", flush=True)
    L = [f"ARS P1 c_u0 sensitivity of the debris bounds; k_d {KD * 1e6:g} cm3/(N s); time steps {dts} s; "
         f"other inputs unchanged", "dry-wall critical height (5.17) H_c = 3.776 c_u0 / gamma_bar", ""]
    for cu in (4, 5, 6, 7):
        for m in ("level", "instant"):
            rr = [res[(cu, m, dt)] for dt in dts]
            outs = {r["outcome"] for r in rr}
            tc = ", ".join("-" if r["t_crater"] is None else f"{r['t_crater']:.1f}" for r in rr)
            f = rr[-1]
            bstr = "-" if f["b"] is None else f"{f['b']:.3f} m"
            L.append(f"c_u0 {cu} kPa | {m:7s} | crater start {tc} s | pipe at collapse "
                     f"{bstr} | outcome {'same' if len(outs) == 1 else 'DIFFERS'}: "
                     f"{', '.join(sorted(outs))} {('(' + f['why'] + ')') if f['why'] else ''}")
            L.append(f"    end ({'dt ' + format(dts[-1], 'g')}, t {f['t_end']:.0f} s): {f['geom']}")
            if f["state"]:
                L.append(f"    end state: {f['state']}")
            L.append(f"    events: {f['counts']}")
            nw = [len(r["walls"]) for r in rr]
            L.append(f"    wall failures per dt {nw}" + ("" if f["walls"] else ": none"))
            for w in f["walls"]:
                L.append(f"      {w}")
            if f["stall"]:
                L.append(f"    {f['stall']}")
            if f["end_walls"]:
                L.append(f"    final walls (stand): {f['end_walls']}")
    water = max(r["water"] for r in res.values()); solids = max(r["solids"] for r in res.values())
    L.append(f"\nwall time {time.time() - t0:.0f} s on {workers} workers; largest water-budget error {water:.1e}, "
             f"solids {solids:.1e}")
    text = "\n".join(L)
    print("\n" + text)
    (HERE / "p1_cu0_check.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
