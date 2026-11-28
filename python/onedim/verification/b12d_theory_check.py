"""Verification matrix of the note `docs/theory/06_note_expansion_stability.md` (§7), 2026-11-28.

For each case: steady state, then
  - the prediction of (N.1): dt_crit = ds (D1 + D2) / (D1 D2 + P), from the solver's own wave speeds,
    areas and widths at the steady state (two-variable model of the note, §§2-4);
  - the linearised critical dt (Jacobian of one explicit step, bisection), as in b12d_expansion.
V1 prediction, V2 grid spacing (ds = 0.5, 0.25, 0.125 m on the same 20 m reaches), V3 direction
(contractions), V4 reconstruction (6.14).

Usage: python -B -u -m onedim.verification.b12d_theory_check [--workers N] [--tests V1,V2,V3,V4]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ..geometry import conduit, rectangle
from ..solver import Model, G
from .junctions import _solve_downstream, junction_relation
from .b12d_stability import _map

L_SIDE = 20.0
CFLS = (0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)


def sections(kind, w, hgt):
    c = conduit(0.0, 0.2, 0.2, 50.0)
    if kind == "pf":
        return c, rectangle(0.0, w)
    if kind == "pp":
        return c, conduit(0.0, w, hgt, 50.0)
    if kind == "ff":
        return rectangle(0.0, hgt), rectangle(0.0, w)          # hgt = narrow width here
    raise ValueError(kind)


def build(kind, w, hgt, h, q, ds, direction, recon):
    """direction +1: narrow -> wide (expansion); -1: wide -> narrow (contraction, the reverse case)."""
    n = int(round(L_SIDE / ds))
    nar, wid = sections(kind, w, hgt)
    if direction > 0:
        eta_dn = _solve_downstream(nar, wid, q, h)
        cells = [nar] * n + [wid] * n
        eta0 = np.r_[np.full(n, h), np.full(n, eta_dn)]
        bcr = {"type": "stage", "eta": eta_dn}
    else:
        eta_up = junction_relation(wid, nar, q, h)
        cells = [wid] * n + [nar] * n
        eta0 = np.r_[np.full(n, eta_up), np.full(n, h)]
        bcr = {"type": "stage", "eta": h}
    m = Model(cells, ds, bc_left={"type": "discharge", "Q": q}, bc_right=bcr, cfl=0.05, recon=recon)
    m.set_stage(eta0); m.Q = np.full(2 * n, q)
    return m, n


def _rho(m, x0, dt):
    m.cfl = 1e3
    k = len(x0); J = np.zeros((k, k))
    for i in range(k):
        hh = 1e-7 * max(abs(x0[i]), 1e-3)
        xp = x0.copy(); xp[i] += hh
        xm = x0.copy(); xm[i] -= hh
        J[:, i] = (_map(m, xp, dt) - _map(m, xm, dt)) / (2 * hh)
    return float(np.max(np.abs(np.linalg.eigvals(J))))


def predict(m, n, direction):
    """(N.1) from the steady state in m (one probe step at a tiny dt fills m.last)."""
    x0 = np.r_[m.A, m.Q]
    _map(m, x0, 1e-9)
    SL, SR = m.last["SL"], m.last["SR"]
    span = SR - SL
    a2 = SL * SR / span; al = SR / span; be = -SL / span
    eta = m.C.eta_from_area(m.A); h = m.C.depth_from_area(m.A)
    T = m.C.width_h(h)
    I = m.I
    if direction > 0:
        jn, jw, k = n - 1, n, n                     # narrow cell, wide cell, narrow interface
        A_n_L = float(I.area(np.array([eta[jn]]), rows=[k])[0])     # left state on the narrow interface
        A_n_R = float(I.area(np.array([eta[jw]]), rows=[k])[0])     # right state (wide cell) on it
        Aw = float(m.A[jw]); Uw = float(m.Q[jw] / m.A[jw])
        sQ = 1.0 if m.recon == "discharge_width" else A_n_R / Aw
        Ustar = sQ * float(m.Q[jw]) / A_n_R
        D1 = abs(a2[k]) + abs(a2[k - 1])
        D2 = abs(a2[k + 1]) + 2 * al[k + 1] * Uw + sQ * (abs(a2[k]) - 2 * be[k] * Ustar)
        if eta[jn] < eta[jw]:                       # (6.16b): receiving face at the narrow stage
            Aw_f = float(m.C.area(np.array([eta[jn]]), rows=[jw])[0])
            load = al[k] * A_n_L + (Aw_f - A_n_L)
        else:
            load = al[k] * A_n_L
        P = be[k] * sQ * G * load / T[jn]
        Tn = float(T[jn])
    else:
        jw, jn, k = n - 1, n, n                     # wide cell upstream, narrow cell downstream
        A_n_R = float(I.area(np.array([eta[jn]]), rows=[k])[0])
        A_w_L = float(I.area(np.array([eta[jw]]), rows=[k])[0])
        Aw = float(m.A[jw]); Uw = float(m.Q[jw] / m.A[jw])
        sQ = 1.0 if m.recon == "discharge_width" else A_w_L / Aw
        UstarL = sQ * float(m.Q[jw]) / A_w_L
        D1 = abs(a2[k]) + abs(a2[k + 1])
        D2 = sQ * (2 * al[k] * UstarL + abs(a2[k])) + abs(a2[k - 1]) - 2 * be[k - 1] * Uw
        P = al[k] * be[k] * sQ * G * A_n_R / T[jn]   # loss side: face at the cell's own stage
        Tn = float(T[jn])
    r_crit = (D1 + D2) / (D1 * D2 + P)
    r_cfl = 2.0 / max(D1, D2)
    return dict(D1=float(D1), D2=float(D2), P=float(P), dt_pred=float(min(r_crit, r_cfl) * m.ds[0]),
                binding="feedback (N.1)" if r_crit < r_cfl else "ordinary (2/D)", Tn=Tn, sQ=float(sQ))


def analyse(label, kind, w, hgt, h, q, ds, direction, recon="discharge_width", t_steady=40.0):
    t0 = time.time()
    m, n = build(kind, w, hgt, h, q, ds, direction, recon)
    m.run(t_steady)
    x0 = np.r_[m.A, m.Q]
    probe, _ = build(kind, w, hgt, h, q, ds, direction, recon)
    probe.A, probe.Q = m.A.copy(), m.Q.copy(); probe.cfl = 1.0
    m.cfl = 1.0
    dt1 = min(m.time_step(), probe.step(1.0))
    pr = predict(m, n, direction)
    rho = {c: _rho(m, x0, c * dt1) for c in CFLS}
    crit = None
    if rho[CFLS[0]] > 1 + 1e-6:
        crit = "< 0.05"
    else:
        for c0, c1 in zip(CFLS, CFLS[1:]):
            if rho[c0] <= 1 + 1e-6 < rho[c1]:
                lo, hi = c0, c1
                for _ in range(8):
                    mid = 0.5 * (lo + hi)
                    if _rho(m, x0, mid * dt1) > 1 + 1e-6:
                        hi = mid
                    else:
                        lo = mid
                crit = 0.5 * (lo + hi)
                break
    return dict(label=label, ds=ds, dt1=dt1, crit=crit, pred=pr, rho09=rho[0.9], secs=time.time() - t0)


def jobs(tests):
    J = []
    if "V1" in tests:
        J += [("V1", "pf 0.2 conduit -> 1 m", "pf", 1.0, None, 0.6, 0.05, 0.25, +1),
              ("V1", "pp -> 1.0 x 0.55", "pp", 1.0, 0.55, 0.6, 0.05, 0.25, +1),
              ("V1", "pp -> 1.0 x 0.40", "pp", 1.0, 0.40, 0.6, 0.05, 0.25, +1),
              ("V1", "ff 0.0667 -> 1 m", "ff", 1.0, 0.0667, 0.6, 0.05, 0.25, +1),
              ("V1", "ff 0.2 -> 1 m", "ff", 1.0, 0.2, 0.6, 0.05, 0.25, +1),
              ("V1", "ff 2 -> 10 m (B12a)", "ff", 10.0, 2.0, 1.0, 2.0, 0.25, +1),
              ("V1", "pf -> 0.3 m", "pf", 0.3, None, 0.6, 0.05, 0.25, +1),
              ("V1", "pf -> 2 m", "pf", 2.0, None, 0.6, 0.05, 0.25, +1),
              ("V1", "pf -> 1 m, h 0.4", "pf", 1.0, None, 0.4, 0.05, 0.25, +1),
              ("V1", "pf -> 1 m, h 1.0", "pf", 1.0, None, 1.0, 0.05, 0.25, +1)]
    if "V2" in tests:
        for ds in (0.5, 0.125):
            J += [("V2", f"pf 0.2 conduit -> 1 m, ds {ds}", "pf", 1.0, None, 0.6, 0.05, ds, +1),
                  ("V2", f"ff 0.0667 -> 1 m, ds {ds}", "ff", 1.0, 0.0667, 0.6, 0.05, ds, +1)]
    if "V3" in tests:
        J += [("V3", f"reverse, open {w} m -> conduit", "pf", w, None, 0.6, 0.05, 0.25, -1) for w in (0.3, 1.0, 5.0)]
    if "V4" in tests:
        J += [("V4", "pf 0.2 conduit -> 1 m with (6.14)", "pf", 1.0, None, 0.6, 0.05, 0.25, +1, "velocity")]
    return J


def fmt(r):
    c = r["crit"]; p = r["pred"]
    lin = f"{c * r['dt1']:.3e} s (CFL {c:.4f})" if isinstance(c, float) else (c or "stable to CFL 1.0")
    pc = p["dt_pred"] / r["dt1"]
    diff = f"{100 * (p['dt_pred'] / (c * r['dt1']) - 1):+.1f} %" if isinstance(c, float) else "-"
    return (f"{r['label']}\n    linearised dt_crit = {lin}; (N.1) predicts {p['dt_pred']:.3e} s (CFL {pc:.4f}, "
            f"binding: {p['binding']}); difference {diff}\n"
            f"    D1 = {p['D1']:.4g}, D2 = {p['D2']:.4g}, P = {p['P']:.4g}, T_n = {p['Tn']:.3e} m, s_Q = {p['sQ']:.4f}; "
            f"rho at CFL 0.9 = {r['rho09']:.4f}; dt(CFL=1) = {r['dt1']:.3e} s ({r['secs']:.0f} s)")


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    tests = sys.argv[sys.argv.index("--tests") + 1].split(",") if "--tests" in sys.argv else ["V1", "V2", "V3", "V4"]
    J = jobs(tests)
    T0 = time.time()
    print(f"Theory check of (N.1): {len(J)} cases on {workers} workers (the ds = 0.125 cases are the slowest)",
          flush=True)
    res = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(analyse, *j[1:]): j for j in J}
        for f in as_completed(futs):
            j = futs[f]
            try:
                res[j[1]] = f.result()
                print(f"[{time.time() - T0:6.0f} s] done: {j[0]} {j[1]}", flush=True)
            except Exception as e:
                res[j[1]] = None
                print(f"[{time.time() - T0:6.0f} s] ERROR {j[1]}: {e!r}", flush=True)
    print("\n================ RESULTS ================")
    for t in ("V1", "V2", "V3", "V4"):
        sel = [j for j in J if j[0] == t]
        if not sel:
            continue
        print(f"--- {t} ---")
        for j in sel:
            print(fmt(res[j[1]]) if res[j[1]] else f"{j[1]}: ERROR")
        print()
    # V2 summary: CFL_crit against ds (ds = 0.25 values come from V1)
    if "V2" in tests and "V1" in tests:
        for base in ("pf 0.2 conduit -> 1 m", "ff 0.0667 -> 1 m"):
            vals = []
            for ds, key in ((0.5, f"{base}, ds 0.5"), (0.25, base), (0.125, f"{base}, ds 0.125")):
                r = res.get(key)
                if r and isinstance(r["crit"], float):
                    vals.append((ds, r["crit"]))
            if vals:
                cs = [v for _, v in vals]
                print(f"V2 {base}: CFL_crit at ds = " + ", ".join(f"{d}: {c:.4f}" for d, c in vals)
                      + f"  (spread {100 * (max(cs) - min(cs)) / np.mean(cs):.1f} %)")
    print(f"\nDONE ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
