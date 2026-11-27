"""B12d stability sweep (user plan, 2026-11-27): is the critical CFL at a pressurised -> free-surface
interface proportional to B_conduit / B_free?

Hypothesis under test (not an established law):  CFL_crit ~ B_conduit / B_free.

Every case: conduit 0.2 x 0.2 m, a_s = 50 m/s, frictionless, 80 + 80 cells of 0.25 m, the same
linearisation as b12d_stability (Jacobian of one explicit step about the steady state, spectral
radius against CFL, critical CFL by bisection). The tailwater (forward) or headwater (reverse) stage
is solved from the junction relation for each geometry, so every case starts at its own steady state.

  forward  (pressurised conduit -> free surface), flow left to right, discharge in, stage out:
      W  widths 0.3, 0.6, 1, 2, 5 m;  conduit head h_up = 0.6 m, Q = 0.05 m3/s
      H  depths: h_up = 0.4 m and 1.0 m with the 1 m channel (and 0.6 m for comparison above)
      Qv flow: Q = 0.02 and 0.10 m3/s with the 1 m channel, h_up = 0.6 m
  reverse  (free surface -> pressurised conduit): open channel upstream, conduit downstream with
      its exit stage held at 0.6 m (pressurised); widths 0.3, 1, 5 m
  control  uniform pressurised conduit

Usage: python -B -u -m onedim.verification.b12d_sweep [--workers N]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ..geometry import conduit, rectangle
from ..solver import Model
from .junctions import _solve_downstream, junction_relation
from .b12d_stability import _rho, _map

DS, N = 0.25, 80
CFLS = (0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)
BC = 0.2                                     # conduit width


def case_list():
    cs = []
    for w in (0.3, 0.6, 1.0, 2.0, 5.0):
        cs.append(("forward", w, 0.6, 0.05))
    for h in (0.4, 1.0):
        cs.append(("forward", 1.0, h, 0.05))
    for q in (0.02, 0.10):
        cs.append(("forward", 1.0, 0.6, q))
    for w in (0.3, 1.0, 5.0):
        cs.append(("reverse", w, 0.6, 0.05))
    cs.append(("uniform", 0.2, 0.6, 0.05))
    return cs


def build(kind, w, h, q):
    c = conduit(0.0, BC, 0.2, 50.0)
    o = rectangle(0.0, w)
    if kind == "forward":
        eta_dn = _solve_downstream(c, o, q, h)
        cells = [c] * N + [o] * N
        m = Model(cells, DS, bc_left={"type": "discharge", "Q": q}, bc_right={"type": "stage", "eta": eta_dn}, cfl=0.05)
        m.set_stage(np.r_[np.full(N, h), np.full(N, eta_dn)])
        info = f"conduit head {h:.2f} m, tailwater {eta_dn:.4f} m"
    elif kind == "reverse":
        eta_up = junction_relation(o, c, q, h)          # open-channel stage for conduit stage h downstream
        cells = [o] * N + [c] * N
        m = Model(cells, DS, bc_left={"type": "discharge", "Q": q}, bc_right={"type": "stage", "eta": h}, cfl=0.05)
        m.set_stage(np.r_[np.full(N, eta_up), np.full(N, h)])
        info = f"open-channel stage {eta_up:.4f} m, conduit exit stage {h:.2f} m"
    else:
        cells = [c] * (2 * N)
        m = Model(cells, DS, bc_left={"type": "discharge", "Q": q}, bc_right={"type": "stage", "eta": h}, cfl=0.05)
        m.set_stage(np.full(2 * N, h))
        info = f"stage {h:.2f} m"
    m.Q = np.full(2 * N, q)
    return m, info


def analyse(kind, w, h, q, t_steady=40.0):
    t0 = time.time()
    m, info = build(kind, w, h, q)
    m.run(t_steady)
    x0 = np.r_[m.A, m.Q]
    probe, _ = build(kind, w, h, q); probe.A, probe.Q = m.A.copy(), m.Q.copy(); probe.cfl = 1.0
    m.cfl = 1.0
    dt1 = min(m.time_step(), probe.step(1.0))
    drift = float(np.max(np.abs(_map(m, x0, 0.05 * dt1) - x0)))
    rows = [(c, _rho(m, x0, c * dt1)[0]) for c in CFLS]
    crit = None
    if rows[0][1] > 1 + 1e-6:
        crit = "< 0.05"
    else:
        for (c0, r0), (c1, r1) in zip(rows, rows[1:]):
            if r0 <= 1 + 1e-6 < r1:
                lo, hi = c0, c1
                for _ in range(8):
                    mid = 0.5 * (lo + hi)
                    if _rho(m, x0, mid * dt1)[0] > 1 + 1e-6:
                        hi = mid
                    else:
                        lo = mid
                crit = 0.5 * (lo + hi)
                break
    _, mode = _rho(m, x0, (crit if isinstance(crit, float) else 1.0) * dt1 * 1.05, want_mode=True)
    ratio = BC / w if kind in ("forward", "reverse") else 1.0
    return dict(kind=kind, w=w, h=h, q=q, info=info, dt1=dt1, drift=drift, rows=rows, crit=crit, ratio=ratio,
                mode=mode, secs=time.time() - t0)


def fmt(r):
    c = r["crit"]
    cs = (f"{c:.4f}" if isinstance(c, float) else (c or "stable to 1.0"))
    rat = (f"{c / r['ratio']:.3f}" if isinstance(c, float) else "-")
    head = (f"{r['kind']:8s} B_free = {r['w']:4.1f} m  h = {r['h']:.2f} m  Q = {r['q']:.2f} m3/s  "
            f"B_c/B_free = {r['ratio']:.3f}  critical CFL = {cs:>13s}  CFL_crit / (B_c/B_free) = {rat}")
    m = r["mode"]
    tail = (f"    {r['info']}; dt(CFL=1) = {r['dt1']:.3e} s; fixed-point drift {r['drift']:.1e}; worst mode just "
            f"above the limit: cells {m['cells']}, share in A {m['A_part']:.2f}; rho at CFL 0.9 = "
            f"{dict(r['rows'])[0.9]:.4f} ({r['secs']:.0f} s)")
    return head + "\n" + tail


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    cases = case_list()
    T0 = time.time()
    print(f"B12d stability sweep: {len(cases)} cases on {workers} workers (each: 40 s steady run, "
          f"{len(CFLS)} Jacobians, bisection)", flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyse, *c): c for c in cases}
        for f in as_completed(futs):
            c = futs[f]
            try:
                res[c] = f.result()
                print(f"[{time.time() - T0:6.0f} s] done: {c}", flush=True)
            except Exception as e:
                res[c] = None
                print(f"[{time.time() - T0:6.0f} s] ERROR {c}: {e!r}", flush=True)
    print("\n================ RESULTS ================")
    for c in cases:
        print(fmt(res[c]) if res[c] else f"{c}: ERROR"); print()
    fw = [res[c] for c in cases if res[c] and c[0] == "forward" and isinstance(res[c]["crit"], float)]
    if fw:
        k = np.array([r["crit"] / r["ratio"] for r in fw])
        print(f"forward cases: CFL_crit / (B_c/B_free) = {k.mean():.3f} mean, {k.min():.3f} .. {k.max():.3f} range "
              f"over {len(k)} cases (a constant would support the hypothesis)")
    print(f"\nDONE ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
