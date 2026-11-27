"""B12d conduit-outlet diagnosis (user plan, 2026-11-27).

Four B12d cases (submerged and free outlet, both directions) under four configurations:

    D1  a_s = 50 m/s,  frictionless          (the B12d reference)
    D2  a_s = 100 m/s, frictionless
    D3  a_s = 200 m/s, frictionless
    D4  a_s = 50 m/s,  Manning n = 0.012 in every cell (a small, controlled value)

Geometry, initial and boundary conditions, CFL and the steady-state criterion are those of B12d
(junctions.b12d_one / _steady_junction); only a_s and n change. The tailwater stage of the
submerged case is the D1 value in every configuration, so the boundary conditions are identical.
Friction is a diagnostic only: it must not be used to make the reference case settle.

Recorded per run
  - stage oscillation in the two conduit cells next to the outlet: range over the last 20 % of the
    run, its history (range in successive 500 s windows), and the dominant period
  - pressure head above the crown (= slot depth) in those cells: min, max, mean
  - outlet discharge (mass flux through the junction interface): mean and range, last 20 %
  - upstream conduit stage (mean over conduit cells n/4 .. n/2): mean and range, last 20 %
  - water balance (6.33) and an energy balance: time-averaged E_up - E_dn with
    E = eta + (Q_f / A)^2 / 2g (Q_f the mean junction flux), and, for D4, the Manning friction head
    between the two measuring windows, so the junction loss is E_up - E_dn - h_f
  - whether the B12d steady criterion is reached (relative change < tol over 500 steps), and when
"""
from __future__ import annotations

import numpy as np

from ..geometry import conduit, rectangle
from ..solver import Model, G
from .junctions import _solve_downstream, junction_relation, borda, _A

A_S0 = 50.0
CONFIGS = {"D1": (A_S0, 0.0), "D2": (2 * A_S0, 0.0), "D3": (4 * A_S0, 0.0), "D4": (A_S0, 0.012)}
Q = 0.05
N_SIDE, DS = 80, 0.25


def _setup(outlet, d, a_s, n_manning):
    a = conduit(0.0, 0.2, 0.2, a_s)
    n = N_SIDE
    if outlet == "submerged":
        b = rectangle(0.0, 1.0)
        a_ref = conduit(0.0, 0.2, 0.2, A_S0)
        eta_dn = _solve_downstream(a_ref, b, Q, 0.6)          # D1 tailwater for every configuration
        cells = [a] * n + [b] * n
        bcl, bcr = {"type": "discharge", "Q": Q}, {"type": "stage", "eta": eta_dn}
        eta0 = np.r_[np.full(n, 0.6), np.full(n, eta_dn)]
        tol = 1e-11
    else:
        b = rectangle(-0.5, 1.0)
        eta_dn = None
        cells = [a] * n + [b] * n
        bcl, bcr = {"type": "discharge", "Q": Q}, {"type": "critical"}
        eta0 = np.r_[np.full(n, 0.3), np.full(n, -0.45)]
        tol = 1e-10
    if d < 0:
        cells = cells[::-1]
        bcl, bcr = ({"type": "stage", "eta": eta_dn} if outlet == "submerged" else {"type": "critical"},
                    {"type": "discharge", "Q": -Q})
        eta0 = eta0[::-1]
    m = Model(cells, DS, manning_n=n_manning, bc_left=bcl, bc_right=bcr)
    m.set_stage(eta0)
    if outlet == "submerged":
        m.Q = np.full(2 * n, Q * d)
    return m, a, b, eta_dn, tol


def diagnose(config, outlet, d, t_max=1.0e4, sample_dt=0.5, check_every=500):
    a_s, n_manning = CONFIGS[config]
    m, a, b, eta_dn, tol = _setup(outlet, d, a_s, n_manning)
    n = N_SIDE
    # indices in the model's own (left-to-right) order
    if d > 0:
        last2 = [n - 2, n - 1]; jf = n
        up = np.arange(n // 4, n // 2); dn = np.arange(2 * n - n // 2, 2 * n - n // 4)
    else:
        last2 = [n + 1, n]; jf = n
        up = np.arange(2 * n - n // 2, 2 * n - n // 4)[::-1]; dn = np.arange(n // 4, n // 2)[::-1]
    crown = a.z + 0.2
    V0 = m.water_volume()
    ts, s2, fa, sup, Eup, Edn = [], [], [], [], [], []
    fine_t, fine_s = [], []
    next_sample = 0.0
    prevA, prevQ = m.A.copy(), m.Q.copy()
    steady_at = None; k = 0; residual = None
    while m.t < t_max:
        m.step()
        k += 1
        eta = None
        if m.t >= next_sample:
            eta = m.stage()
            Qf = abs(m.last["FA"][jf])
            ts.append(m.t); s2.append(eta[last2].copy()); fa.append(Qf); sup.append(eta[up].mean())
            Eup.append(np.mean(eta[up] + (Qf / m.A[up]) ** 2 / (2 * G)))
            Edn.append(np.mean(eta[dn] + (Qf / m.A[dn]) ** 2 / (2 * G)))
            next_sample += sample_dt
        if m.t > t_max - 20.0:                           # every step over the last 20 s
            if eta is None:
                eta = m.stage()
            fine_t.append(m.t); fine_s.append(eta[last2[-1]])
        if k % check_every == 0:
            dA = np.max(np.abs(m.A - prevA)) / max(np.max(np.abs(m.A)), 1e-12)
            dQ = np.max(np.abs(m.Q - prevQ)) / max(np.max(np.abs(m.Q)), 1e-12)
            residual = (float(dA), float(dQ))
            if dA < tol and dQ < tol and steady_at is None:
                steady_at = m.t
                break
            prevA, prevQ = m.A.copy(), m.Q.copy()
    ts = np.array(ts); s2 = np.array(s2); fa = np.array(fa); sup = np.array(sup)
    Eup = np.array(Eup); Edn = np.array(Edn)
    late = ts >= 0.8 * ts[-1]
    # oscillation envelope in 500 s windows (last conduit cell)
    env = []
    for t0 in np.arange(0.0, ts[-1], 500.0):
        w = (ts >= t0) & (ts < t0 + 500.0)
        if w.sum() > 1:
            env.append(float(np.ptp(s2[w, -1])))
    # dominant period from the fine record (zero crossings about the mean)
    period = np.nan
    if len(fine_s) > 10:
        f = np.array(fine_s) - np.mean(fine_s); tt = np.array(fine_t)
        zc = np.where((f[:-1] < 0) & (f[1:] >= 0))[0]
        if len(zc) >= 3:
            period = float(np.mean(np.diff(tt[zc])))
    # friction head between the two measuring windows (D4); the cells between their centres
    h_f = 0.0
    if n_manning > 0:
        lo, hi = sorted([int(np.mean(up)), int(np.mean(dn))])
        h = m.depth(); P = m.C.perimeter_h(h); A = m.A
        Qf = float(np.mean(fa[late]))
        Sf = n_manning ** 2 * Qf ** 2 / (A ** 2 * (A / P) ** (4.0 / 3.0))
        h_f = float(np.sum(Sf[lo:hi + 1] * m.ds[lo:hi + 1]))
    loss = float(np.mean(Eup[late]) - np.mean(Edn[late]))
    out = dict(config=config, a_s=a_s, n=n_manning, outlet=outlet, direction="L->R" if d > 0 else "R->L",
               t=float(m.t), steps=m.nsteps, steady=steady_at is not None, steady_at=steady_at,
               residual=residual,
               osc_range_last20=float(np.ptp(s2[late, -1])), osc_range_last20_cell2=float(np.ptp(s2[late, 0])),
               osc_envelope_500s=env, osc_period=period,
               slot_depth_min=float((s2[late] - crown).min()), slot_depth_max=float((s2[late] - crown).max()),
               slot_depth_mean=float((s2[late] - crown).mean()),
               outlet_Q_mean=float(fa[late].mean()), outlet_Q_range=float(np.ptp(fa[late])),
               stage_up_mean=float(sup[late].mean()), stage_up_range=float(np.ptp(sup[late])),
               water_err=m.water_error(V0), loss=loss, h_friction=h_f, junction_loss=loss - h_f,
               min_area=m.min_area_seen)
    if outlet == "submerged":
        b_ref = rectangle(0.0, 1.0)
        rel_up = junction_relation(a, b_ref, Q, eta_dn)
        Ea = rel_up + (Q / _A(a, rel_up)) ** 2 / (2 * G); Eb = eta_dn + (Q / _A(b_ref, eta_dn)) ** 2 / (2 * G)
        out["loss_relation"] = Ea - Eb
        out["borda"] = borda(a, b_ref, Q, out["stage_up_mean"], eta_dn)
        out["stage_up_relation"] = rel_up
    return out


def job(config, outlet, d, t_max):
    return diagnose(config, outlet, d, t_max=t_max)


def main():
    import os
    import sys
    import time
    from concurrent.futures import ProcessPoolExecutor, as_completed

    t_max = float(sys.argv[sys.argv.index("--tmax") + 1]) if "--tmax" in sys.argv else 1.0e4
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 1)
    cfgs = sys.argv[sys.argv.index("--configs") + 1].split(",") if "--configs" in sys.argv else ["D3", "D2", "D1", "D4"]
    outs = sys.argv[sys.argv.index("--outlets") + 1].split(",") if "--outlets" in sys.argv else ["submerged", "free"]
    jobs = [(c, o, d) for c in cfgs for o in outs for d in (+1, -1)]
    T0 = time.time()
    print(f"B12d diagnosis: {len(jobs)} runs on {workers} workers, t_max = {t_max:.0f} s "
          f"(D3 is the slowest: 4x more steps than D1)", flush=True)
    res = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(job, c, o, d, t_max): (c, o, d) for c, o, d in jobs}
        for f in as_completed(futs):
            key = futs[f]
            try:
                r = f.result(); res.append(r)
                print(f"[{time.time() - T0:7.0f} s] {r['config']} {r['outlet']:9s} {r['direction']} "
                      f"steady={r['steady']} t={r['t']:.0f} osc(last cell, last 20%)={r['osc_range_last20']:.3e} m "
                      f"period={r['osc_period']:.3f} s slot depth [{r['slot_depth_min']:.3f}, {r['slot_depth_max']:.3f}] m "
                      f"Q_out={r['outlet_Q_mean']:.5f}±{r['outlet_Q_range']:.1e} "
                      f"stage_up={r['stage_up_mean']:.4f}±{r['stage_up_range']:.1e} "
                      f"loss={r['loss']:.4f} (h_f {r['h_friction']:.4f}, junction {r['junction_loss']:.4f})"
                      + (f" relation={r['loss_relation']:.4f} Borda={r['borda']:.4f} stage_up_rel={r['stage_up_relation']:.4f}"
                         if 'loss_relation' in r else "")
                      + f" water err={r['water_err']:.1e}", flush=True)
                print(f"           envelope (range per 500 s): " + ", ".join(f"{e:.2e}" for e in r["osc_envelope_500s"]),
                      flush=True)
            except Exception as e:
                print(f"ERROR {key}: {e!r}", flush=True)
    print("\n================ TABLE (last conduit cell; last 20 % of each run) ================")
    print(f"{'cfg':4s} {'a_s':>5s} {'n':>6s} {'outlet':9s} {'dir':5s} {'steady':6s} {'osc m':>9s} {'period s':>8s} "
          f"{'slot max':>8s} {'stage_up':>8s} {'loss m':>7s} {'jn loss':>7s} {'water':>8s}")
    for r in sorted(res, key=lambda x: (x["outlet"], x["config"], x["direction"])):
        print(f"{r['config']:4s} {r['a_s']:5.0f} {r['n']:6.3f} {r['outlet']:9s} {r['direction']:5s} {str(r['steady']):6s} "
              f"{r['osc_range_last20']:9.2e} {r['osc_period']:8.3f} {r['slot_depth_max']:8.3f} {r['stage_up_mean']:8.4f} "
              f"{r['loss']:7.4f} {r['junction_loss']:7.4f} {r['water_err']:8.1e}")
    sub = [r for r in res if "loss_relation" in r]
    if sub:
        print(f"\nsubmerged reference: relation loss {sub[0]['loss_relation']:.4f} m, upstream stage "
              f"{sub[0]['stage_up_relation']:.4f} m (D1 conduit); Borda {sub[0]['borda']:.4f} m")
    print(f"\nDONE ({time.time() - T0:.0f} s)")


if __name__ == "__main__":
    main()
