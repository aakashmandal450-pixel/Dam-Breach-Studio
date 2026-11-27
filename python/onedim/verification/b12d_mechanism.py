"""B12d mechanism checks (2026-11-27), after the CFL series showed that the conduit-outlet oscillation
vanishes at CFL 0.1125 (stage 0.6000 m, loss 0.0692 m = relation and Borda) and grows with the time step.

M1  interface flux response: change in the HLL mass and momentum flux for a stage difference across
    one interface, in free-surface, pressurised, and conduit -> open-channel pairs
M2  no section change: a uniform pressurised conduit; a pressurised conduit into a larger pressurised
    conduit; a pressurised conduit into a 1 x 1 m conduit running with a free surface
M3  term trace in the last conduit cell (conduit -> open 1 m): interface mass fluxes, the HLL momentum
    flux contribution and the step-face (W) contribution to dQ in each step, at CFL 0.9 and 0.1125
M4  B12a contractions (open channels, no slot) at CFL 0.9 and 0.1125: does the contraction mismatch
    depend on the time step as well?

Usage: python -B -u -m onedim.verification.b12d_mechanism [--workers N]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ..geometry import conduit, rectangle, trapezoid
from ..solver import Model, G
from . import junctions as J

Q = 0.05
DS = 0.25
N = 80


# ------------------------------------------------------------------------------------------ M1
def m1():
    lines = ["M1 interface flux response (one interface, Q = 0.05 m3/s both cells, dt = 1e-9 s)"]

    def flux(a, b, eL, eR):
        m = Model([a, b], DS, bc_left={"type": "transmissive"}, bc_right={"type": "transmissive"})
        m.set_stage(np.array([eL, eR])); m.Q = np.full(2, Q)
        m.step(dt=1e-9)
        L = m.last
        return L["FA"][1], L["FQ"][1], L["SL"][1], L["SR"][1]

    cases = [("free surface: open 0.2 | open 0.2, eta 0.5 (subcritical)", rectangle(0, 0.2), rectangle(0, 0.2), 0.5),
             ("pressurised: conduit | conduit, eta 0.6", conduit(0, 0.2, 0.2, 50.0), conduit(0, 0.2, 0.2, 50.0), 0.6),
             ("outlet: conduit | open 1 m, eta 0.6", conduit(0, 0.2, 0.2, 50.0), rectangle(0, 1.0), 0.6)]
    for name, a, b, e0 in cases:
        F0, M0, SL, SR = flux(a, b, e0, e0)
        lines.append(f"  {name}: FA0 = {F0:.5f} m3/s, FQ0 = {M0:.5f}, S_L = {SL:.2f}, S_R = {SR:.2f} m/s")
        for de in (0.001, 0.01, 0.1):
            F, Mq, _, _ = flux(a, b, e0 + de, e0)
            lines.append(f"      d_eta = {de:5.3f} m: dFA = {F - F0:+.3e} m3/s ({(F - F0) / de:+.3e} per m), "
                         f"dFQ = {Mq - M0:+.3e} ({(Mq - M0) / de:+.3e} per m)")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------ M2, M3
def _run(cells, eta0, eta_dn, T, track, cfl=0.9, trace_last=0.0):
    m = Model(cells, DS, bc_left={"type": "discharge", "Q": Q}, bc_right={"type": "stage", "eta": eta_dn}, cfl=cfl)
    m.set_stage(eta0); m.Q = np.full(len(cells), Q)
    s, tr = [], []
    while m.t < T:
        m.step()
        if m.t > T - 30.0:
            s.append(m.stage()[track])
        if trace_last and m.t > T - trace_last:
            L = m.last; i = track; r = L["dt"] / DS
            tr.append((m.t, m.stage()[i], m.Q[i], L["FA"][i], L["FA"][i + 1],
                       -r * (L["FQ"][i + 1] - L["FQ"][i]), -r * (L["WR"][i] - L["WL"][i]), L["etaf_R"][i]))
    return m, float(np.ptp(s)), float(np.mean(s)), tr


def m2(case):
    c = conduit(0, 0.2, 0.2, 50.0)
    eta0 = np.r_[np.full(N, 0.65), np.full(N, 0.61)]
    if case == "uniform":
        name = "uniform pressurised conduit (160 cells), tailwater 0.61 m"
        cells = [c] * (2 * N)
    elif case == "bigger_pressurised":
        name = "pressurised 0.2 conduit -> pressurised 0.4 x 0.4 conduit (eta above both crowns)"
        cells = [c] * N + [conduit(0, 0.4, 0.4, 50.0)] * N
    else:
        name = "pressurised 0.2 conduit -> 1 x 1 m conduit with a free surface"
        cells = [c] * N + [conduit(0, 1.0, 1.0, 50.0)] * N
    m, osc, mean, _ = _run(cells, eta0, 0.61, 120.0, N - 1)
    return f"M2 {name}: oscillation in cell {N - 1} (last 30 s of 120 s) = {osc:.3e} m, mean stage {mean:.4f} m"


def m3(cfl):
    c = conduit(0, 0.2, 0.2, 50.0)
    cells = [c] * N + [rectangle(0, 1.0)] * N
    m, osc, mean, tr = _run(cells, np.r_[np.full(N, 0.65), np.full(N, 0.61)], 0.61, 120.0, N - 1, cfl=cfl,
                            trace_last=0.06)
    lines = [f"M3 term trace, last conduit cell (i = {N - 1}), conduit -> open 1 m, CFL {cfl}: "
             f"oscillation {osc:.3e} m, mean stage {mean:.4f} m; final steps:",
             "      t [s]    eta_i [m]  Q_i       FA_in     FA_out    dQ from HLL momentum   dQ from step face W   eta_f right face"]
    for row in tr[-14:]:
        lines.append("    %9.4f  %8.4f  %8.5f  %8.5f  %8.5f   %+12.4e          %+12.4e          %8.4f" % row)
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------ M4
def m4(i, cfl):
    specs = J.b12a_specs()
    name, a, b, kind, Qc, h1 = specs[i]
    orig = Model.__init__

    def init(self, *args, **kw):
        kw.setdefault("cfl", cfl); orig(self, *args, **kw)

    Model.__init__ = init
    try:
        r = J.b12a_one(name, a, b, kind, Qc, h1, +1, "discharge_width")
    finally:
        Model.__init__ = orig
    return (f"M4 {name:12s} CFL {cfl:<6}: loss {r['loss']:.5f} m, relation {r['loss_rel']:.5f} m "
            f"({100 * r['err_rel']:+.1f} %), steady {r['converged']}")


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    con = [i for i, s in enumerate(J.b12a_specs()) if s[3] == "con"]
    jobs = [("M1", m1, ()), ("M2a", m2, ("uniform",)), ("M2b", m2, ("bigger_pressurised",)),
            ("M2c", m2, ("free_surface_conduit",)), ("M3 CFL 0.9", m3, (0.9,)), ("M3 CFL 0.1125", m3, (0.1125,))]
    jobs += [(f"M4 {i} {c}", m4, (i, c)) for i in con for c in (0.9, 0.1125)]
    T0 = time.time()
    print(f"B12d mechanism checks: {len(jobs)} jobs on {workers} workers "
          f"(the CFL 0.1125 jobs are the slowest, about 8x the steps)", flush=True)
    out = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, *args): key for key, fn, args in jobs}
        for f in as_completed(futs):
            key = futs[f]
            try:
                out[key] = f.result()
                print(f"[{time.time() - T0:6.0f} s] done: {key}", flush=True)
            except Exception as e:
                out[key] = f"{key}: ERROR {e!r}"
                print(f"[{time.time() - T0:6.0f} s] ERROR {key}: {e!r}", flush=True)
    print("\n================ RESULTS ================")
    for key, _, _ in jobs:
        print(out.get(key, f"{key}: missing"))
        print()
    print(f"DONE ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
