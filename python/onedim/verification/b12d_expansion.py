"""B12d expansion check (user plan, 2026-11-28): is the instability specific to a slot (pressurised)
cell discharging into a free-surface cell, or general to (6.14a) at expansions?

Same linearisation as b12d_stability / b12d_sweep: steady state, Jacobian of one explicit step,
spectral radius against CFL, critical CFL by bisection. CFL is relative to each case's own solver
step (6.21) at its steady state; dt_crit in seconds is also reported. Reconstruction (6.14a) and the
loading (6.16b) as in the solver. Downstream stage from the junction relation for each pair, so each
case starts at its own steady state. Frictionless, 80 + 80 cells of 0.25 m.

Case groups (area ratio r = A_up / A_down at the steady state):
  1 free -> free         open rectangle -> open rectangle 1 m, h = 0.6 m, Q = 0.05:
                          upstream width 0.0667 m (r ~ 0.067, the same flow area and velocity as the
                          conduit), 0.2 m (r ~ 0.2); and the B12a case 2 m -> 10 m, h = 1 m, Q = 2
  2 pressurised -> free  conduit 0.2 x 0.2 m (a_s = 50 m/s) -> open rectangle 1 m, h = 0.6 m (r ~ 0.067)
  3 pressurised -> pressurised  conduit 0.2 x 0.2 -> conduit 1.0 m wide x 0.55 m high (r ~ 0.073) and
                          -> 1.0 x 0.4 m (r = 0.1); both run full (stage 0.6 m above both crowns)

For each case the dominant mode just above the limit is reported as the discharge perturbation in
the four cells around the interface (cells 78-81, normalised to the largest), and its share in A.

Usage: python -B -u -m onedim.verification.b12d_expansion [--workers N]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ..geometry import conduit, rectangle
from ..solver import Model
from .junctions import _solve_downstream
from .b12d_stability import _map

DS, N = 0.25, 80
CFLS = (0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)


def cases():
    return [
        ("1 free->free, 0.0667 m -> 1 m", "free", 0.0667, None, 0.6, 0.05),
        ("1 free->free, 0.2 m -> 1 m", "free", 0.2, None, 0.6, 0.05),
        ("1 free->free, 2 m -> 10 m (B12a)", "free_b12a", 2.0, None, 1.0, 2.0),
        ("2 pressurised->free, conduit 0.2 -> 1 m", "pf", 0.2, None, 0.6, 0.05),
        ("3 pressurised->pressurised, -> 1.0 x 0.55 conduit", "pp", 1.0, 0.55, 0.6, 0.05),
        ("3 pressurised->pressurised, -> 1.0 x 0.40 conduit", "pp", 1.0, 0.40, 0.6, 0.05),
    ]


def build(kind, w, hgt, h, q):
    if kind == "free":
        up, dn = rectangle(0.0, w), rectangle(0.0, 1.0)
    elif kind == "free_b12a":
        up, dn = rectangle(0.0, 2.0), rectangle(0.0, 10.0)
    elif kind == "pf":
        up, dn = conduit(0.0, 0.2, 0.2, 50.0), rectangle(0.0, 1.0)
    else:
        up, dn = conduit(0.0, 0.2, 0.2, 50.0), conduit(0.0, w, hgt, 50.0)
    eta_dn = _solve_downstream(up, dn, q, h)
    m = Model([up] * N + [dn] * N, DS, bc_left={"type": "discharge", "Q": q},
              bc_right={"type": "stage", "eta": eta_dn}, cfl=0.05)
    m.set_stage(np.r_[np.full(N, h), np.full(N, eta_dn)]); m.Q = np.full(2 * N, q)
    return m, eta_dn


def _jac_mode(m, x0, dt):
    m.cfl = 1e3
    n = len(x0); J = np.zeros((n, n))
    for k in range(n):
        hh = 1e-7 * max(abs(x0[k]), 1e-3)
        xp = x0.copy(); xp[k] += hh
        xm = x0.copy(); xm[k] -= hh
        J[:, k] = (_map(m, xp, dt) - _map(m, xm, dt)) / (2 * hh)
    ev, V = np.linalg.eig(J)
    k = int(np.argmax(np.abs(ev)))
    return float(abs(ev[k])), ev[k], V[:, k]


def analyse(label, kind, w, hgt, h, q, t_steady=40.0):
    t0 = time.time()
    m, eta_dn = build(kind, w, hgt, h, q)
    m.run(t_steady)
    x0 = np.r_[m.A, m.Q]
    probe, _ = build(kind, w, hgt, h, q); probe.A, probe.Q = m.A.copy(), m.Q.copy(); probe.cfl = 1.0
    m.cfl = 1.0
    dt1 = min(m.time_step(), probe.step(1.0))
    drift = float(np.max(np.abs(_map(m, x0, 0.05 * dt1) - x0)))
    r_area = float(m.A[N - 1] / m.A[N])
    rho = {c: _jac_mode(m, x0, c * dt1)[0] for c in CFLS}
    crit = None
    if rho[CFLS[0]] > 1 + 1e-6:
        crit = "< 0.05"
    else:
        for c0, c1 in zip(CFLS, CFLS[1:]):
            if rho[c0] <= 1 + 1e-6 < rho[c1]:
                lo, hi = c0, c1
                for _ in range(8):
                    mid = 0.5 * (lo + hi)
                    if _jac_mode(m, x0, mid * dt1)[0] > 1 + 1e-6:
                        hi = mid
                    else:
                        lo = mid
                crit = 0.5 * (lo + hi)
                break
    c_mode = crit * 1.05 if isinstance(crit, float) else (0.05 if crit else 1.0)
    r, lam, v = _jac_mode(m, x0, c_mode * dt1)
    vA, vQ = v[:m.N], v[m.N:]
    ph = vQ[np.argmax(np.abs(vQ))]
    dq = (vQ[N - 2:N + 2] / ph).real                 # discharge perturbation, cells 78-81, phase-aligned
    share_A = float(np.abs(vA).sum() / (np.abs(v).sum() + 1e-30))
    S = m.last
    return dict(label=label, r_area=r_area, eta_dn=eta_dn, dt1=dt1, drift=drift, rho=rho, crit=crit,
                lam=complex(lam), rho_mode=r, c_mode=c_mode, dq=dq, share_A=share_A,
                speeds=(float(np.max(np.abs(S["SL"]))), float(np.max(np.abs(S["SR"])))),
                secs=time.time() - t0)


def fmt(r):
    c = r["crit"]
    cs = f"{c:.4f}" if isinstance(c, float) else (c or "stable to 1.0")
    dtc = f"{c * r['dt1']:.3e} s" if isinstance(c, float) else "-"
    lines = [f"{r['label']}",
             f"    area ratio A_up/A_down = {r['r_area']:.4f}; tailwater {r['eta_dn']:.4f} m; dt(CFL=1) = {r['dt1']:.3e} s "
             f"(max interface speed {max(r['speeds']):.2f} m/s); fixed-point drift {r['drift']:.1e}",
             f"    critical CFL = {cs}  (dt_crit = {dtc}); rho at CFL 0.9 = {r['rho'][0.9]:.4f}",
             f"    dominant mode at CFL {r['c_mode']:.3f}: lambda = {r['lam'].real:+.4f}{r['lam'].imag:+.4f}i "
             f"(|lambda| = {r['rho_mode']:.4f}); discharge perturbation in cells 78, 79 | 80, 81 = "
             + ", ".join(f"{x:+.3f}" for x in r["dq"][:2]) + " | " + ", ".join(f"{x:+.3f}" for x in r["dq"][2:])
             + f"; share in A {r['share_A']:.2f}",
             f"    ({r['secs']:.0f} s)"]
    return "\n".join(lines)


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    cs = cases()
    T0 = time.time()
    print(f"B12d expansion check: {len(cs)} cases on {workers} workers (each: 40 s steady run, "
          f"{len(CFLS)} Jacobians, bisection)", flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyse, *c): c[0] for c in cs}
        for f in as_completed(futs):
            lab = futs[f]
            try:
                res[lab] = f.result()
                print(f"[{time.time() - T0:6.0f} s] done: {lab}", flush=True)
            except Exception as e:
                res[lab] = None
                print(f"[{time.time() - T0:6.0f} s] ERROR {lab}: {e!r}", flush=True)
    print("\n================ RESULTS ================")
    for c in cs:
        print(fmt(res[c[0]]) if res[c[0]] else f"{c[0]}: ERROR"); print()
    print(f"DONE ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
