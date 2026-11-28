"""C2 verification (note 06_note_expansion_stability.md, draft 2.1, §§11-12), in the user's acceptance
order. C2 is the experimental option Model(interface_coupling="c2"); the explicit solver stays default.

Stage A (linear):     V8 steady-state null test, V9 linearisation (ten N.1 cases), V10 grid spacing,
                      V11 direction, V13 successive expansions (independent blocks and chain solve)
Stage B (nonlinear):  V5 eigenvector seeds (with V6 conservation and V7c energy source), V5b physical
                      disturbances, V7a steady expansion loss at CFL 0.9, V7b closed sloshing energy,
                      V12 consistency (dt series), V16 cost
Stage C (benchmarks): V14 = the phase B suite with ONEDIM_COUPLING=c2 (run by the PowerShell script)

Substitutions, stated in the output: the C3 reference (local subcycling) is replaced by the explicit
scheme at a globally small, stable step, which is the solution C3 approximates; C1 (relaxation) is not
implemented (V15 "reported only").

Usage: python -B -u -m onedim.verification.c2_tests --stage A|B [--workers N]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ..geometry import conduit, rectangle
from ..solver import Model, G
from .junctions import _solve_downstream, junction_relation, borda, _A
from .b12d_stability import _map

L_SIDE = 20.0
TEN = [("pf 0.2 conduit -> 1 m", "pf", 1.0, None, 0.6, 0.05),
       ("pp -> 1.0 x 0.55", "pp", 1.0, 0.55, 0.6, 0.05),
       ("pp -> 1.0 x 0.40", "pp", 1.0, 0.40, 0.6, 0.05),
       ("ff 0.0667 -> 1 m", "ff", 1.0, 0.0667, 0.6, 0.05),
       ("ff 0.2 -> 1 m", "ff", 1.0, 0.2, 0.6, 0.05),
       ("ff 2 -> 10 m (B12a)", "ff", 10.0, 2.0, 1.0, 2.0),
       ("pf -> 0.3 m", "pf", 0.3, None, 0.6, 0.05),
       ("pf -> 2 m", "pf", 2.0, None, 0.6, 0.05),
       ("pf -> 1 m, h 0.4", "pf", 1.0, None, 0.4, 0.05),
       ("pf -> 1 m, h 1.0", "pf", 1.0, None, 1.0, 0.05)]
CRIT = {"pf 0.2 conduit -> 1 m": 0.2072, "ff 0.0667 -> 1 m": 0.4884}      # linearised, status §12


# ------------------------------------------------------------------------------------------ helpers
def sections(kind, w, hgt):
    c = conduit(0.0, 0.2, 0.2, 50.0)
    if kind == "pf":
        return c, rectangle(0.0, w)
    if kind == "pp":
        return c, conduit(0.0, w, hgt, 50.0)
    return rectangle(0.0, hgt), rectangle(0.0, w)


def build(kind, w, hgt, h, q, ds=0.25, direction=+1, coupling="none", mode="independent"):
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
    m = Model(cells, ds, bc_left={"type": "discharge", "Q": q}, bc_right=bcr, cfl=0.05,
              interface_coupling=coupling, c2_mode=mode)
    m.set_stage(eta0); m.Q = np.full(2 * n, q)
    return m, n


def steady(m, t=40.0):
    m.coupling = "none"; m.cfl = 0.05
    m.run(m.t + t)
    return np.r_[m.A, m.Q]


def dt_unit(m):
    """dt at CFL 1 by the solver's own rule (6.21), cell and interface speeds (state unchanged)."""
    save = (m.A.copy(), m.Q.copy(), m.AC.copy(), m.M.copy(), m.t, m.nsteps, m.cfl, m.coupling)
    m.cfl = 1.0; m.coupling = "none"
    d1 = m.time_step()
    d2 = m.step(1.0)
    m.A, m.Q, m.AC, m.M, m.t, m.nsteps, m.cfl, m.coupling = save
    return min(d1, d2)


def jac_rho(m, x0, dt, coupling, mode="independent", want=False):
    m.coupling = coupling; m.c2_mode = mode; m.cfl = 1e3
    k = len(x0); J = np.zeros((k, k))
    for i in range(k):
        hh = 1e-7 * max(abs(x0[i]), 1e-3)
        xp = x0.copy(); xp[i] += hh
        xm = x0.copy(); xm[i] -= hh
        J[:, i] = (_map(m, xp, dt) - _map(m, xm, dt)) / (2 * hh)
    ev, V = np.linalg.eig(J)
    j = int(np.argmax(np.abs(ev)))
    if want:
        return float(abs(ev[j])), ev[j], V[:, j]
    return float(abs(ev[j]))


def energy(m):
    eta = m.stage()
    with np.errstate(divide="ignore", invalid="ignore"):
        ke = np.where(m.A > m.A_dry, m.Q ** 2 / (2 * np.where(m.A > 0, m.A, 1.0)), 0.0)
    pe = G * (m.A * eta - m.C.i1(eta))
    return float(np.sum((ke + pe) * m.ds))


# ------------------------------------------------------------------------------------------ stage A
def v8(i):
    lab, kind, w, hgt, h, q = TEN[i]
    m, n = build(kind, w, hgt, h, q)
    x0 = steady(m)
    dt = 0.9 * dt_unit(m)
    m.coupling = "none"; m.cfl = 1e3
    xe = _map(m, x0, dt)
    expl = float(np.max(np.abs(xe - x0)) / np.max(np.abs(x0)))
    m.coupling = "c2"; m.c2_blocks = 0
    _map(m, x0, dt)
    nb = m.c2_blocks
    fmax = float(np.max(np.abs(m.last["FA"])))
    corr = max((abs(c[0]) for c in m.last_c2["corr"]), default=0.0) / fmax if nb else 0.0
    return dict(test="V8", case=lab, blocks=nb, explicit_increment=expl, correction=corr,
                ok=bool(nb > 0 and corr <= 10 * max(expl, 1e-16)))


def v9(i, ds=0.25, test="V9"):
    lab, kind, w, hgt, h, q = TEN[i]
    m, n = build(kind, w, hgt, h, q, ds=ds)
    x0 = steady(m)
    d1 = dt_unit(m)
    re = jac_rho(m, x0, 0.9 * d1, "none")
    r9 = jac_rho(m, x0, 0.9 * d1, "c2")
    r5 = jac_rho(m, x0, 0.5 * d1, "c2")
    return dict(test=test, case=lab + (f", ds {ds}" if ds != 0.25 else ""), rho_explicit_09=re,
                rho_c2_09=r9, rho_c2_05=r5, ok=bool(r9 <= 1 + 1e-6 and r5 <= 1 + 1e-6))


def v10(i, ds):
    return v9(i, ds=ds, test="V10")


def v11(w):
    m, n = build("pf", w, None, 0.6, 0.05, direction=-1)
    x0 = steady(m)
    d1 = dt_unit(m)
    re = jac_rho(m, x0, 0.9 * d1, "none")
    m.c2_blocks = 0
    rc = jac_rho(m, x0, 0.9 * d1, "c2")
    return dict(test="V11", case=f"reverse, open {w} m -> conduit", rho_explicit_09=re, rho_c2_09=rc,
                c2_blocks=m.c2_blocks, ok=bool(abs(rc - re) < 1e-9 and m.c2_blocks == 0 and rc <= 1 + 1e-6))


def v13(kind, mid_cells):
    ds = 0.25; n = int(L_SIDE / ds)
    a = conduit(0.0, 0.2, 0.2, 50.0) if kind == "conduit" else rectangle(0.0, 0.2)
    b = rectangle(0.0, 0.6); c = rectangle(0.0, 2.0)
    cells = [a] * n + [b] * mid_cells + [c] * n
    m = Model(cells, ds, bc_left={"type": "discharge", "Q": 0.05}, bc_right={"type": "stage", "eta": 0.61}, cfl=0.05)
    m.set_stage(np.full(len(cells), 0.61)); m.Q = np.full(len(cells), 0.05)
    x0 = steady(m, 60.0)
    d1 = dt_unit(m)
    re = jac_rho(m, x0, 0.9 * d1, "none")
    ri = jac_rho(m, x0, 0.9 * d1, "c2", "independent")
    rc = jac_rho(m, x0, 0.9 * d1, "c2", "chain")
    return dict(test="V13", case=f"{kind} 0.2 -> 0.6 m ({mid_cells} cell{'s' if mid_cells > 1 else ''}) -> 2 m",
                rho_explicit_09=re, rho_independent_09=ri, rho_chain_09=rc,
                ok=bool(min(ri, rc) <= 1 + 1e-6), adopt=("independent" if ri <= 1 + 1e-6 else
                                                         ("chain" if rc <= 1 + 1e-6 else "neither")))


# ------------------------------------------------------------------------------------------ stage B
def _block_cells(n):
    return [n - 1, n]


def v5(i, eps, scheme):
    """scheme: 'explicit 0.9', 'explicit 0.9 x limit', 'c2 0.9'."""
    lab, kind, w, hgt, h, q = TEN[i]
    m, n = build(kind, w, hgt, h, q)
    x0 = steady(m)
    d1 = dt_unit(m)
    rho, lam, v = jac_rho(m, x0, 0.9 * d1, "none", want=True)
    v = np.real(v * np.exp(-1j * np.angle(v[np.argmax(np.abs(v))])))
    scale = np.abs(x0) + 1e-6
    v = v / np.max(np.abs(v) / scale)
    x = x0 + eps * v
    cfl = {"explicit 0.9": 0.9, "explicit 0.9 x limit": 0.9 * CRIT[lab], "c2 0.9": 0.9}[scheme]
    m.coupling = "c2" if scheme.startswith("c2") else "none"
    m.cfl = 1e3
    nn = m.N
    m.A = x[:nn].copy(); m.Q = x[nn:].copy(); m.AC = m.A.copy(); m.M = np.zeros(nn)
    m.vol_in = m.vol_out = m.sol_in = m.sol_out = 0.0; m.max_step_imbalance = 0.0
    V0 = m.water_volume(); S0 = m.solids()
    dt = cfl * d1
    cells = _block_cells(n)
    amp = []; w_int = 0.0; w_face = 0.0
    for s_ in range(2000):
        U = m.velocity()
        m.step(dt)
        L = m.last; r = dt / m.ds
        for c in cells:
            w_int += U[c] * m.ds[c] * (-r[c] * (L["FQ"][c + 1] - L["FQ"][c]))
            w_face += U[c] * m.ds[c] * (-r[c] * (L["WR"][c] - L["WL"][c]))
        dx = np.r_[m.A - x0[:nn], m.Q - x0[nn:]] / scale
        amp.append(float(np.max(np.abs(np.r_[dx[cells], dx[nn + np.array(cells)]]))))
        if not np.isfinite(amp[-1]) or amp[-1] > 1e3:
            break
    a = np.array(amp)
    k = min(200, len(a) - 1)
    rate = float((a[k] / a[0]) ** (1.0 / k)) if a[0] > 0 and k > 0 else float("nan")
    return dict(test="V5", case=lab, eps=eps, scheme=scheme, lam=float(rho), growth_per_step=rate,
                amp_start=float(a[0]), amp_end=float(a[-1]), steps=len(a),
                water_err=m.water_error(V0), max_step_imbalance=m.max_step_imbalance,
                solids_err=m.solids_error(S0), work_interface=w_int, work_face=w_face,
                c2_fallback=m.c2_fallback, c2_skipped=m.c2_skipped_ad)


def v5b(i, dist, scheme):
    lab, kind, w, hgt, h, q = TEN[i]
    m, n = build(kind, w, hgt, h, q)
    x0 = steady(m)
    d1 = dt_unit(m)
    cfl = 0.9 if scheme == "c2 0.9" else (0.1 if kind == "ff" else 0.1 * CRIT[lab])
    T = 100.0 if kind == "ff" else 60.0
    m.coupling = "c2" if scheme == "c2 0.9" else "none"
    m.cfl = 1e3
    if dist == "inflow +10 %":
        m.bc_left = dict(m.bc_left); m.bc_left["Q"] = 1.1 * q
    elif dist == "tailwater +5 cm":
        m.bc_right = dict(m.bc_right); m.bc_right["eta"] = m.bc_right["eta"] + 0.05
    else:
        hn = m.depth()[n - 1]; Tn = float(m.C.width_h(np.array([hn]), rows=[n - 1])[0])
        m.A[n - 1] += Tn * 0.02 if kind == "ff" else Tn * 0.02
    V0 = m.water_volume(); m.vol_in = m.vol_out = 0.0; m.max_step_imbalance = 0.0
    dt = cfl * d1
    t0 = m.t; stg = []; ts = []
    while m.t < t0 + T:
        m.step(min(dt, t0 + T - m.t))
        e = m.stage()
        stg.append(e[[n - 1, n]].copy()); ts.append(m.t - t0)
    stg = np.array(stg); ts = np.array(ts)
    first = (ts > 0.1 * T) & (ts < 0.2 * T); last = ts > 0.9 * T
    amp_first = float(np.max(np.ptp(stg[first], axis=0))); amp_last = float(np.max(np.ptp(stg[last], axis=0)))
    A1, Q1 = m.A.copy(), m.Q.copy()
    m.step(min(dt, 1e-3)); resid = float(np.max(np.abs(m.A - A1)) / np.max(np.abs(A1)))
    return dict(test="V5b", case=lab, dist=dist, scheme=scheme, T=T, cfl=cfl, amp_first=amp_first,
                amp_last=amp_last, energy_end=energy(m), water_err=m.water_error(V0),
                A_end=A1.tolist(), Q_end=Q1.tolist(), resid=resid, c2_fallback=m.c2_fallback,
                c2_skipped=m.c2_skipped_ad)


def v7a(i, T=1000.0):
    """Steady expansion loss with C2 at CFL 0.9, against relation and Borda."""
    lab, kind, w, hgt, h, q = TEN[i]
    m, n = build(kind, w, hgt, h, q, coupling="c2")
    m.cfl = 0.9; m.coupling = "c2"
    m.run(T)
    nar, wid = sections(kind, w, hgt)
    eta = m.stage(); qq = n // 4
    Qf = float(np.mean(np.abs(m.last["FA"])))
    E = eta + (Qf / m.A) ** 2 / (2 * G)
    loss = float(np.mean(E[qq:2 * qq]) - np.mean(E[-2 * qq:-qq]))
    eta_dn = m.bc_right["eta"]
    rel_up = junction_relation(nar, wid, q, eta_dn)
    Ea = rel_up + (q / _A(nar, rel_up)) ** 2 / (2 * G); Eb = eta_dn + (q / _A(wid, eta_dn)) ** 2 / (2 * G)
    bo = borda(nar, wid, q, float(np.mean(eta[qq:2 * qq])), eta_dn)
    osc = float(np.ptp([m.stage()[n - 1]]))
    return dict(test="V7a", case=lab, loss=loss, loss_relation=Ea - Eb, borda=bo,
                err_rel=(loss - (Ea - Eb)) / (Ea - Eb), err_borda=(loss - bo) / bo,
                stage_up=float(np.mean(eta[qq:2 * qq])), stage_up_rel=rel_up, c2_fallback=m.c2_fallback,
                c2_skipped=m.c2_skipped_ad, ok=bool(abs((loss - (Ea - Eb)) / (Ea - Eb)) < 0.01))


def v7b(kind, scheme, T=100.0):
    """Closed, frictionless reach with an expansion; tilted initial stage, Q = 0."""
    ds = 0.25; n = int(L_SIDE / ds)
    nar = conduit(0.0, 0.2, 0.2, 50.0) if kind == "pf" else rectangle(0.0, 0.2)
    wid = rectangle(0.0, 1.0)
    cells = [nar] * n + [wid] * n
    m = Model(cells, ds, bc_left={"type": "wall"}, bc_right={"type": "wall"}, cfl=0.05,
              interface_coupling="c2" if scheme == "c2 0.9" else "none")
    x = ds * (np.arange(2 * n) + 0.5)
    m.set_stage(0.6 + 0.05 * (x / x[-1] - 0.5))
    d1 = dt_unit(m)
    cfl = 0.9 if scheme == "c2 0.9" else (0.1 if kind == "ff" else 0.1 * CRIT["pf 0.2 conduit -> 1 m"])
    m.cfl = 1e3; dt = cfl * d1
    E0 = energy(m); Ep = E0; worst = 0.0; V0 = m.water_volume()
    es = []
    while m.t < T:
        m.step(min(dt, T - m.t))
        E = energy(m)
        worst = max(worst, (E - Ep) / E0)
        Ep = E; es.append(E)
    return dict(test="V7b", case=f"closed reach, {'conduit' if kind == 'pf' else 'open 0.2 m'} -> 1 m",
                scheme=scheme, cfl=cfl, E0=E0, E_end=es[-1], dissipated=(E0 - es[-1]) / E0,
                worst_step_increase=worst, water_err=m.water_error(V0), c2_blocks=m.c2_blocks,
                c2_fallback=m.c2_fallback, c2_skipped=m.c2_skipped_ad)


def v12(scheme_cfl):
    """Consistency: conduit -> 1 m, 2 cm bump in the last conduit cell, 10 s."""
    lab, kind, w, hgt, h, q = TEN[0]
    m, n = build(kind, w, hgt, h, q)
    x0 = steady(m)
    d1 = dt_unit(m)
    scheme, cfl = scheme_cfl
    m.coupling = "c2" if scheme == "c2" else "none"; m.cfl = 1e3
    hn = m.depth()[n - 1]; Tn = float(m.C.width_h(np.array([hn]), rows=[n - 1])[0])
    m.A[n - 1] += Tn * 0.02
    t0 = m.t
    while m.t < t0 + 10.0 - 1e-12:
        m.step(min(cfl * d1, t0 + 10.0 - m.t))
    return dict(test="V12", scheme=scheme, cfl=cfl, A=m.A.tolist(), Q=m.Q.tolist(), n=n)


def v16():
    lab, kind, w, hgt, h, q = TEN[0]
    out = {}
    for coup in ("none", "c2"):
        m, n = build(kind, w, hgt, h, q)
        steady(m, 5.0)
        d1 = dt_unit(m)
        m.coupling = coup; m.cfl = 1e3
        t0 = time.perf_counter()
        for _ in range(2000):
            m.step(0.1 * d1)
        out[coup] = (time.perf_counter() - t0) / 2000
    return dict(test="V16", per_step_explicit=out["none"], per_step_c2=out["c2"],
                overhead=out["c2"] / out["none"] - 1.0)


# ------------------------------------------------------------------------------------------ driver
def jobs(stage):
    J = []
    if stage == "A":
        J += [(f"V8 {TEN[i][0]}", v8, (i,)) for i in range(10)]
        J += [(f"V9 {TEN[i][0]}", v9, (i,)) for i in range(10)]
        J += [(f"V10 {TEN[i][0]} ds {d}", v10, (i, d)) for i in (0, 3) for d in (0.5, 0.125)]
        J += [(f"V11 reverse {w}", v11, (w,)) for w in (0.3, 1.0, 5.0)]
        J += [(f"V13 {k} {c}", v13, (k, c)) for k in ("open", "conduit") for c in (1, 4)]
    else:
        for i in (0, 3):
            for eps in (1e-6, 1e-3, 1e-1):
                for sch in ("explicit 0.9", "explicit 0.9 x limit", "c2 0.9"):
                    J.append((f"V5 {TEN[i][0]} eps {eps:g} {sch}", v5, (i, eps, sch)))
            for dist in ("inflow +10 %", "tailwater +5 cm", "2 cm bump"):
                for sch in ("c2 0.9", "explicit stable"):
                    J.append((f"V5b {TEN[i][0]} {dist} {sch}", v5b, (i, dist, sch)))
            J.append((f"V7a {TEN[i][0]}", v7a, (i,)))
        for k in ("pf", "ff"):
            for sch in ("c2 0.9", "explicit stable"):
                J.append((f"V7b {k} {sch}", v7b, (k, sch)))
        for sc in (("c2", 0.9), ("c2", 0.45), ("c2", 0.225), ("explicit", 0.1), ("explicit", 0.01)):
            J.append((f"V12 {sc[0]} {sc[1]}", v12, (sc,)))
        J.append(("V16 cost", v16, ()))
    return J


def report_A(res):
    out = []
    def P(ok): return "PASS" if ok else "FAIL"
    print("\n--- V8 steady-state null test (one C2 step at CFL 0.9 from the steady state) ---")
    for r in [r for r in res if r["test"] == "V8"]:
        print(f"{P(r['ok'])}  {r['case']:22s} blocks {r['blocks']}, |C2 mass-flux correction|/|F| = {r['correction']:.2e}, "
              f"explicit increment (steady residual) {r['explicit_increment']:.2e}")
        out.append(r["ok"])
    print("    (criterion: correction <= 10 x the steady residual; an absolute 1e-12 is not reachable because the "
          "steady states are converged to ~1e-10, not to round-off)")
    for t, title in (("V9", "linearisation, ten N.1 cases"), ("V10", "grid spacing")):
        print(f"\n--- {t} {title} (spectral radius) ---")
        for r in [r for r in res if r["test"] == t]:
            print(f"{P(r['ok'])}  {r['case']:30s} explicit CFL 0.9: {r['rho_explicit_09']:.4f}   C2 CFL 0.9: "
                  f"{r['rho_c2_09']:.4f}   C2 CFL 0.5: {r['rho_c2_05']:.4f}")
            out.append(r["ok"])
    print("\n--- V11 direction (contractions: C2 must stay inactive) ---")
    for r in [r for r in res if r["test"] == "V11"]:
        print(f"{P(r['ok'])}  {r['case']:30s} explicit {r['rho_explicit_09']:.6f}  C2 {r['rho_c2_09']:.6f}  C2 blocks {r['c2_blocks']}")
        out.append(r["ok"])
    print("\n--- V13 successive expansions (CFL 0.9) ---")
    for r in [r for r in res if r["test"] == "V13"]:
        print(f"{P(r['ok'])}  {r['case']:38s} explicit {r['rho_explicit_09']:.4f}  independent {r['rho_independent_09']:.4f}  "
              f"chain {r['rho_chain_09']:.4f}  -> adopt: {r['adopt']}")
        out.append(r["ok"])
    return out


def report_B(res):
    out = []
    def P(ok): return "PASS" if ok else "FAIL"
    print("\n--- V5 eigenvector seeds (2000 steps), with V6 conservation and V7c energy source ---")
    for r in sorted([r for r in res if r["test"] == "V5"], key=lambda x: (x["case"], x["eps"], x["scheme"])):
        grows = r["growth_per_step"] > 1 + 1e-4
        ok = (not grows) if r["scheme"] != "explicit 0.9" else True
        cons = r["max_step_imbalance"] < 1e-12 or r["water_err"] < 1e-10
        print(f"{P(ok and cons)}  {r['case']:22s} eps {r['eps']:7.0e} {r['scheme']:21s} growth/step {r['growth_per_step']:.5f} "
              f"(|lambda| explicit 0.9 = {r['lam']:.4f}); amplitude {r['amp_start']:.1e} -> {r['amp_end']:.1e} in {r['steps']} steps; "
              f"water err {r['water_err']:.1e}, step imbalance {r['max_step_imbalance']:.1e}, solids err {r['solids_err']:.1e}; "
              f"work: interface {r['work_interface']:+.3e}, face {r['work_face']:+.3e}")
        out.append(ok and cons)
    print("    (explicit 0.9 is expected to grow; it is reported, not gated)")
    print("\n--- V5b physical disturbances: C2 at CFL 0.9 against the explicit scheme at a stable step ---")
    pairs = {}
    for r in [r for r in res if r["test"] == "V5b"]:
        pairs.setdefault((r["case"], r["dist"]), {})[r["scheme"]] = r
    for (case, dist), d in sorted(pairs.items()):
        c, e = d.get("c2 0.9"), d.get("explicit stable")
        if not (c and e):
            continue
        A1, A2 = np.array(c["A_end"]), np.array(e["A_end"]); Q1, Q2 = np.array(c["Q_end"]), np.array(e["Q_end"])
        dA = float(np.max(np.abs(A1 - A2)) / np.max(np.abs(A2))); dQ = float(np.max(np.abs(Q1 - Q2)) / np.max(np.abs(Q2)))
        no_growth = c["amp_last"] <= max(c["amp_first"], 1e-6)
        both_steady = c["resid"] < 1e-8 and e["resid"] < 1e-8
        agree = (dA < 1e-6 and dQ < 1e-6) if both_steady else True
        ok = no_growth and agree and abs(c["water_err"]) < 1e-10
        print(f"{P(ok)}  {case:22s} {dist:16s} C2: oscillation {c['amp_first']:.2e} -> {c['amp_last']:.2e} m; explicit "
              f"(CFL {e['cfl']:.4f}): {e['amp_first']:.2e} -> {e['amp_last']:.2e} m; end states differ dA {dA:.1e}, dQ {dQ:.1e} "
              f"after {c['T']:.0f} s (steady: C2 {c['resid']:.0e}, explicit {e['resid']:.0e}); water err C2 {c['water_err']:.1e}; "
              f"C2 fallback {c['c2_fallback']}, skipped {c['c2_skipped']}")
        out.append(ok)
    print("\n--- V7a steady expansion loss with C2 at CFL 0.9 (1000 s) ---")
    for r in [r for r in res if r["test"] == "V7a"]:
        print(f"{P(r['ok'])}  {r['case']:22s} loss {r['loss']:.5f} m, relation {r['loss_relation']:.5f} ({100 * r['err_rel']:+.2f} %), "
              f"Borda {r['borda']:.5f} ({100 * r['err_borda']:+.2f} %); upstream stage {r['stage_up']:.4f} (relation {r['stage_up_rel']:.4f}); "
              f"fallback {r['c2_fallback']}, skipped {r['c2_skipped']}")
        out.append(r["ok"])
    print("\n--- V7b closed frictionless reach with an expansion (100 s) ---")
    v7 = {}
    for r in [r for r in res if r["test"] == "V7b"]:
        v7.setdefault(r["case"], {})[r["scheme"]] = r
    for case, d in v7.items():
        c, e = d.get("c2 0.9"), d.get("explicit stable")
        if not (c and e):
            continue
        rate = c["dissipated"] / e["dissipated"] if e["dissipated"] > 0 else float("nan")
        ok = c["worst_step_increase"] <= 1e-12 and 0.8 <= rate <= 1.2
        print(f"{P(ok)}  {case:32s} C2 CFL 0.9: worst step-to-step energy increase {c['worst_step_increase']:.1e}, dissipated "
              f"{100 * c['dissipated']:.3f} %; explicit (CFL {e['cfl']:.4f}): {100 * e['dissipated']:.3f} %, worst increase "
              f"{e['worst_step_increase']:.1e}; ratio {rate:.3f}; C2 blocks {c['c2_blocks']}, fallback {c['c2_fallback']}")
        out.append(ok)
    print("\n--- V12 consistency (conduit -> 1 m, 2 cm bump, state at 10 s against explicit CFL 0.01) ---")
    v12r = {(r["scheme"], r["cfl"]): r for r in res if r["test"] == "V12"}
    ref = v12r.get(("explicit", 0.01))
    if ref:
        Aref = np.array(ref["A"])
        errs = []
        for key in (("c2", 0.9), ("c2", 0.45), ("c2", 0.225), ("explicit", 0.1)):
            if key in v12r:
                e = float(np.sum(np.abs(np.array(v12r[key]["A"]) - Aref)) / np.sum(np.abs(Aref)))
                errs.append((key, e))
                print(f"      {key[0]:8s} CFL {key[1]:<6} L1 difference in A: {e:.3e}")
        c2e = [e for (k, e) in errs if k[0] == "c2"]
        if len(c2e) == 3:
            r1, r2 = c2e[0] / c2e[1], c2e[1] / c2e[2]
            ok = 1.5 <= r1 <= 2.6 and 1.5 <= r2 <= 2.6
            print(f"{P(ok)}  ratios {r1:.2f}, {r2:.2f} (first order: about 2)")
            out.append(ok)
    for r in [r for r in res if r["test"] == "V16"]:
        print(f"\n--- V16 cost ---\n      per step: explicit {1e3 * r['per_step_explicit']:.3f} ms, C2 {1e3 * r['per_step_c2']:.3f} ms "
              f"(overhead {100 * r['overhead']:+.1f} %)")
    print("\n--- V15 ---\n      C3 (local subcycling) replaced by the explicit scheme at a globally small, stable step "
          "(V5b, V7b, V12); C1 (relaxation) not implemented.")
    return out


def main():
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "A"
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    J = jobs(stage)
    T0 = time.time()
    print(f"C2 verification, stage {stage}: {len(J)} jobs on {workers} workers", flush=True)
    res = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, *args): lab for lab, fn, args in J}
        for f in as_completed(futs):
            lab = futs[f]
            try:
                res.append(f.result())
                print(f"[{time.time() - T0:6.0f} s] done: {lab}", flush=True)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[{time.time() - T0:6.0f} s] ERROR {lab}: {e!r}", flush=True)
                res.append(dict(test="ERROR", case=lab))
    print("\n================ RESULTS ================")
    oks = report_A(res) if stage == "A" else report_B(res)
    n_err = sum(1 for r in res if r["test"] == "ERROR")
    print(f"\nRESULT stage {stage}: {sum(oks)} pass, {len(oks) - sum(oks)} fail, {n_err} errors  ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
