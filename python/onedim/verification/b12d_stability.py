"""B12d linear stability analysis (2026-11-27).

For each case: compute the steady state at a small CFL, linearise one explicit time step about it
(Jacobian of the update map by central differences, state = (A, Q) in every cell), and find the
spectral radius rho (largest |eigenvalue|) against CFL. rho > 1 means the step amplifies a mode:
the scheme is unstable at that time step. The critical CFL (rho = 1) is found by bisection, and the
worst mode is located (which cells, how much of it is in A versus Q).

The reference time step for "CFL = 1" is the solver's own rule (6.21) at the steady state:
dt1 = min over cells and interfaces of ds / wave speed; a run at CFL c uses dt = c * dt1.

Cases (all Q = 0.05 m3/s, ds = 0.25 m, 80 + 80 cells, frictionless, B12d boundary conditions):
  outlet        pressurised conduit 0.2 x 0.2 m (a_s = 50 m/s) -> open rectangle 1 m      (the B12d case)
  outlet_as100  as outlet, a_s = 100 m/s
  outlet_b04    as outlet, open rectangle 0.4 m
  pp            pressurised 0.2 conduit -> pressurised 0.4 x 0.4 conduit (no free surface)
  fs            pressurised 0.2 conduit -> 1 x 1 m conduit with a free surface
  uniform       uniform pressurised conduit (no section change)

Usage: python -B -u -m onedim.verification.b12d_stability [--cases outlet,uniform] [--workers N]
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

Q, DS, N = 0.05, 0.25, 80
CFLS = (0.1, 0.15, 0.2, 0.25, 0.3, 0.45, 0.6, 0.9)
CASES = ("outlet", "outlet_as100", "outlet_b04", "pp", "fs", "uniform")


def build(case):
    a_s = 100.0 if case == "outlet_as100" else 50.0
    c = conduit(0.0, 0.2, 0.2, a_s)
    eta_dn = _solve_downstream(conduit(0.0, 0.2, 0.2, 50.0), rectangle(0.0, 1.0), Q, 0.6)
    dn = {"outlet": rectangle(0.0, 1.0), "outlet_as100": rectangle(0.0, 1.0), "outlet_b04": rectangle(0.0, 0.4),
          "pp": conduit(0.0, 0.4, 0.4, a_s), "fs": conduit(0.0, 1.0, 1.0, a_s), "uniform": c}[case]
    m = Model([c] * N + [dn] * N, DS, bc_left={"type": "discharge", "Q": Q},
              bc_right={"type": "stage", "eta": eta_dn}, cfl=0.1)
    m.set_stage(np.r_[np.full(N, 0.6), np.full(N, eta_dn)]); m.Q = np.full(2 * N, Q)
    return m


def _map(m, x, dt):
    n = m.N
    m.A = x[:n].copy(); m.Q = x[n:].copy(); m.AC = np.zeros(n); m.M = np.zeros(n)
    m.step(dt)
    return np.r_[m.A, m.Q]


def _rho(m, x0, dt, want_mode=False):
    m.cfl = 1e3                                 # the given dt is never reduced inside step()
    n = len(x0)
    J = np.zeros((n, n))
    for k in range(n):
        h = 1e-7 * max(abs(x0[k]), 1e-3)
        xp = x0.copy(); xp[k] += h
        xm = x0.copy(); xm[k] -= h
        J[:, k] = (_map(m, xp, dt) - _map(m, xm, dt)) / (2 * h)
    ev, V = np.linalg.eig(J)
    k = int(np.argmax(np.abs(ev)))
    if not want_mode:
        return float(abs(ev[k])), None
    v = np.abs(V[:, k]); nc = m.N
    cell_w = v[:nc] / max(v[:nc].max(), 1e-30) + v[nc:] / max(v[nc:].max(), 1e-30)
    top = [int(i) for i in np.argsort(cell_w)[::-1][:4]]
    a_part = float(v[:nc].sum() / (v.sum() + 1e-30))
    return float(abs(ev[k])), dict(eig=complex(ev[k]), cells=top, A_part=a_part)


def analyse(case, t_steady=40.0):
    t0 = time.time()
    m = build(case)
    m.run(t_steady)
    x0 = np.r_[m.A, m.Q]
    m.cfl = 1.0
    dt1 = m.time_step()
    # include the interface wave speeds of (6.21): take one probe step with a huge dt and read the cap
    probe = build(case); probe.A, probe.Q = m.A.copy(), m.Q.copy(); probe.cfl = 1.0
    dt1 = min(dt1, probe.step(1.0))
    drift = float(np.max(np.abs(_map(m, x0, 0.1 * dt1) - x0)))
    lines = [f"{case}: steady state after {t_steady:.0f} s (fixed-point drift per step at CFL 0.1: {drift:.1e}); "
             f"dt(CFL = 1) = {dt1:.3e} s; conduit stage near the outlet {m.stage()[N - 1]:.4f} m"]
    rows = []
    for c in CFLS:
        r, mode = _rho(m, x0, c * dt1, want_mode=True)
        rows.append((c, r))
        lines.append(f"    CFL {c:5.3f}: rho = {r:.6f}  {'UNSTABLE' if r > 1 + 1e-6 else 'stable  '}  "
                     f"worst mode: lambda = {mode['eig'].real:+.4f}{mode['eig'].imag:+.4f}i, peaks in cells "
                     f"{mode['cells']}, share in A {mode['A_part']:.2f}")
    # critical CFL by bisection between the last stable and the first unstable value
    crit = None
    for (c0, r0), (c1, r1) in zip(rows, rows[1:]):
        if r0 <= 1 + 1e-6 < r1:
            lo, hi = c0, c1
            for _ in range(7):
                mid = 0.5 * (lo + hi)
                if _rho(m, x0, mid * dt1)[0] > 1 + 1e-6:
                    hi = mid
                else:
                    lo = mid
            crit = 0.5 * (lo + hi)
            break
    if crit is not None:
        lines.append(f"    critical CFL = {crit:.4f} (rho = 1), i.e. dt_crit = {crit * dt1:.3e} s")
    elif rows[0][1] > 1 + 1e-6:
        lines.append("    unstable already at CFL 0.1")
    else:
        lines.append("    stable at every CFL tested (to 0.9)")
    lines.append(f"    ({time.time() - t0:.0f} s)")
    return "\n".join(lines)


def main():
    cases = sys.argv[sys.argv.index("--cases") + 1].split(",") if "--cases" in sys.argv else list(CASES)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    T0 = time.time()
    print(f"B12d linear stability: {len(cases)} cases on {workers} workers; each case = a 40 s steady run at "
          f"CFL 0.1, then {len(CFLS)} Jacobians (320 x 320) and a bisection", flush=True)
    out = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyse, c): c for c in cases}
        for f in as_completed(futs):
            c = futs[f]
            try:
                out[c] = f.result()
            except Exception as e:
                out[c] = f"{c}: ERROR {e!r}"
            print(f"[{time.time() - T0:6.0f} s] done: {c}", flush=True)
    print("\n================ RESULTS ================")
    for c in cases:
        print(out[c]); print()
    print(f"DONE ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
