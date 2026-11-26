"""Note H-1, controlled coupled test of H1-a (review 2026-11-26): exit widening on, P1 in the frozen
validation configuration (level debris + D5 + D1-a, c_u0 5 kPa), the 5.4a k_d band, dt = 2, 1, 0.5 s.
Reports per run: exit width B_e against the pipe width at roof collapse (the photo comparison is a ratio,
scale >~ 0.45 m per marker spacing, a lower bound), the notch flow depth against the pipe crown (open
cavern check, review point B), the notch critical depth against the pipe height, the bulk and solid
volume removed by widening, outcome, budgets. Option off reproduces the frozen runs (H-A7, unit tests).
Usage: python lumped/verification/p1_h1a.py [--workers N]. Writes p1_h1a.txt next to this script."""
import argparse
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lumped import exit_widening as xw                 # noqa: E402
from lumped.piping_run import PipingRun                # noqa: E402
from lumped.stability_table import StabilityTable      # noqa: E402
from lumped.tests.test_piping_run import N, p1_case     # noqa: E402

KD = (16.5, 6.77, 3.16, 1.48, 0.88)
G = 9.81
_T = None


def run(args):
    global _T
    kd, dt = args
    if _T is None:
        _T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    r = PipingRun(p1_case(kd=kd * 1e-6, exit_widening=True, plugs=True), _T, dt=dt).run(7200.0)
    cra = next((e for e in r.events if e["type"] == "crater_start"), None)
    pre = [x for x in r.series if "cr_W" not in x and "B_e" in x]
    last = pre[-1]
    Q = None
    if cra:
        b, D, B = cra["b"], cra["D"], cra["B_e"]
        crown = cra["z_inv"] + D
    else:
        b, D, B, crown = last["b"], last["D"], last["B_e"], last["z_inv"] + last["D"]
    q_pts = [x for x in pre]
    y_max = max(x["notch_depth"] for x in q_pts)
    ratio_D = max(x["notch_depth"] / x["D_out"] for x in q_pts)
    # critical depth in the notch against the pipe height, at the last pre-collapse record
    from lumped import piping as pp
    p = pp.Pipe(last["b"], last["D"], last["z_inv"], last["x_o"] - last["x_in"])
    Q = pp.pipe_flow(1.1 - last["z_inv"], p.b, p.D, p.L, 0.016).Q
    yc = (Q * Q / (G * last["B_e"] ** 2)) ** (1 / 3)
    return dict(kd=kd, dt=dt, t_c=cra["t"] if cra else None, b=b, B=B, D=D, crown=crown, y_max=y_max,
                ratio_D=ratio_D, yc=yc, D_last=last["D"], V=r.s.V_exit, Vs=(1 - N) * r.s.V_exit,
                out=r.stopped[0] if r.stopped else "running", water=r.max_water_err, solids=r.max_solids_err)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--dt", default="2,1,0.5")
    a = ap.parse_args()
    dts = [float(v) for v in a.dt.split(",")]
    tasks = sorted([(kd, dt) for kd in KD for dt in dts], key=lambda t: (t[1], -t[0]))
    workers = a.workers or max(1, min((os.cpu_count() or 2) - 1, 8, len(tasks)))
    t0 = time.time()
    res = {}
    with Pool(workers, maxtasksperchild=4) as pool:
        for k, r in enumerate(pool.imap_unordered(run, tasks), 1):
            res[(r["kd"], r["dt"])] = r
            print(f"  [{k:2d}/{len(tasks)}] k_d {r['kd']} dt {r['dt']:g}: B_e/b {r['B'] / r['b']:.3f} ({time.time() - t0:.0f} s)",
                  flush=True)
    L = ["P1 H1-a controlled coupled test (exit widening on; level + D5 + D1-a; c_u0 5 kPa)", "",
         f"{'k_d':>5} {'dt':>4} | {'collapse s':>10} {'pipe b':>7} {'exit B_e':>8} {'B_e/b':>6} | {'max notch y':>11} "
         f"{'y/D max':>7} {'y_c notch':>9} {'D':>6} | {'V_exit bulk':>11} {'solid':>7} | outcome"]
    for kd in KD:
        for dt in dts:
            r = res[(kd, dt)]
            L.append(f"{kd:5.2f} {dt:4g} | {r['t_c'] if r['t_c'] is None else round(r['t_c'], 1)!s:>10} {r['b']:7.3f} "
                     f"{r['B']:8.3f} {r['B'] / r['b']:6.3f} | {r['y_max']:11.4f} {r['ratio_D']:7.3f} {r['yc']:9.4f} "
                     f"{r['D_last']:6.3f} | {r['V']:11.5f} {r['Vs']:7.5f} | {r['out']}")
    w = max(r["water"] for r in res.values()); s = max(r["solids"] for r in res.values())
    L.append(f"\nlargest water-budget error {w:.1e}, solids {s:.1e}; wall time {time.time() - t0:.0f} s on {workers} workers")
    text = "\n".join(L)
    print("\n" + text)
    (HERE / "p1_h1a.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
