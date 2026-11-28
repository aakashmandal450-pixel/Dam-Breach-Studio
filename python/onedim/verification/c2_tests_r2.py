"""C2 verification, revision 2 (user decisions, 2026-11-28, after stages A-C):

V5r   seeded disturbance measured against an unseeded baseline run, delta(t) = |x_seeded - x_baseline|;
      seeds below the baseline noise floor are INCONCLUSIVE; the explicit scheme at CFL 0.9 is the
      positive control and must grow.
V5br  physical disturbances; C2 (CFL 0.9) against a stable explicit reference at the same physical
      times and forcing; oscillation envelope in 5 s windows after the disturbance reaches the junction,
      ratio <= 1.25; end states compared only after both runs are steady (residual < 1e-10), otherwise
      INCONCLUSIVE.
V7br  closed frictionless reach: explicit and C2 at the same CFL (control), C2 at 0.9, explicit at small
      CFL; cumulative energy drift and systematic growth as well as single-step increases.
V12r  consistency with CFL 0.9, 0.45, 0.225, 0.1125 against explicit CFL 0.01; first order in the
      asymptotic range (r^2 P < 1: the 0.225 -> 0.1125 pair) and an absolute bound: max stage difference
      <= 1 mm (5 % of the 2 cm disturbance).
COST  total runtime = cost per step x number of steps over 20 s, C2 at CFL 0.9 against the explicit
      scheme at 0.9 x its own critical CFL ((N.1) at the steady state), for the B12d outlet and two
      breach-scale geometries.

Steady states are now converged with C2 at CFL 0.9 (cheap; the steady state is the same as the
explicit scheme's, V8) to a relative change < 1e-12 per 500 steps, or 3000 s.

Usage: python -B -u -m onedim.verification.c2_tests_r2 [--workers N] [--only V5r,V7br,...]
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from ..geometry import conduit, rectangle
from ..solver import Model, G
from .junctions import _solve_downstream
from .b12d_stability import _map
from .b12d_theory_check import predict
from .c2_tests import energy, jac_rho, dt_unit

L_SIDE = 20.0
DS = 0.25
GEOMS = {
    "pf 0.2 conduit -> 1 m": (lambda: conduit(0.0, 0.2, 0.2, 50.0), lambda: rectangle(0.0, 1.0), 0.6, 0.05),
    "ff 0.0667 -> 1 m": (lambda: rectangle(0.0, 0.0667), lambda: rectangle(0.0, 1.0), 0.6, 0.05),
    "breach: conduit 0.5 x 0.5 -> 20 m, h 3 m": (lambda: conduit(0.0, 0.5, 0.5, 50.0), lambda: rectangle(0.0, 20.0), 3.0, 0.75),
    "breach: open 2 m -> 40 m, h 2 m": (lambda: rectangle(0.0, 2.0), lambda: rectangle(0.0, 40.0), 2.0, 8.0),
}
CRIT = {"pf 0.2 conduit -> 1 m": 0.2072, "ff 0.0667 -> 1 m": 0.4884}


def build(name, coupling="none"):
    nar_f, wid_f, h, q = GEOMS[name]
    nar, wid = nar_f(), wid_f()
    n = int(round(L_SIDE / DS))
    eta_dn = _solve_downstream(nar, wid, q, h)
    m = Model([nar] * n + [wid] * n, DS, bc_left={"type": "discharge", "Q": q},
              bc_right={"type": "stage", "eta": eta_dn}, cfl=0.9, interface_coupling=coupling)
    m.set_stage(np.r_[np.full(n, h), np.full(n, eta_dn)]); m.Q = np.full(2 * n, q)
    return m, n, q


CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_steady_cache")


def _cache_file(name):
    return os.path.join(CACHE, "".join(ch if ch.isalnum() else "_" for ch in name) + ".npz")


def make_steady(name, tol=1e-12, t_max=3000.0):
    """Steady state with C2 at CFL 0.9 (stable; same steady state as the explicit scheme, V8), cached."""
    m, n, q = build(name, coupling="c2")
    m.cfl = 0.9
    ok = m.run_to_steady(tol=tol, check_every=500, t_max=t_max)
    os.makedirs(CACHE, exist_ok=True)
    np.savez(_cache_file(name), A=m.A, Q=m.Q, res=np.array(m.steady_residual), ok=ok, t=m.t)
    return dict(name=name, ok=bool(ok), res=m.steady_residual, t=m.t)


def converge(m, name=None):
    """Load the cached steady state into m; returns (state, residual, ok)."""
    d = np.load(_cache_file(name))
    m.A = d["A"].copy(); m.Q = d["Q"].copy(); m.AC = np.zeros(m.N); m.M = np.zeros(m.N)
    m.coupling = "none"
    return np.r_[m.A, m.Q], tuple(d["res"]), bool(d["ok"])


def _set(m, x):
    nn = m.N
    m.A = x[:nn].copy(); m.Q = x[nn:].copy(); m.AC = m.A.copy(); m.M = np.zeros(nn)


# ------------------------------------------------------------------------------------------ V5r
def v5r(name, eps, scheme, steps=2000):
    m, n, q = build(name)
    x0, res, ok = converge(m, name)
    d1 = dt_unit(m)
    rho, lam, v = jac_rho(m, x0, 0.9 * d1, "none", want=True)
    v = np.real(v * np.exp(-1j * np.angle(v[np.argmax(np.abs(v))])))
    scale = np.abs(x0) + 1e-6
    v = v / np.max(np.abs(v) / scale)
    cfl = {"c2 0.9": 0.9, "explicit 0.9": 0.9, "explicit 0.9 x limit": 0.9 * CRIT[name]}[scheme]
    coup = "c2" if scheme.startswith("c2") else "none"
    dt = cfl * d1
    cells = [n - 1, n]
    idx = np.r_[cells, m.N + np.array(cells)]

    def run(x):
        mm, _, _ = build(name, coupling=coup)
        _set(mm, x); mm.cfl = 1e3; mm.vol_in = mm.vol_out = 0.0; mm.max_step_imbalance = 0.0
        V0 = mm.water_volume()
        traj = []
        for _ in range(steps):
            mm.step(dt)
            traj.append(np.r_[mm.A, mm.Q][idx].copy())
            if not np.all(np.isfinite(traj[-1])) or np.max(np.abs(traj[-1])) > 1e6:
                break
        return np.array(traj), mm.water_error(V0), mm.max_step_imbalance

    base, wb, _ = run(x0)
    seed, ws, imb = run(x0 + eps * v)
    k = min(len(base), len(seed))
    sc = scale[idx]
    delta = np.max(np.abs(seed[:k] - base[:k]) / sc, axis=1)
    floor = float(np.max(np.abs(base[:k] - x0[idx]) / sc))           # baseline drift = noise floor
    k2 = min(200, k - 1)
    rate = float((delta[k2] / delta[0]) ** (1.0 / k2)) if delta[0] > 0 else float("nan")
    if scheme == "explicit 0.9":
        verdict = "PASS" if rate > 1.0 + 1e-4 else "FAIL"            # positive control must grow
    elif eps <= 10 * floor:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS" if (rate <= 1.0 + 1e-4 and delta[-1] <= delta[0]) else "FAIL"
    return dict(test="V5r", case=name, eps=eps, scheme=scheme, verdict=verdict, rate=rate, lam=float(rho),
                delta0=float(delta[0]), delta_end=float(delta[-1]), floor=floor, steps=k, steady_res=res,
                water_err=max(abs(wb), abs(ws)), imbalance=imb)


# ------------------------------------------------------------------------------------------ V5br
def v5br(name, dist, scheme):
    m, n, q = build(name)
    x0, res0, _ = converge(m, name)
    d1 = dt_unit(m)
    cfl = 0.9 if scheme == "c2 0.9" else (0.1 if name.startswith("ff") else 0.5 * CRIT[name])
    coup = "c2" if scheme == "c2 0.9" else "none"
    mm, _, _ = build(name, coupling=coup)
    _set(mm, x0); mm.cfl = 1e3
    if dist == "inflow +10 %":
        mm.bc_left = dict(mm.bc_left); mm.bc_left["Q"] = 1.1 * q
    elif dist == "tailwater +5 cm":
        mm.bc_right = dict(mm.bc_right); mm.bc_right["eta"] += 0.05
    else:
        hn = mm.depth()[n - 1]; Tn = float(mm.C.width_h(np.array([hn]), rows=[n - 1])[0])
        mm.A[n - 1] += Tn * 0.02
    V0 = mm.water_volume(); mm.vol_in = mm.vol_out = 0.0
    dt = cfl * d1
    T = 100.0 if name.startswith("ff") else 60.0
    tt, st = [], []
    next_s = 0.0
    while mm.t < T - 1e-12:
        mm.step(min(dt, T - mm.t))
        if mm.t >= next_s:
            tt.append(mm.t); st.append(mm.stage()[[n - 1, n]].copy()); next_s += 0.05
    tt = np.array(tt); st = np.array(st)
    w_err = mm.water_error(V0)
    # continue to a steady state for the end-state comparison
    mm.cfl = cfl
    steady = mm.run_to_steady(tol=1e-10, check_every=500, t_max=mm.t + 1500.0)
    return dict(test="V5br", case=name, dist=dist, scheme=scheme, cfl=cfl, t=tt.tolist(), st=st.tolist(),
                A_end=mm.A.tolist(), Q_end=mm.Q.tolist(), steady=bool(steady), resid=mm.steady_residual,
                water_err=w_err, c2_fallback=mm.c2_fallback, c2_skipped=mm.c2_skipped_ad, steady0=res0)


# ------------------------------------------------------------------------------------------ V7br
def v7br(kind, scheme, cfl, T=100.0):
    nn = int(L_SIDE / DS)
    nar = conduit(0.0, 0.2, 0.2, 50.0) if kind == "pf" else rectangle(0.0, 0.2)
    cells = [nar] * nn + [rectangle(0.0, 1.0)] * nn
    m = Model(cells, DS, bc_left={"type": "wall"}, bc_right={"type": "wall"}, cfl=0.05,
              interface_coupling="c2" if scheme == "c2" else "none")
    x = DS * (np.arange(2 * nn) + 0.5)
    m.set_stage(0.6 + 0.05 * (0.5 - x / x[-1]))
    d1 = dt_unit(m)
    m.cfl = 1e3; dt = cfl * d1
    E0 = energy(m); Ep = E0; worst = 0.0; drift_max = -np.inf; V0 = m.water_volume()
    ts, es = [0.0], [E0]
    while m.t < T - 1e-12:
        m.step(min(dt, T - m.t))
        E = energy(m)
        worst = max(worst, (E - Ep) / E0); Ep = E
        drift_max = max(drift_max, (E - E0) / E0)
        ts.append(m.t); es.append(E)
    ts = np.array(ts); es = np.array(es)
    win = [float(np.mean(es[(ts >= a) & (ts < a + 10.0)])) for a in np.arange(0.0, T, 10.0)]
    win_up = max(0.0, max(((b - a) / E0 for a, b in zip(win, win[1:])), default=0.0))
    half = ts >= 0.5 * T
    slope = float(np.polyfit(ts[half], es[half] / E0, 1)[0])
    return dict(test="V7br", kind=kind, scheme=scheme, cfl=cfl, dissipated=(E0 - es[-1]) / E0, worst_step=worst,
                drift_max=drift_max, window_up=win_up, slope=slope, water_err=m.water_error(V0),
                c2_blocks=m.c2_blocks, c2_fallback=m.c2_fallback)


# ------------------------------------------------------------------------------------------ V12r
def v12r(scheme, cfl):
    name = "pf 0.2 conduit -> 1 m"
    m, n, q = build(name)
    x0, _, _ = converge(m, name)
    d1 = dt_unit(m)
    mm, _, _ = build(name, coupling="c2" if scheme == "c2" else "none")
    _set(mm, x0); mm.cfl = 1e3
    hn = mm.depth()[n - 1]; Tn = float(mm.C.width_h(np.array([hn]), rows=[n - 1])[0])
    mm.A[n - 1] += Tn * 0.02
    while mm.t < 10.0 - 1e-12:
        mm.step(min(cfl * d1, 10.0 - mm.t))
    return dict(test="V12r", scheme=scheme, cfl=cfl, A=mm.A.tolist(), eta=mm.stage().tolist())


# ------------------------------------------------------------------------------------------ COST
def cost(name, scheme):
    m, n, q = build(name)
    x0, res, _ = converge(m, name)
    d1 = dt_unit(m)
    if scheme == "c2 0.9":
        cfl, coup = 0.9, "c2"
        crit = None
    else:
        pr = predict(m, n, +1)
        crit = pr["dt_pred"] / d1
        cfl, coup = 0.9 * min(crit, 1.0), "none"
    mm, _, _ = build(name, coupling=coup)
    _set(mm, x0); mm.cfl = 1e3
    hn = mm.depth()[n - 1]; Tn = float(mm.C.width_h(np.array([hn]), rows=[n - 1])[0])
    mm.A[n - 1] += Tn * 0.02                                         # the same small disturbance
    t0 = time.perf_counter(); steps = 0
    while mm.t < 20.0 - 1e-12:
        mm.step(min(cfl * d1, 20.0 - mm.t)); steps += 1
    wall = time.perf_counter() - t0
    return dict(test="COST", case=name, scheme=scheme, cfl=cfl, crit_pred=crit, steps=steps, wall=wall,
                per_step=wall / steps, eta=mm.stage().tolist(), finite=bool(np.all(np.isfinite(mm.A))))


# ------------------------------------------------------------------------------------------ driver
def jobs(only):
    J = []
    if "V5r" in only:
        for name in ("pf 0.2 conduit -> 1 m", "ff 0.0667 -> 1 m"):
            for eps in (1e-6, 1e-3, 1e-1):
                for sch in ("c2 0.9", "explicit 0.9", "explicit 0.9 x limit"):
                    J.append((f"V5r {name} eps {eps:g} {sch}", v5r, (name, eps, sch)))
    if "V5br" in only:
        for name in ("pf 0.2 conduit -> 1 m", "ff 0.0667 -> 1 m"):
            for dist in ("inflow +10 %", "tailwater +5 cm", "2 cm bump"):
                for sch in ("c2 0.9", "explicit reference"):
                    J.append((f"V5br {name} {dist} {sch}", v5br, (name, dist, sch)))
    if "V7br" in only:
        for sch, c in (("explicit", 0.1), ("explicit", 0.45), ("c2", 0.45), ("c2", 0.9)):
            J.append((f"V7br ff {sch} {c}", v7br, ("ff", sch, c)))
        for sch, c in (("explicit", 0.0207), ("explicit", 0.186), ("c2", 0.186), ("c2", 0.9)):
            J.append((f"V7br pf {sch} {c}", v7br, ("pf", sch, c)))
    if "V12r" in only:
        for sc in (("c2", 0.9), ("c2", 0.45), ("c2", 0.225), ("c2", 0.1125), ("explicit", 0.1), ("explicit", 0.01)):
            J.append((f"V12r {sc[0]} {sc[1]}", v12r, sc))
    if "COST" in only:
        for name in GEOMS:
            for sch in ("c2 0.9", "explicit 0.9 x critical"):
                J.append((f"COST {name} {sch}", cost, (name, sch)))
    return J


def report(res):
    tally = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0}

    def mark(v):
        tally[v] += 1
        return v

    print("\n--- V5r seeded disturbance against an unseeded baseline (2000 steps) ---")
    for r in sorted([r for r in res if r["test"] == "V5r"], key=lambda x: (x["case"], x["eps"], x["scheme"])):
        print(f"{mark(r['verdict']):12s} {r['case']:22s} eps {r['eps']:7.0e} {r['scheme']:21s} growth/step {r['rate']:.5f}; "
              f"delta {r['delta0']:.1e} -> {r['delta_end']:.1e}; noise floor {r['floor']:.1e} (steady residual "
              f"{r['steady_res'][0]:.0e}); water {r['water_err']:.1e}, step imbalance {r['imbalance']:.1e}")
    print("    (explicit 0.9 is the positive control: PASS means it grows, as it must)")

    print("\n--- V5br physical disturbances: C2 at CFL 0.9 against the stable explicit reference ---")
    pairs = {}
    for r in [r for r in res if r["test"] == "V5br"]:
        pairs.setdefault((r["case"], r["dist"]), {})[r["scheme"]] = r
    for (case, dist), d in sorted(pairs.items()):
        c, e = d.get("c2 0.9"), d.get("explicit reference")
        if not (c and e):
            continue
        tc, sc = np.array(c["t"]), np.array(c["st"]); te, se = np.array(e["t"]), np.array(e["st"])
        se_i = np.column_stack([np.interp(tc, te, se[:, j]) for j in range(2)])
        dev = np.max(np.abs(se_i - se_i[-1]), axis=1)
        arrive = tc[np.argmax(dev > 0.1 * dev.max())] if dev.max() > 0 else tc[0]
        ratios = []
        for a in np.arange(arrive, tc[-1] - 5.0 + 1e-9, 5.0):
            w = (tc >= a) & (tc < a + 5.0)
            env_e = float(np.max(np.ptp(se_i[w], axis=0))); env_c = float(np.max(np.ptp(sc[w], axis=0)))
            if env_e > 1e-6:
                ratios.append(env_c / env_e)
        rmax = max(ratios) if ratios else float("nan")
        env_ok = (not ratios) or rmax <= 1.25
        if c["steady"] and e["steady"]:
            A1, A2 = np.array(c["A_end"]), np.array(e["A_end"]); Q1, Q2 = np.array(c["Q_end"]), np.array(e["Q_end"])
            dA = float(np.max(np.abs(A1 - A2)) / np.max(np.abs(A2))); dQ = float(np.max(np.abs(Q1 - Q2)) / np.max(np.abs(Q2)))
            end = f"end states (both steady) dA {dA:.1e}, dQ {dQ:.1e}"
            end_ok = dA < 1e-6 and dQ < 1e-6
            verdict = "PASS" if (env_ok and end_ok and abs(c["water_err"]) < 1e-10) else "FAIL"
        else:
            end = f"end state INCONCLUSIVE (steady: C2 {c['steady']}, explicit {e['steady']}; residuals A/Q: C2 {c['resid'][0]:.0e}/{c['resid'][1]:.0e}, explicit {e['resid'][0]:.0e}/{e['resid'][1]:.0e})"
            verdict = ("INCONCLUSIVE" if env_ok else "FAIL")
        print(f"{mark(verdict):12s} {case:22s} {dist:16s} arrival {arrive:5.1f} s; envelope ratio C2/reference max {rmax:.3f} "
              f"over {len(ratios)} windows (<= 1.25); {end}; reference CFL {e['cfl']:.4f}; C2 fallback {c['c2_fallback']}")

    print("\n--- V7br closed frictionless reach (100 s): energy ---")
    v7 = {(r["kind"], r["scheme"], r["cfl"]): r for r in res if r["test"] == "V7br"}
    for key, r in sorted(v7.items()):
        print(f"      {key[0]} {key[1]:8s} CFL {key[2]:<6}: dissipated {100 * r['dissipated']:+.4f} %, worst single step "
              f"{r['worst_step']:.1e}, max cumulative drift {r['drift_max']:+.1e}, largest 10 s window-mean rise "
              f"{r['window_up']:.1e}, slope (2nd half) {r['slope']:+.1e} /s, water {r['water_err']:.1e}, C2 blocks {r['c2_blocks']}")
    for kind, same in (("ff", 0.45), ("pf", 0.186)):
        e, c, c9 = v7.get((kind, "explicit", same)), v7.get((kind, "c2", same)), v7.get((kind, "c2", 0.9))
        if not (e and c and c9):
            continue
        ratio = c["dissipated"] / e["dissipated"] if e["dissipated"] > 0 else float("nan")
        a = 0.8 <= ratio <= 1.25 and c["worst_step"] <= 10 * max(e["worst_step"], 1e-16)
        b = c9["drift_max"] <= 1e-12 and c9["window_up"] <= 1e-10 and c9["slope"] <= 1e-12 and \
            c["drift_max"] <= 1e-12 and c["window_up"] <= 1e-10
        v = "PASS" if (a and b) else "FAIL"
        print(f"{mark(v):12s} {kind}: same-CFL control (CFL {same}) dissipation C2/explicit {ratio:.3f} (0.8-1.25), worst step "
              f"C2 {c['worst_step']:.1e} vs explicit {e['worst_step']:.1e} (<= 10 x); no systematic growth at CFL {same} and 0.9: "
              f"{'yes' if b else 'no'}")

    print("\n--- V12r consistency and accuracy (conduit -> 1 m, 2 cm bump, 10 s; reference explicit CFL 0.01) ---")
    v12 = {(r["scheme"], r["cfl"]): r for r in res if r["test"] == "V12r"}
    ref = v12.get(("explicit", 0.01))
    if ref:
        Er, Ar = np.array(ref["eta"]), np.array(ref["A"])
        errs = {}
        for key in (("c2", 0.9), ("c2", 0.45), ("c2", 0.225), ("c2", 0.1125), ("explicit", 0.1)):
            if key in v12:
                de = float(np.max(np.abs(np.array(v12[key]["eta"]) - Er)))
                dl = float(np.sum(np.abs(np.array(v12[key]["A"]) - Ar)) / np.sum(np.abs(Ar)))
                errs[key] = (de, dl)
                print(f"      {key[0]:8s} CFL {key[1]:<7} max stage difference {1e3 * de:.4f} mm, L1 in A {dl:.2e}")
        if all(k in errs for k in (("c2", 0.225), ("c2", 0.1125), ("c2", 0.9))):
            den = errs[("c2", 0.1125)][1]
            ratio = errs[("c2", 0.225)][1] / den if den > 0 else float("inf")
            acc = max(errs[k][0] for k in errs if k[0] == "c2") <= 1e-3
            v = "PASS" if (1.5 <= ratio <= 2.6 and acc) else "FAIL"
            print(f"{mark(v):12s} asymptotic ratio (0.225 -> 0.1125, r^2 P < 1) {ratio:.2f} (1.5-2.6); max stage difference over "
                  f"all C2 steps {1e3 * max(errs[k][0] for k in errs if k[0] == 'c2'):.4f} mm (<= 1 mm)")

    print("\n--- COST: total runtime over 20 s = cost per step x steps ---")
    cs = {}
    for r in [r for r in res if r["test"] == "COST"]:
        cs.setdefault(r["case"], {})[r["scheme"]] = r
    for case, d in cs.items():
        c, e = d.get("c2 0.9"), d.get("explicit 0.9 x critical")
        if not (c and e):
            continue
        de = float(np.max(np.abs(np.array(c["eta"]) - np.array(e["eta"]))))
        print(f"      {case:40s} C2: CFL 0.9, {c['steps']} steps, {1e3 * c['per_step']:.2f} ms/step, {c['wall']:.1f} s | explicit: "
              f"CFL {e['cfl']:.4f} (0.9 x predicted critical {e['crit_pred']:.4f}), {e['steps']} steps, {1e3 * e['per_step']:.2f} ms/step, "
              f"{e['wall']:.1f} s | speed-up {e['wall'] / c['wall']:.1f} x; end-stage difference {1e3 * de:.3f} mm")
    print(f"\nRESULT revision 2: {tally['PASS']} pass, {tally['FAIL']} fail, {tally['INCONCLUSIVE']} inconclusive")


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["V5r", "V5br", "V7br", "V12r", "COST"]
    J = jobs(only)
    T0 = time.time()
    need = [g for g in GEOMS if any(g in lab for lab, _, _ in J)]
    print(f"Converging {len(need)} steady states with C2 at CFL 0.9 (residual < 1e-12 per 500 steps, or 3000 s) ...", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(make_steady, need):
            print(f"[{time.time() - T0:6.0f} s] steady: {r['name']}: converged {r['ok']} at t = {r['t']:.0f} s, residual "
                  f"{r['res'][0]:.1e} / {r['res'][1]:.1e}", flush=True)
    print(f"C2 verification revision 2 ({', '.join(only)}): {len(J)} jobs on {workers} workers", flush=True)
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
    print("\n================ RESULTS ================")
    report(res)
    print(f"({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
