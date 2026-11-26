"""ARS P1: the four debris comparison treatments of theory 5.7 across the 5.4a k_d band (decision 2026-11-26).

Treatments (the crater framework of 5.7a; see the reply/notes for the mapping to 5.7):
  level    level deposit over the crater footprint (5.18-5.20) - the localised deposit at x* of 5.7 (baseline)
  instant  instant removal: fallen soil leaves the model domain at once
  tank     DL Breach virtual tank (Wu 2016, 4.7): removed from the crater and stored; the flow's erosion
           capacity empties the tank before any wall erosion resumes (geometry frozen meanwhile)
  The fourth 5.7 treatment, a uniform layer along the whole pipe (5.12b), needs a rule for debris inside the
  pipe reaches and is not run until that rule is decided.
Inputs as the baseline otherwise (tau_c 0, n_p 0.016, exit headcut off); every case at three time steps.
Reported: crater start, hand-over, outcome, crater-level range after the crater starts, downstream reopening
time, final crater and pipe geometry, debris exported / in the tank, pipe-stage peak outflow, budgets.
Hand-over ends the run (stage 4 not implemented), so no post-hand-over breach peak exists yet.

Usage (from the python folder):
    python lumped/verification/p1_debris_modes.py [--dt 2,1,0.5] [--workers N] [--modes level,instant,tank]
Writes p1_debris_modes.txt next to this script.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from lumped import piping as pp                    # noqa: E402
from lumped import roof                             # noqa: E402
from lumped.geometry import Dam                     # noqa: E402
from lumped.piping_run import PipingCase, PipingRun  # noqa: E402
from lumped.stability_table import StabilityTable   # noqa: E402

G = 9.81
RHO_D, GS, W = 1696.0, 2.65, 0.1149
N = 1 - RHO_D / (GS * 1000)
SOIL = roof.Soil(c_u0=5000.0, rho=0.0, gamma_sat=(RHO_D + N * 1000) * G, gamma_moist=RHO_D * (1 + W) * G)
BASE = dict(kd=150e-6, tau_c=0.0, n_p=0.016, exit_headcut=False, debris="level")


def run(T, dt=1.0, t_end=3600.0, **kw):
    p = {**BASE, **kw}
    case = PipingCase(dam=Dam(1.3, 1.83, 3.0, 3.0, 100.0), soil=SOIL, kd=p["kd"], tau_c=p["tau_c"], b0=0.04,
                      D0=0.04, z_inv0=0.2, z_s0=1.1, porosity=N, n_p=p["n_p"],
                      exit_headcut=p.get("exit_headcut", False), debris=p.get("debris", "level"))
    fl0 = pp.pipe_flow(1.1 - 0.2, 0.04, 0.04, Dam(1.3, 1.83, 3.0, 3.0, 100.0).x_down(0.22) - 0.66, p["n_p"])
    r = PipingRun(case, T, dt=dt, record_every=dt).run(t_end)
    ev = r.events
    first = lambda k: next((e for e in ev if e["type"] == k), None)
    inl, cra = first("inlet_retreat"), first("crater_start")
    ho = first("handover")
    hcs = r.s.hc
    hcinfo = ("off" if hcs is None else
              f"stage {hcs.stage}, base {hcs.z_h:.3f} m, brink {hcs.x_h:.2f} m (outlet {r.s.x_o:.2f}), "
              f"outlet retreat {sum(e.get('dist', 0) for e in ev if e['type'] == 'headcut_outlet_retreat'):.3f} m, "
              f"V_hc {hcs.vol:.4f} m3, V_roof {hcs.V_roof:.4f} m3")
    seq = []
    for e in ev:
        if not seq or seq[-1] != e["type"]:
            seq.append(e["type"])
    cra_t = cra["t"] if cra else None
    after = [row for row in r.series if cra_t is not None and row["t"] >= cra_t and "z_c" in row]
    zc = [row["z_c"] for row in after]
    reopen = next((row["t"] for row in after if row.get("a_open", 0) > 0 and row.get("Q_out_cr", 0) > 0), None)
    crs = r.s.crater
    geom = ("no crater" if crs is None else
            f"crater [{crs.x1:.2f}, {crs.x2:.2f}] W {crs.W:.2f} z_d {crs.z_d:.3f}; pipe b {r.s.pipe.b:.3f} D {r.s.pipe.D:.3f}; "
            f"fallen {crs.V_fall:.3f} m3, exported {crs.V_exp_out:.3f}, tank {crs.V_tank:.3f}")
    peak = max(row["Q_final"] for row in r.series)
    tpk = next(row["t"] for row in r.series if row["Q_final"] == peak)
    extra = dict(zc=(min(zc), max(zc)) if zc else None, reopen=reopen, geom=geom, peak=peak, tpk=tpk,
                 solids=r.max_solids_err)
    return dict(p=p, hc=hcinfo, seq=" > ".join(seq), **extra, tau0=pp.wall_shear(fl0), t_inlet=inl["t"] if inl else None, t_crater=cra["t"] if cra else None,
                b_crater=cra["b"] if cra else None,
                retreat=sum(e.get("dist", 0) for e in ev if e["type"] == "inlet_retreat"),
                t_handover=ho["t"] if ho else None,
                outcome=(r.stopped[0] if r.stopped else
                         ("spilling at t_end" if r.series and r.series[-1].get("Q_spill", 0) > 0 else "running at t_end")),
                water=r.max_water_err)


def fmt(v, f="{:8.1f}"):
    return f.format(v) if v is not None else "       -"


_T = None


def _task(args):
    """One run in a worker process (the table is loaded once per process)."""
    global _T
    name, kw, dt, t_end = args
    if _T is None:
        _T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    return name, dt, run(_T, dt=dt, t_end=t_end, **kw)


def main():
    import argparse
    import math
    import os
    from multiprocessing import Pool
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default="2,1,0.5")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--modes", default="level,instant,tank")
    ap.add_argument("--t_end", type=float, default=4 * 3600.0, help="model time per run [s]")
    a = ap.parse_args()
    dts = [float(v) for v in a.dt.split(",")]
    base = [("field JET (R = 1)", {})]
    base += [(f"R = {R:g} ({lab}): k_d {150 / R:.3g}", dict(kd=150e-6 / R))
             for R, lab in ((9.1, "low"), (22.2, "P2"), (47.4, "central"), (101.4, "P3"), (171.4, "high"))]
    cases = [(f"{nm} | {m:7s}", {**kw, "debris": m}) for m in a.modes.split(",") for nm, kw in base]
    tasks = [(name, kw, dt, a.t_end) for name, kw in cases for dt in dts]
    tasks.sort(key=lambda t: (t[2], t[1].get("kd", 1.0)))   # small steps and low k_d (slowest) first
    workers = a.workers or max(1, min((os.cpu_count() or 2) - 1, 8, len(tasks)))
    t0 = time.time()
    lines = [f"ARS P1 debris treatments ({a.modes}) across the 5.4a k_d band; tau_c 0, n_p 0.016, exit headcut off; time steps {dts} s; t_end {a.t_end:g} s",
             "observed sequence (PAP-1017): pipe enlargement with headcutting to the base, soil-bridge collapse at 0.23 h (790-830 s), breach;",
             "time origin not defined in the source: comparison provisional (5.4a point 6)", ""]
    print("\n".join(lines) + f"{len(tasks)} runs on {workers} workers", flush=True)
    res = {name: {} for name, _ in cases}
    with Pool(workers, maxtasksperchild=4) as pool:
        for k, (name, dt, r) in enumerate(pool.imap_unordered(_task, tasks), 1):
            res[name][dt] = r
            print(f"  [{k:2d}/{len(tasks)}] {name:46s} dt {dt:4g}: tau0 {r['tau0']:6.2f} Pa  inlet "
                  f"{fmt(r['t_inlet'])}  crater {fmt(r['t_crater'])}  b_cr {fmt(r['b_crater'], '{:6.3f}')}  "
                  f"retreat {r['retreat']:6.3f}  handover {fmt(r['t_handover'])}  {r['outcome']}  "
                  f"({time.time() - t0:.0f} s)", flush=True)
    table = [f"{'run':34s} {'dt':>4s} {'tau0 Pa':>8s} {'inlet s':>8s} {'crater s':>8s} {'b_cr m':>7s} "
             f"{'retr m':>7s} {'handov s':>8s}  outcome"]
    summary = []
    for name, _ in cases:
        for dt in dts:
            r = res[name][dt]
            table.append(f"{name:46s} {dt:4g} {r['tau0']:8.2f} {fmt(r['t_inlet'])} {fmt(r['t_crater'])} "
                         f"{fmt(r['b_crater'], '{:7.3f}')} {r['retreat']:7.3f} {fmt(r['t_handover'])}  {r['outcome']}")
        tc = [res[name][dt]["t_crater"] for dt in dts]
        outcomes = {res[name][dt]["outcome"] for dt in dts}
        conv = "-"
        if all(v is not None for v in tc) and len(dts) == 3:
            d1, d2 = tc[0] - tc[1], tc[1] - tc[2]
            if d2 != 0 and d1 / d2 > 0:
                pobs = math.log(d1 / d2) / math.log(dts[0] / dts[1])
                t_inf = tc[2] - d2 / ((dts[1] / dts[2]) ** pobs - 1) if pobs > 0 else float("nan")
                conv = f"p = {pobs:4.2f}, t_inf = {t_inf:8.1f} s"
            else:
                conv = f"differences {d1:+.2f}, {d2:+.2f} s (not monotone)"
        summary.append(f"{name:46s} sequence (dt {dts[-1]:g}): {res[name][dts[-1]]['seq']}")
        rr = res[name][dts[-1]]
        zcs = "-" if rr["zc"] is None else f"{rr['zc'][0]:.3f}-{rr['zc'][1]:.3f} m"
        summary.append(f"{name:46s} (dt {dts[-1]:g}) crater level {zcs}; downstream open from "
                       f"{fmt(rr['reopen']).strip()} s; pipe-stage peak {rr['peak']:.3f} m3/s at {rr['tpk']:.0f} s")
        summary.append(f"{name:46s} (dt {dts[-1]:g}) end state: {rr['geom']}")
        summary.append(f"{name:46s} crater start {', '.join(fmt(v).strip() for v in tc)} s | {conv} | "
                       f"outcome {'same' if len(outcomes) == 1 else 'DIFFERS'}: {', '.join(sorted(outcomes))}")
    water = max(r["water"] for d in res.values() for r in d.values())
    solids = max(r["solids"] for d in res.values() for r in d.values())
    lines += table + ["", "Summary (crater-start time at each step, convergence, outcome):"] + summary
    lines.append(f"\nwall time {time.time() - t0:.0f} s on {workers} workers; largest water-budget error {water:.1e}, solids {solids:.1e}")
    text = "\n".join(lines)
    print("\n" + "\n".join(lines[3:]))
    (HERE / "p1_debris_modes.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
