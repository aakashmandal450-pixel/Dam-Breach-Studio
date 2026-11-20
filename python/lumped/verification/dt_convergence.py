"""Time-step convergence of the lumped model — the lumped equivalent of grid convergence.

Runs each case at dt, dt/2, dt/4 (dt = t_end / N0) and reports Qp, Tp and B with the observed order p
and GCI (Roache; same routine as the 2-D convergence study). A GCI verdict is only given for
0.5 <= p <= 3. Explicit Euler is first order, so p near 1 is expected.

Usage (from the python folder):
    python -u -m lumped.verification.dt_convergence [--cases Castlewood E1S1 ...] [--n0 5000] [--desktop DIR]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PY)); sys.path.insert(0, str(PY / "calibration"))
import cases as C  # noqa: E402
from v34_convergence import gci  # noqa: E402

from lumped.model import run_case  # noqa: E402

CAL = ("Castlewood", "E1S1", "E1S3", "E2S2", "GooseCreek", "SouthFork", "LaurelRun")
METRICS = (("Qp", "m3/s"), ("Tp_h", "h"), ("B", "m"))
P_RANGE = (0.5, 3.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=list(CAL))
    ap.add_argument("--n0", type=int, default=5000, help="steps on the coarsest run")
    ap.add_argument("--desktop", default=None)
    a = ap.parse_args()

    rows = [f"LUMPED MODEL - TIME-STEP CONVERGENCE (dt = t_end/{a.n0}, /2, /4; neutral factors)",
            "p: observed order (explicit Euler -> ~1 expected). GCI: band on the finest value.", ""]
    head = f"  {'case':12s}{'metric':8s}{'dt':>14s}{'dt/2':>14s}{'dt/4':>14s}{'p':>7s}{'GCI%':>8s}   verdict"
    rows.append(head)
    t_all = time.time()
    fails = 0
    for cid in a.cases:
        case = C.load_case(cid)
        t_end = float(case.get("t_end", 43200.0))
        res = []
        for k in (1, 2, 4):
            t0 = time.time()
            r = run_case(case, factors={"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}, dt=t_end / (a.n0 * k))
            res.append(r)
            print(f"  {cid:12s} dt/{k}: Qp {r['Qp']:10.3f}  Tp {r['Tp_h']:7.3f} h  B {r['B']:8.2f}  "
                  f"({time.time() - t0:5.1f} s)", flush=True)
        for key, unit in METRICS:
            f3, f2, f1 = (res[0][key], res[1][key], res[2][key])
            p, status, _, g = gci(f3, f2, f1, 2.0, 2.0)
            if status != "ok":
                verdict = status
            elif not (P_RANGE[0] <= p <= P_RANGE[1]):
                verdict = "p out of range - not established"
            else:
                verdict = "CONVERGED" if g < 5 else ("marginal" if g < 15 else "NOT converged")
            if verdict not in ("CONVERGED", "converged (differences at round-off)"):
                fails += 1
            ps = f"{p:7.2f}" if p is not None else f"{'-':>7s}"
            gs = f"{g:7.2f}%" if g is not None else f"{'-':>8s}"
            rows.append(f"  {cid:12s}{key:8s}{f3:14.4f}{f2:14.4f}{f1:14.4f}{ps}{gs}   {verdict}")
        rows.append("")
    rows.append(f"metrics not converged: {fails}   wall time {time.time() - t_all:.0f} s")
    text = "\n".join(rows)
    print("\n" + text, flush=True)
    out = PY.parent / "runs" / "lumped_dt_convergence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "SUMMARY.txt").write_text(text + "\n")
    if a.desktop:
        Path(a.desktop, f"lumped_dt_convergence_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
