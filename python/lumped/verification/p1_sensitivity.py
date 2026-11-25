"""ARS P1: one-at-a-time sensitivity of the pipe-stage timing to tau_c and n_p (decision 2026-11-25).

Baseline: field-JET k_d 150 cm3/(N s), tau_c 0, n_p 0.016 (other inputs as in p1_diagnostic.py).
Each parameter is varied alone over a range justified by the sources, the others held at the baseline.
This is not a calibration: the observed collapse time (790-830 s) is reported beside the results, not
fitted. Ranges:
  tau_c [Pa]: 0 (field JET, PAP-1017 Table 4); 8.7e-5 and 3.1e-4 (lab JETs at ARS conditions, PAP-1017);
              0.144 (GeoHazards 2024 base) and 0.16 (top of its range). 1.0 is added as a value above every
              P1 source, to show the threshold's leverage, and is labelled as such.
  n_p:        0.012-0.030: smooth to rough earth channels (Chow 1959, Table 5-6, excavated earth); 0.016 is
              the model default (the open-breach n); 0.025 is the GeoHazards 2024 base.
Outputs per run: first inlet retreat, crater start, pipe width at crater start, total inlet retreat,
hand-over time, sealed or not, and the initial wall shear.

Every case is run at three time steps (default 2, 1 and 0.5 s) so that each result can be checked for
time-step convergence: the crater-start time, its observed order p and a Richardson estimate
t_inf = t(dt_min) - (t(dt_mid) - t(dt_min)) / (2^p - 1) are reported, and the outcome (sealed, hand-over,
...) must be the same at all three steps.

Usage (from the python folder):  python lumped/verification/p1_sensitivity.py [dt1,dt2,dt3]
Writes p1_sensitivity.txt next to this script, with progress printed as each run finishes.
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
BASE = dict(kd=150e-6, tau_c=0.0, n_p=0.016)


def run(T, dt=1.0, **kw):
    p = {**BASE, **kw}
    case = PipingCase(dam=Dam(1.3, 1.83, 3.0, 3.0, 100.0), soil=SOIL, kd=p["kd"], tau_c=p["tau_c"], b0=0.04,
                      D0=0.04, z_inv0=0.2, z_s0=1.1, porosity=N, n_p=p["n_p"])
    fl0 = pp.pipe_flow(1.1 - 0.2, 0.04, 0.04, Dam(1.3, 1.83, 3.0, 3.0, 100.0).x_down(0.22) - 0.66, p["n_p"])
    r = PipingRun(case, T, dt=dt).run(4 * 3600.0)
    ev = r.events
    first = lambda k: next((e for e in ev if e["type"] == k), None)
    inl, cra = first("inlet_retreat"), first("crater_start")
    ho = first("handover")
    return dict(p=p, tau0=pp.wall_shear(fl0), t_inlet=inl["t"] if inl else None, t_crater=cra["t"] if cra else None,
                b_crater=cra["b"] if cra else None,
                retreat=sum(e.get("dist", 0) for e in ev if e["type"] == "inlet_retreat"),
                t_handover=ho["t"] if ho else None, outcome=r.stopped[0] if r.stopped else "running at t_end",
                water=r.max_water_err)


def fmt(v, f="{:8.1f}"):
    return f.format(v) if v is not None else "       -"


def main():
    import math
    dts = [float(v) for v in sys.argv[1].split(",")] if len(sys.argv) > 1 else [2.0, 1.0, 0.5]
    T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    t0 = time.time()
    cases = [("baseline", {})]
    cases += [(f"tau_c = {v:g} Pa" + (" (above all P1 sources)" if v == 1.0 else ""), dict(tau_c=v))
              for v in (8.7e-5, 3.1e-4, 0.144, 0.16, 1.0)]
    cases += [(f"n_p = {v:g}", dict(n_p=v)) for v in (0.012, 0.020, 0.025, 0.030)]
    lines = [f"ARS P1 one-at-a-time sensitivity (baseline k_d 150 cm3/(N s), tau_c 0, n_p 0.016); time steps {dts} s",
             "observed: soil-bridge collapse 790-830 s (PAP-1017; Chen et al. 2019), not fitted", ""]
    print("\n".join(lines), flush=True)
    summary = []
    for name, kw in cases:
        res = {}
        for dt in dts:
            res[dt] = run(T, dt=dt, **kw)
            r = res[dt]
            print(f"  {name:34s} dt {dt:4g}: tau0 {r['tau0']:6.2f} Pa  inlet {fmt(r['t_inlet'])}  crater "
                  f"{fmt(r['t_crater'])}  b_cr {fmt(r['b_crater'], '{:6.3f}')}  retreat {r['retreat']:6.3f}  "
                  f"handover {fmt(r['t_handover'])}  {r['outcome']}  ({time.time() - t0:.0f} s)", flush=True)
        tc = [res[dt]["t_crater"] for dt in dts]
        outcomes = {res[dt]["outcome"] for dt in dts}
        conv = "-"
        if all(v is not None for v in tc) and len(dts) == 3:
            d1, d2 = tc[0] - tc[1], tc[1] - tc[2]
            if d2 != 0 and d1 / d2 > 0:
                pobs = math.log(d1 / d2) / math.log(dts[0] / dts[1])
                t_inf = tc[2] - d2 / (2 ** pobs - 1) if pobs > 0 else float("nan")
                conv = f"p = {pobs:4.2f}, t_inf = {t_inf:8.1f} s"
            else:
                conv = f"differences {d1:+.2f}, {d2:+.2f} s (not monotone)"
        summary.append(f"{name:34s} crater start {', '.join(fmt(v).strip() for v in tc)} s | {conv} | "
                       f"outcome {'same' if len(outcomes) == 1 else 'DIFFERS'}: {', '.join(sorted(outcomes))}")
    lines += ["", "Summary (crater-start time at each step, convergence, outcome):"] + summary
    lines.append(f"\nwall time {time.time() - t0:.0f} s")
    text = "\n".join(lines)
    print("\n".join(lines[3:]))
    (HERE / "p1_sensitivity.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
