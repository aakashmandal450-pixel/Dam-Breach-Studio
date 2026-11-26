"""ARS P1 validation band with the frozen debris rules (5.7b, 2026-11-26): level deposit with D5 (both
mouths obstructed) and D1-a (plug breakthrough at the critical gradient, 5.26), across the 5.4a k_d band,
exit headcut off and on, dt = 2, 1, 0.5 s. c_u0 = 5 kPa (estimate), rho = 0, tau_c = 0, n_p = 0.016,
n_d = n, c_d = 0. A validation run, not a fit: nothing is adjusted to the observation.

Reported per run: crater start, every plug event with i against i_cr, the final plug margins, outcome,
end state and budgets.
Usage (from the python folder):  python lumped/verification/p1_plugs_band.py [--workers N] [--dt 2,1,0.5]
Writes p1_plugs_band.txt next to this script.
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
KD_BAND = (16.5, 6.77, 3.16, 1.48, 0.88)      # cm3/(N s), 5.4a
_T = None


def run(args):
    global _T
    kd, hc, dt, t_end = args
    if _T is None:
        _T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    soil = roof.Soil(c_u0=5000.0, rho=0.0, gamma_sat=(RHO_D + N * 1000) * G, gamma_moist=RHO_D * (1 + W) * G)
    case = PipingCase(dam=Dam(1.3, 1.83, 3.0, 3.0, 100.0), soil=soil, kd=kd * 1e-6, tau_c=0.0, b0=0.04,
                      D0=0.04, z_inv0=0.2, z_s0=1.1, porosity=N, debris="level", plugs=True, exit_headcut=hc)
    r = PipingRun(case, _T, dt=dt).run(t_end)
    ev = r.events
    cra = next((e for e in ev if e["type"] == "crater_start"), None)
    plugs = []
    for e in ev:
        if e["type"].startswith("plug_"):
            if e["type"].endswith("_fail"):
                plugs.append(f"{e['type']} t={e['t']:.1f} i {e['i']:.3f} / i_cr {e['i_cr']:.3f} (dh {e['dh']:.3f}, "
                             f"l {e['ell']:.3f}) V_plug {e['V_plug']:.4f} m3")
            else:
                plugs.append(f"{e['type']} t={e['t']:.1f} z_d {e['z_d']:.3f}")
    cr, final = r.s.crater, ""
    if cr is not None:
        h = r.hyd(r.s)
        m = r.plug_margins(r.s, h["z_c"]) if not (r.stopped and r.stopped[0] == "handover") else {}
        final = "; ".join(f"{k}: i {d['i']:.3f} / i_cr {d['i_cr']:.3f}" for k, d in m.items())
        state = (f"crater [{cr.x1:.2f}, {cr.x2:.2f}] W {cr.W:.3f} z_d {cr.z_d:.3f} z_c {h['z_c']:.3f}; mouths up "
                 f"{'open' if cr.open_up else 'as deposit'}, down {'open' if cr.open_dn else 'as deposit'}; "
                 f"Q_res {h['Q_res'] * 1e3:.2f} L/s, Q_out {h['Q_out_cr'] * 1e3:.2f}, spill {h['Q_spill'] * 1e3:.2f}; "
                 f"V_exp {cr.V_exp:.4f} out {cr.V_exp_out:.4f} m3")
    else:
        state = "no crater"
    out = r.stopped[0] if r.stopped else ("crater_spilling, still evolving at t_end" if r._spilling else "running at t_end")
    return dict(kd=kd, hc=hc, dt=dt, t_crater=cra["t"] if cra else None, outcome=out,
                why=r.stopped[1] if r.stopped else "", plugs=plugs, final=final, state=state, t=r.s.t,
                water=r.max_water_err, solids=r.max_solids_err)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default="2,1,0.5")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--t_end", type=float, default=7200.0)
    a = ap.parse_args()
    dts = [float(v) for v in a.dt.split(",")]
    tasks = [(kd, hc, dt, a.t_end) for kd in KD_BAND for hc in (False, True) for dt in dts]
    tasks.sort(key=lambda t: (t[2], -t[0]))
    workers = a.workers or max(1, min((os.cpu_count() or 2) - 1, 8, len(tasks)))
    t0 = time.time()
    print(f"{len(tasks)} runs on {workers} workers", flush=True)
    res = {}
    with Pool(workers, maxtasksperchild=4) as pool:
        for k, r in enumerate(pool.imap_unordered(run, tasks), 1):
            res[(r["kd"], r["hc"], r["dt"])] = r
            print(f"  [{k:2d}/{len(tasks)}] k_d {r['kd']} headcut {'on' if r['hc'] else 'off'} dt {r['dt']:g}: "
                  f"crater {r['t_crater']} s, {r['outcome']} ({time.time() - t0:.0f} s)", flush=True)
    L = [f"ARS P1 validation band, frozen debris rules 5.7b (level + D5 + D1-a); c_u0 5 kPa; time steps {dts} s", ""]
    for kd in KD_BAND:
        for hc in (False, True):
            rr = [res[(kd, hc, dt)] for dt in dts]
            outs = {r["outcome"] for r in rr}
            tc = ", ".join("-" if r["t_crater"] is None else f"{r['t_crater']:.1f}" for r in rr)
            f = rr[-1]
            L.append(f"k_d {kd:5.2f} | headcut {'on ' if hc else 'off'} | crater start {tc} s | outcome "
                     f"{'same' if len(outs) == 1 else 'DIFFERS'}: {', '.join(sorted(outs))} "
                     f"{('(' + f['why'] + ')') if f['why'] else ''}")
            L.append(f"    end (dt {dts[-1]:g}, t {f['t']:.0f} s): {f['state']}")
            L.append(f"    plug events per dt {[len(r['plugs']) for r in rr]}")
            for p in f["plugs"]:
                L.append(f"      {p}")
            if f["final"]:
                L.append(f"    final plugs: {f['final']}")
    water = max(r["water"] for r in res.values()); solids = max(r["solids"] for r in res.values())
    L.append(f"\nwall time {time.time() - t0:.0f} s on {workers} workers; largest water-budget error {water:.1e}, "
             f"solids {solids:.1e}")
    text = "\n".join(L)
    print("\n" + text)
    (HERE / "p1_plugs_band.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
