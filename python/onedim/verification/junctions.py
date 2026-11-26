"""B12a, B12b, B12c: steady junctions and the free overfall (Part 6 §6.5.3, §6.8.4, Appendix 6A).

Each case returns a dict of measured quantities. Nothing here is tuned: the references are solved
independently of the solver (the junction relation by root finding on the section functions, the
critical discharge from (1.4)-(1.5)).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from ..geometry import SectionSet, intersection, rectangle, trapezoid, conduit
from ..solver import Model, G


def _I1(sec, eta):
    return float(SectionSet([sec]).i1(np.array([eta]))[0])


def _A(sec, eta):
    return float(SectionSet([sec]).area(np.array([eta]))[0])


def _T(sec, eta):
    S = SectionSet([sec])
    return float(S.width_h(np.array([max(eta - sec.z, 0.0)]))[0])


def _residual(sec_a, sec_b, si, Q, eta_a, eta_b):
    """Momentum residual across an abrupt junction a -> b (flow from a to b), with the loading
    closure (6.16b): cell a loses mass (face at eta_a), cell b gains it (face at min(eta_a, eta_b)):

        Q^2/A_a + g I1_a(eta_a) - g J_a(eta_a) = Q^2/A_b + g I1_b(eta_b) - g J_b(eta_f),
        J_x(eta) = I1_x(eta) - I1_int(eta)."""
    ef = min(eta_a, eta_b)
    lhs = Q * Q / _A(sec_a, eta_a) + G * _I1(si, eta_a)
    rhs = Q * Q / _A(sec_b, eta_b) + G * _I1(sec_b, eta_b) - G * (_I1(sec_b, ef) - _I1(si, ef))
    return lhs - rhs


def _crit_stage(sec, Q, hi):
    fr2 = lambda eta: Q * Q * _T(sec, eta) / (G * _A(sec, eta) ** 3) - 1.0
    return brentq(fr2, sec.z + 1e-6, hi, xtol=1e-14)


def _largest_root(f, lo, hi, n=400):
    xs = np.linspace(lo, hi, n)
    fs = [f(x) for x in xs]
    for k in range(n - 1, 0, -1):
        if fs[k - 1] == 0.0:
            return xs[k - 1]
        if fs[k - 1] * fs[k] < 0:
            return brentq(f, xs[k - 1], xs[k], xtol=1e-14)
    raise ValueError("no subcritical root")


def junction_relation(sec_a, sec_b, Q, eta_b):
    """Upstream stage eta_a (subcritical) for a given downstream stage eta_b."""
    si = intersection(sec_a, sec_b); Q = abs(Q)
    lo = _crit_stage(sec_a, Q, eta_b + 5.0)
    return _largest_root(lambda ea: _residual(sec_a, sec_b, si, Q, ea, eta_b), lo, eta_b + 2.0)


def _solve_downstream(sec_a, sec_b, Q, eta_a):
    """Downstream stage eta_b (subcritical) for a given upstream stage eta_a."""
    si = intersection(sec_a, sec_b); Q = abs(Q)
    lo = _crit_stage(sec_b, Q, eta_a + 5.0)
    return _largest_root(lambda eb: _residual(sec_a, sec_b, si, Q, eta_a, eb), lo, eta_a + 2.0)


def energy(m):
    h = m.depth(); U = m.velocity()
    return m.stage() + U * U / (2 * G)


def _steady_junction(sec_up, sec_dn, Q, h_far, n_side=80, L_side=20.0, spread=0, direction=+1,
                     tol=1e-11, t_max=3000.0, recon="discharge_width"):
    """Steady flow through a junction between sec_up (upstream in the flow sense) and sec_dn.
    direction=+1: flow left -> right; -1: the same channel mirrored, flow right -> left.
    spread=k: the change is spread linearly over k cells (B12c), widths and side slopes
    interpolated between the two sections (open sections only).
    The downstream stage is imposed; h_far is the upstream depth the reference relation is
    solved for (it fixes eta_dn)."""
    ds = L_side / n_side
    cells = [sec_up] * n_side
    if spread:
        for k in range(1, spread + 1):
            f = k / (spread + 1)
            cells.append(_blend(sec_up, sec_dn, f))
    cells += [sec_dn] * n_side
    # reference downstream stage for the abrupt case from h_far upstream
    eta_up_ref = sec_up.z + h_far
    eta_dn = _solve_downstream(sec_up, sec_dn, Q, eta_up_ref)
    if direction < 0:
        cells = cells[::-1]
        bc_l = {"type": "stage", "eta": eta_dn}; bc_r = {"type": "discharge", "Q": -Q}
    else:
        bc_l = {"type": "discharge", "Q": Q}; bc_r = {"type": "stage", "eta": eta_dn}
    m = Model(cells, ds, bc_left=bc_l, bc_right=bc_r, recon=recon)
    # initial: linear stage between the two levels, the steady discharge
    nc = len(cells)
    eta0 = np.where(np.arange(nc) < nc / 2, eta_up_ref, eta_dn)
    if direction < 0:
        eta0 = eta0[::-1]
    m.set_stage(eta0)
    m.Q = np.full(nc, Q * direction)
    ok = m.run_to_steady(tol=tol, check_every=500, t_max=t_max)
    E = energy(m)
    if direction < 0:
        E = E[::-1]; eta = m.stage()[::-1]; Qc = -m.Q[::-1]
    else:
        eta = m.stage(); Qc = m.Q
    q = n_side // 4
    E_up = float(np.mean(E[q:2 * q])); E_dn = float(np.mean(E[-2 * q:-q]))
    eta_up = float(np.mean(eta[q:2 * q]))
    # energy gain anywhere along the flow (frictionless: E must not increase downstream).
    # In the cells next to a junction the cell discharge differs from the steady flux (a one-cell
    # numerical layer), so the energy is also formed with the steady discharge (the mean interface
    # mass flux): E_f = eta + (Q_f / A)^2 / 2g.
    Qf = float(np.mean(np.abs(m.last["FA"])))
    A = m.A[::-1] if direction < 0 else m.A
    Ef = eta + (Qf / A) ** 2 / (2 * G)
    gain = float(max(np.diff(E).max(), 0.0)); gain_f = float(max(np.diff(Ef).max(), 0.0))
    return dict(converged=ok, t=m.t, residual=getattr(m, "steady_residual", None), eta_up=eta_up, eta_dn=eta_dn, E_up=E_up, E_dn=E_dn,
                loss=E_up - E_dn, max_gain=gain, max_gain_flux=gain_f, Q_flux=Qf, Q_spread=float(Qc.max() - Qc.min()), model=m)


def _blend(a, b, f):
    """Linear blend of two open sections with two nodes each (rectangle/trapezoid)."""
    if len(a.y) != 2 or len(b.y) != 2:
        raise ValueError("blend only for two-node open sections")
    H = a.y[1]
    w0 = (1 - f) * a.w[0] + f * b.w[0]
    w1 = (1 - f) * a.w[1] + f * b.w[1]
    from ..geometry import Section
    return Section((1 - f) * a.z + f * b.z, [0.0, H], [w0, w1], [1])


def borda(sec_a, sec_b, Q, eta_a, eta_b):
    Ua = Q / _A(sec_a, eta_a); Ub = Q / _A(sec_b, eta_b)
    return (Ua - Ub) ** 2 / (2 * G)


def b12a_cases(recon="discharge_width", report=None):
    Q, h1 = 2.0, 1.0
    out = []
    pairs = [("rect 2->4", rectangle(0, 2), rectangle(0, 4), "exp"),
             ("rect 2->10", rectangle(0, 2), rectangle(0, 10), "exp"),
             ("rect 4->2", rectangle(0, 4), rectangle(0, 2), "con"),
             ("rect 10->2", rectangle(0, 10), rectangle(0, 2), "con"),
             ("trap 2->4", trapezoid(0, 2, 1.0, 5.0), trapezoid(0, 4, 1.0, 5.0), "exp"),
             ("trap 2->10", trapezoid(0, 2, 1.0, 5.0), trapezoid(0, 10, 1.0, 5.0), "exp"),
             ("trap 4->2", trapezoid(0, 4, 1.0, 5.0), trapezoid(0, 2, 1.0, 5.0), "con"),
             ("trap 10->2", trapezoid(0, 10, 1.0, 5.0), trapezoid(0, 2, 1.0, 5.0), "con")]
    for name, a, b, kind in pairs:
        for d in (+1, -1):
            r = _steady_junction(a, b, Q, h1, direction=d, recon=recon)
            eta_a_rel = junction_relation(a, b, Q, r["eta_dn"])
            Ea = eta_a_rel + (Q / _A(a, eta_a_rel)) ** 2 / (2 * G)
            Eb = r["eta_dn"] + (Q / _A(b, r["eta_dn"])) ** 2 / (2 * G)
            loss_rel = Ea - Eb
            res = dict(case=name, direction="L->R" if d > 0 else "R->L", kind=kind,
                       loss=r["loss"], loss_rel=loss_rel, err_rel=(r["loss"] - loss_rel) / loss_rel,
                       max_gain=r["max_gain"], max_gain_flux=r["max_gain_flux"],
                       converged=r["converged"], Q_spread=r["Q_spread"])
            if kind == "exp":
                bo = borda(a, b, Q, r["eta_up"], r["eta_dn"])
                res["borda"] = bo; res["err_borda"] = (r["loss"] - bo) / bo
            out.append(res)
            if report:
                report(res)
    # conduit (full, slot) -> open channel 1 m wide, submerged outlet
    a = conduit(0.0, 0.2, 0.2, 50.0); b = rectangle(0.0, 1.0)
    Qc = 0.05
    for d in (+1, -1):
        r = _steady_junction(a, b, Qc, 0.6, direction=d, recon=recon)
        eta_a_rel = junction_relation(a, b, Qc, r["eta_dn"])
        Ea = eta_a_rel + (Qc / _A(a, eta_a_rel)) ** 2 / (2 * G)
        Eb = r["eta_dn"] + (Qc / _A(b, r["eta_dn"])) ** 2 / (2 * G)
        bo = borda(a, b, Qc, r["eta_up"], r["eta_dn"])
        out.append(dict(case="conduit 0.2x0.2 -> open 1", direction="L->R" if d > 0 else "R->L",
                        kind="exp", loss=r["loss"], loss_rel=Ea - Eb,
                        err_rel=(r["loss"] - (Ea - Eb)) / (Ea - Eb), borda=bo,
                        err_borda=(r["loss"] - bo) / bo, max_gain=r["max_gain"],
                        max_gain_flux=r["max_gain_flux"], converged=r["converged"], Q_spread=r["Q_spread"]))
        if report:
            report(out[-1])
    return out


def critical_discharge(sec, E):
    """Critical discharge for specific energy E above the section bottom ((1.4)-(1.5)):
    E = h_c + A_c/(2 T_c), Q_c = sqrt(g A_c^3 / T_c)."""
    f = lambda h: h + _A(sec, sec.z + h) / (2 * _T(sec, sec.z + h)) - E
    hc = brentq(f, 1e-9, E, xtol=1e-15)
    A = _A(sec, sec.z + hc); T = _T(sec, sec.z + hc)
    return float(np.sqrt(G * A ** 3 / T)), hc


def b12b_case(kind="rect", N=10, E=0.5, L_crest=2.0, L_apron=4.0, t_max=200.0):
    """Flat crest z = 1 m fed from a still reservoir of energy E above the crest, then a 1 m drop
    onto a dry apron (z = 0) ending in a free outfall. N cells on the crest."""
    if kind == "rect":
        mk = lambda z: rectangle(z, 1.0)
    else:
        mk = lambda z: trapezoid(z, 1.0, 1.0, 5.0)
    ds = L_crest / N
    na = int(round(L_apron / ds))
    cells = [mk(1.0)] * N + [mk(0.0)] * na
    m = Model(cells, ds, bc_left={"type": "reservoir", "z_s": 1.0 + E}, bc_right={"type": "critical"})
    eta0 = np.r_[np.full(N, 1.0 + 0.6 * E), np.zeros(na)]
    m.set_stage(eta0)
    Qc, hc = critical_discharge(mk(1.0), E)
    hist = []
    while m.t < t_max:
        m.run(min(m.t + 5.0, t_max))
        hist.append(m.last["FA"][N])
    FA = m.last["FA"]
    h = m.depth(); U = m.velocity()
    Ab = m.A[N - 1]; Tb = m.C.width_h(h)[N - 1]
    Fr = abs(U[N - 1]) / np.sqrt(G * Ab / Tb)
    return dict(kind=kind, N=N, Qc=Qc, Q_brink=float(FA[N]), Q_in=float(FA[0]),
                err=float(FA[N] / Qc - 1.0), Fr_brink=float(Fr), h_brink_over_hc=float(h[N - 1] / hc),
                drift=float(abs(hist[-1] - hist[-2]) / Qc), min_area=m.min_area_seen,
                water_err=None)


def b12c_cases(recon="discharge_width", spreads=(5, 10, 20, 50), report=None):
    """The B12a width changes spread linearly over k cells, both directions."""
    Q, h1 = 2.0, 1.0
    out = []
    pairs = [("rect 2->4", rectangle(0, 2), rectangle(0, 4)), ("rect 2->10", rectangle(0, 2), rectangle(0, 10)),
             ("rect 4->2", rectangle(0, 4), rectangle(0, 2)), ("rect 10->2", rectangle(0, 10), rectangle(0, 2)),
             ("trap 2->10", trapezoid(0, 2, 1.0, 5.0), trapezoid(0, 10, 1.0, 5.0)),
             ("trap 10->2", trapezoid(0, 10, 1.0, 5.0), trapezoid(0, 2, 1.0, 5.0))]
    for name, a, b in pairs:
        for k in spreads:
            for d in (+1, -1):
                r = _steady_junction(a, b, Q, h1, spread=k, direction=d, recon=recon)
                res = dict(case=name, spread=k, direction="L->R" if d > 0 else "R->L", loss=r["loss"],
                           max_gain=r["max_gain"], max_gain_flux=r["max_gain_flux"], converged=r["converged"])
                out.append(res)
                if report:
                    report(res)
    return out


# ---------------------------------------------------------------------- single cases (parallel runner)
def b12a_specs():
    """(name, sec_a, sec_b, kind, Q, h_far) for every B12a junction."""
    R, T = rectangle, trapezoid
    s = [("rect 2->4", R(0, 2), R(0, 4), "exp"), ("rect 2->10", R(0, 2), R(0, 10), "exp"),
         ("rect 4->2", R(0, 4), R(0, 2), "con"), ("rect 10->2", R(0, 10), R(0, 2), "con"),
         ("trap 2->4", T(0, 2, 1.0, 5.0), T(0, 4, 1.0, 5.0), "exp"),
         ("trap 2->10", T(0, 2, 1.0, 5.0), T(0, 10, 1.0, 5.0), "exp"),
         ("trap 4->2", T(0, 4, 1.0, 5.0), T(0, 2, 1.0, 5.0), "con"),
         ("trap 10->2", T(0, 10, 1.0, 5.0), T(0, 2, 1.0, 5.0), "con")]
    out = [(n, a, b, k, 2.0, 1.0) for n, a, b, k in s]
    out.append(("conduit 0.2x0.2 -> open 1", conduit(0.0, 0.2, 0.2, 50.0), rectangle(0.0, 1.0), "exp", 0.05, 0.6))
    return out


def b12a_one(name, a, b, kind, Q, h1, d, recon):
    r = _steady_junction(a, b, Q, h1, direction=d, recon=recon)
    eta_a_rel = junction_relation(a, b, Q, r["eta_dn"])
    Ea = eta_a_rel + (Q / _A(a, eta_a_rel)) ** 2 / (2 * G)
    Eb = r["eta_dn"] + (Q / _A(b, r["eta_dn"])) ** 2 / (2 * G)
    loss_rel = Ea - Eb
    res = dict(case=name, direction="L->R" if d > 0 else "R->L", kind=kind, recon=recon,
               loss=r["loss"], loss_rel=loss_rel, err_rel=(r["loss"] - loss_rel) / loss_rel,
               max_gain=r["max_gain"], max_gain_flux=r["max_gain_flux"],
               converged=r["converged"], Q_spread=r["Q_spread"])
    if kind == "exp":
        bo = borda(a, b, Q, r["eta_up"], r["eta_dn"])
        res["borda"] = bo; res["err_borda"] = (r["loss"] - bo) / bo
    return res


def b12c_specs():
    R, T = rectangle, trapezoid
    return [("rect 2->4", R(0, 2), R(0, 4)), ("rect 2->10", R(0, 2), R(0, 10)),
            ("rect 4->2", R(0, 4), R(0, 2)), ("rect 10->2", R(0, 10), R(0, 2)),
            ("trap 2->10", T(0, 2, 1.0, 5.0), T(0, 10, 1.0, 5.0)),
            ("trap 10->2", T(0, 10, 1.0, 5.0), T(0, 2, 1.0, 5.0))]


def b12c_one(name, a, b, k, d, recon):
    r = _steady_junction(a, b, 2.0, 1.0, spread=k, direction=d, recon=recon)
    return dict(case=name, spread=k, direction="L->R" if d > 0 else "R->L", recon=recon, loss=r["loss"],
                max_gain=r["max_gain"], max_gain_flux=r["max_gain_flux"], converged=r["converged"])


def b12c_refine_specs():
    R = rectangle
    return [("rect 2->4", R(0, 2), R(0, 4)), ("rect 2->10", R(0, 2), R(0, 10)),
            ("rect 4->2", R(0, 4), R(0, 2)), ("rect 10->2", R(0, 10), R(0, 2))]


def b12c_refine_one(i, ds, recon="discharge_width", L_t=2.5, L_side=10.0):
    """Decision 6-21: a transition of fixed length L_t at grid spacing ds (flow L->R)."""
    name, a, b = b12c_refine_specs()[i]
    n_side = int(round(L_side / ds)); k = int(round(L_t / ds))
    r = _steady_junction(a, b, 2.0, 1.0, n_side=n_side, L_side=L_side, spread=k, recon=recon,
                         t_max=2000.0)
    return dict(case=name, ds=ds, cells=k, recon=recon, loss=r["loss"], max_gain=r["max_gain"],
                max_gain_flux=r["max_gain_flux"], converged=r["converged"])


def b12d_one(outlet, d, recon="discharge_width"):
    """Conduit 0.2 x 0.2 m (a_s = 50 m/s) -> open rectangle 1 m, Q = 0.05 m3/s.
    outlet = "submerged": same bed, tailwater stage fixed; "free": the open channel is 0.5 m lower
    and ends in a free outfall. Run until steady or 1e4 s; the outlet-flux history is returned."""
    Q = 0.05
    a = conduit(0.0, 0.2, 0.2, 50.0)
    ds, n = 0.25, 80
    if outlet == "submerged":
        b = rectangle(0.0, 1.0)
        r = _steady_junction(a, b, Q, 0.6, direction=d, recon=recon, t_max=1.0e4)
        rel_up = junction_relation(a, b, Q, r["eta_dn"])
        Ea = rel_up + (Q / _A(a, rel_up)) ** 2 / (2 * G)
        Eb = r["eta_dn"] + (Q / _A(b, r["eta_dn"])) ** 2 / (2 * G)
        bo = borda(a, b, Q, r["eta_up"], r["eta_dn"])
        return dict(outlet=outlet, direction="L->R" if d > 0 else "R->L", recon=recon,
                    converged=r["converged"], residual=r["residual"], t=r["t"], loss=r["loss"],
                    loss_rel=Ea - Eb, borda=bo, err_rel=(r["loss"] - (Ea - Eb)) / (Ea - Eb),
                    err_borda=(r["loss"] - bo) / bo)
    b = rectangle(-0.5, 1.0)
    cells = [a] * n + [b] * n
    bcl = {"type": "discharge", "Q": Q}; bcr = {"type": "critical"}
    if d < 0:
        cells = cells[::-1]; bcl, bcr = {"type": "critical"}, {"type": "discharge", "Q": -Q}
    m = Model(cells, ds, bc_left=bcl, bc_right=bcr, recon=recon)
    eta0 = np.r_[np.full(n, 0.3), np.full(n, -0.45)]
    m.set_stage(eta0[::-1] if d < 0 else eta0)
    hist = []
    ok = False
    while m.t < 1.0e4:
        ok = m.run_to_steady(tol=1e-10, check_every=500, t_max=m.t + 100.0)
        j = n if d > 0 else n
        hist.append(float(abs(m.last["FA"][j])))
        if ok:
            break
    return dict(outlet=outlet, direction="L->R" if d > 0 else "R->L", recon=recon, converged=ok,
                residual=getattr(m, "steady_residual", None), t=m.t,
                outlet_flux=hist[-1] if hist else np.nan,
                flux_range_last_10=(float(np.ptp(hist[-10:])) if len(hist) >= 2 else np.nan),
                stage_upstream=float(np.mean((m.stage()[::-1] if d < 0 else m.stage())[n // 4:n // 2])))
