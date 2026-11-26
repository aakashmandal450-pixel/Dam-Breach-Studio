"""B1, B2, B3, B9 and B13 (Part 6 Appendix 6A): lake at rest, dam breaks, two rarefactions,
passive scalar. Exact solutions are written out here, independent of the solver."""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from ..geometry import Section, rectangle, trapezoid, conduit
from ..solver import Model, G


# ----------------------------------------------------------------------------- B1 lake at rest
def b1_lake_at_rest(N=50, L=10.0, steps=100_000, seed=6):
    """Irregular bed and widths, rectangles and trapezoids, one 5-cell conduit 0.2 x 0.2 m that
    is pressurised (eta in the slot), and three emergent dry cells (z > eta). eta = 0.5 m, Q = 0,
    closed ends. The spec's bed range z in [0, 0.4] has no dry cell, so three cells are raised to
    0.55-0.65 m to make the case 'partly dry' as the test title requires."""
    rng = np.random.default_rng(seed)
    cells = []
    for i in range(N):
        z = 0.4 * rng.random()
        if rng.random() < 0.5:
            cells.append(rectangle(z, 0.5 + 2.5 * rng.random()))
        else:
            cells.append(trapezoid(z, 0.5 + 2.5 * rng.random(), 2.0 * rng.random(), 5.0))
    for i in range(20, 25):
        cells[i] = conduit(0.1 + 0.05 * rng.random(), 0.2, 0.2, 50.0)
    for i, z in ((8, 0.55), (9, 0.65), (40, 0.6)):
        cells[i] = rectangle(z, 1.0)
    m = Model(cells, L / N, manning_n=0.03)
    eta0 = 0.5
    m.set_stage(np.maximum(eta0, m.C.z))
    wet0 = m.depth() > m.h_dry
    V0 = m.water_volume()
    m.run(np.inf, max_steps=steps)
    h = m.depth(); wet = h > m.h_dry
    return dict(steps=m.nsteps, t=m.t, max_U=float(np.max(np.abs(m.velocity()))),
                max_deta=float(np.max(np.abs(m.stage()[wet] - eta0))),
                dry_cells_stay_dry=bool(np.all(wet == wet0)), water_err=m.water_error(V0),
                n_dry=int((~wet0).sum()), n_conduit=5)


# ----------------------------------------------------------------------------- exact solutions
def ritter(x, t, h0):
    c0 = np.sqrt(G * h0); xi = x / t
    h = np.where(xi <= -c0, h0, np.where(xi >= 2 * c0, 0.0, (2 * c0 - xi) ** 2 / (9 * G)))
    u = np.where(xi <= -c0, 0.0, np.where(xi >= 2 * c0, 0.0, 2.0 / 3.0 * (xi + c0)))
    return h, u


def stoker_state(hL, hR):
    cL = np.sqrt(G * hL)

    def f(hm):
        um_r = 2 * (cL - np.sqrt(G * hm))
        um_s = (hm - hR) * np.sqrt(0.5 * G * (hm + hR) / (hm * hR))
        return um_r - um_s

    hm = brentq(f, hR, hL, xtol=1e-15)
    um = 2 * (cL - np.sqrt(G * hm))
    S = hm * um / (hm - hR)
    return hm, um, S


def stoker(x, t, hL, hR):
    hm, um, S = stoker_state(hL, hR)
    cL, cm = np.sqrt(G * hL), np.sqrt(G * hm)
    xi = x / t
    h = np.full_like(x, hR); u = np.zeros_like(x)
    rare = (xi > -cL) & (xi <= um - cm)
    h = np.where(xi <= -cL, hL, h); u = np.where(xi <= -cL, 0.0, u)
    h = np.where(rare, (2 * cL - xi) ** 2 / (9 * G), h); u = np.where(rare, 2.0 / 3.0 * (xi + cL), u)
    mid = (xi > um - cm) & (xi < S)
    h = np.where(mid, hm, h); u = np.where(mid, um, u)
    return h, u, (hm, um, S)


def two_rarefactions(x, t, h0, u0):
    """Toro (2001) exact solution for h0, -u0 | h0, +u0 (no dry middle when 4 c0 > 2 u0)."""
    c0 = np.sqrt(G * h0)
    cs = c0 - 0.5 * u0                          # (u_L + 2 c_L - (u_R - 2 c_R)) / 4 with u_L = -u0
    if cs <= 0:
        raise ValueError("dry middle; not this case")
    hs = cs * cs / G
    xi = x / t
    h = np.full_like(x, hs); u = np.zeros_like(x)
    # left rarefaction: from -u0 - c0 to 0 - cs
    lw = (xi > -u0 - c0) & (xi < -cs)
    c = (-u0 + 2 * c0 - xi) / 3.0
    h = np.where(lw, c * c / G, h); u = np.where(lw, xi + c, u)
    h = np.where(xi <= -u0 - c0, h0, h); u = np.where(xi <= -u0 - c0, -u0, u)
    rw = (xi > cs) & (xi < u0 + c0)
    c = (2 * c0 - u0 + xi) / 3.0               # right family: u - 2c = u0 - 2 c0, xi = u + c
    h = np.where(rw, c * c / G, h); u = np.where(rw, xi - c, u)
    h = np.where(xi >= u0 + c0, h0, h); u = np.where(xi >= u0 + c0, u0, u)
    return h, u, hs


def _l1(a, b, ds):
    return float(np.sum(np.abs(a - b) * ds))


# ----------------------------------------------------------------------------- B2, B3
def b2_ritter(N, h0=1.0, L=1000.0, t_end=50.0):
    ds = 2 * L / N
    x = -L + ds * (np.arange(N) + 0.5)
    m = Model([rectangle(0.0, 1.0)] * N, ds, bc_left={"type": "transmissive"}, bc_right={"type": "transmissive"})
    m.set_stage(np.where(x < 0, h0, 0.0))
    V0 = m.water_volume()
    m.run(t_end)
    he, ue = ritter(x, t_end, h0)
    h = m.depth(); u = m.velocity()
    wet = h > 1e-6
    front = float(x[wet].max() + 0.5 * ds)
    # same-threshold diagnostic (decision 6-20): first position where h falls below h_th, linearly
    # interpolated, in both the numerical and the exact solution
    h_th = 1e-3
    c0 = np.sqrt(G * h0)
    front_th_exact = (2 * c0 - np.sqrt(9 * G * h_th)) * t_end
    k = np.where((h[:-1] >= h_th) & (h[1:] < h_th) & (x[:-1] > 0))[0]
    front_th = float(x[k[-1]] + ds * (h[k[-1]] - h_th) / (h[k[-1]] - h[k[-1] + 1])) if len(k) else np.nan
    return dict(N=N, ds=ds, L1_h=_l1(h, he, ds), L1_u=_l1(u, ue, ds), front=front,
                front_th=front_th, front_th_exact=front_th_exact, front_th_err=front_th / front_th_exact - 1.0,
                front_exact=2 * np.sqrt(G * h0) * t_end,
                front_err=front / (2 * np.sqrt(G * h0) * t_end) - 1.0,
                water_err=m.water_error(V0), min_area=m.min_area_seen, nan=bool(np.isnan(h).any()))


def b3_stoker(N, hL=1.0, hR=0.1, L=1000.0, t_end=50.0):
    ds = 2 * L / N
    x = -L + ds * (np.arange(N) + 0.5)
    m = Model([rectangle(0.0, 1.0)] * N, ds, bc_left={"type": "transmissive"}, bc_right={"type": "transmissive"})
    m.set_stage(np.where(x < 0, hL, hR))
    V0 = m.water_volume()
    m.run(t_end)
    he, ue, (hm, um, S) = stoker(x, t_end, hL, hR)
    h = m.depth(); u = m.velocity()
    # shock position: where h crosses (hm + hR)/2, right of the rarefaction
    k = np.where((h[:-1] > 0.5 * (hm + hR)) & (h[1:] <= 0.5 * (hm + hR)) & (x[:-1] > 0))[0]
    xs = float(x[k[-1]] + ds * (h[k[-1]] - 0.5 * (hm + hR)) / (h[k[-1]] - h[k[-1] + 1])) if len(k) else np.nan
    # intermediate state: mean over the middle half of the plateau
    a, b = (um - np.sqrt(G * hm)) * t_end, S * t_end
    sel = (x > a + 0.25 * (b - a)) & (x < b - 0.25 * (b - a))
    return dict(N=N, ds=ds, L1_h=_l1(h, he, ds), L1_u=_l1(u, ue, ds),
                shock_speed=xs / t_end, shock_speed_exact=S, shock_err=xs / t_end / S - 1.0,
                hm=float(h[sel].mean()), hm_exact=hm, hm_err=float(h[sel].mean() / hm - 1.0),
                um=float(u[sel].mean()), um_exact=um, um_err=float(u[sel].mean() / um - 1.0),
                water_err=m.water_error(V0))


# ----------------------------------------------------------------------------- B9
def b9_two_rarefactions(N=400, h0=1.0, u0=5.0, L=50.0, t_end=2.5):
    ds = 2 * L / N
    x = -L + ds * (np.arange(N) + 0.5)
    m = Model([rectangle(0.0, 1.0)] * N, ds, bc_left={"type": "transmissive"}, bc_right={"type": "transmissive"})
    m.set_stage(np.full(N, h0), U=np.where(x < 0, -u0, u0))
    V0 = m.water_volume()
    stats = dict(minA=np.inf, nan=False)

    def cb(mm):
        stats["minA"] = min(stats["minA"], float(mm.A.min()))
        stats["nan"] = stats["nan"] or bool(np.isnan(mm.A).any() or np.isnan(mm.Q).any())

    m.run(t_end, callback=cb, every=1)
    he, ue, hs = two_rarefactions(x, t_end, h0, u0)
    h = m.depth()
    return dict(N=N, min_area=stats["minA"], nan=stats["nan"], clipped=m.clipped_volume,
                water_err=m.water_error(V0), h_centre=float(h[N // 2 - 1:N // 2 + 1].mean()),
                h_star=hs, L1_h=_l1(h, he, ds))


# ----------------------------------------------------------------------------- B13 passive scalar
class _Watch:
    def __init__(self, cmax):
        self.cmax = cmax; self.c_lo = np.inf; self.c_hi = -np.inf; self.ac_min = np.inf; self.steps = 0
        self.c_lo_wet = np.inf; self.c_hi_wet = -np.inf; self.cmin0 = None

    def __call__(self, m):
        C = m.concentration(); wet = m.A > m.A_dry
        if np.any(wet):
            self.c_lo = min(self.c_lo, float(C[wet].min())); self.c_hi = max(self.c_hi, float(C[wet].max()))
        well = m.depth() > 1e-3                   # cells well above the drying threshold
        if np.any(well):
            self.c_lo_wet = min(self.c_lo_wet, float(C[well].min())); self.c_hi_wet = max(self.c_hi_wet, float(C[well].max()))
        self.ac_min = min(self.ac_min, float(m.AC.min())); self.steps += 1

    def result(self, m, S0, extra=None):
        d = dict(C_min=self.c_lo, C_max=self.c_hi, C_min_h_gt_1mm=self.c_lo_wet, C_max_h_gt_1mm=self.c_hi_wet, C_max0=self.cmax, AC_min=self.ac_min,
                 solids_err=m.solids_error(S0), store=float(m.M.sum()), steps=self.steps)
        d["AC_min_before_drying"] = m.min_ac_seen; d["clipped_volume"] = m.clipped_volume
        d["bounded"] = bool(m.min_ac_seen >= -1e-15 and self.c_lo >= -1e-12 and self.c_hi <= self.cmax * (1 + 1e-12) and self.ac_min >= -1e-15)
        if extra:
            d.update(extra)
        return d


def b13_cases():
    out = {}
    # (0) uniform rectangle, U = 1 m/s, C = 1 on 4 <= s <= 6
    N, L = 200, 20.0; ds = L / N; x = ds * (np.arange(N) + 0.5)
    pulse = ((x >= 4) & (x <= 6)).astype(float)

    def uniform(reverse_at=None):
        m = Model([rectangle(0.0, 1.0)] * N, ds, bc_left={"type": "discharge", "Q": 1.0, "C": 0.0},
                  bc_right={"type": "transmissive"})
        m.set_stage(np.full(N, 1.0), U=1.0, C=pulse)
        S0 = m.solids(); w = _Watch(1.0)
        if reverse_at is None:
            m.run(8.0, callback=w, every=1)
        else:
            m.run(reverse_at, callback=w, every=1)
            m.bc_left = {"type": "transmissive"}; m.bc_right = {"type": "discharge", "Q": -1.0, "C": 0.0}
            m.Q = -m.Q                          # the flow is reversed everywhere at once
            m.run(reverse_at + 6.0, callback=w, every=1)
        C = m.concentration()
        centre = float(np.sum(x * C * m.A) / max(np.sum(C * m.A), 1e-30))
        return m, S0, w, centre

    m, S0, w, c = uniform()
    out["uniform"] = w.result(m, S0, dict(centroid=c, centroid_expected=5.0 + 8.0))
    m, S0, w, c = uniform(reverse_at=4.0)
    out["reversed"] = w.result(m, S0, dict(centroid=c, centroid_expected=5.0 + 4.0 - 6.0))
    # (a) through B4's sections (trapezoid with varying width, side slope and bed)
    N, L = 100, 10.0; ds = L / N; x = ds * (np.arange(N) + 0.5)
    cells = [Section(0.1 * np.sin(2 * np.pi * s / L), [0.0, 5.0],
                     [1 + 0.5 * np.sin(2 * np.pi * s / L),
                      1 + 0.5 * np.sin(2 * np.pi * s / L) + 2 * 5.0 * (1 + 0.5 * np.cos(2 * np.pi * s / L))], [1])
             for s in x]
    m = Model(cells, ds, bc_left={"type": "discharge", "Q": 1.0, "C": 0.0}, bc_right={"type": "stage", "eta": 0.8})
    m.set_stage(np.full(N, 0.8), C=((x >= 2) & (x <= 4)).astype(float))
    m.Q = np.full(N, 1.0); m.AC = m.A * m.concentration()
    S0 = m.solids(); w = _Watch(1.0)
    m.run(10.0, callback=w, every=1)
    out["varying_section"] = w.result(m, S0)
    # (b) across a wetting front: dam break onto a dry bed, C = 1 and 0.5 in the reservoir
    N, L = 400, 100.0; ds = 2 * L / N; x = -L + ds * (np.arange(N) + 0.5)
    m = Model([rectangle(0.0, 1.0)] * N, ds, bc_left={"type": "wall"}, bc_right={"type": "transmissive"})
    m.set_stage(np.where(x < 0, 1.0, 0.0), C=np.where(x < -20, 0.5, 1.0) * (x < 0))
    S0 = m.solids(); w = _Watch(1.0)
    m.run(15.0, callback=w, every=1)
    out["wetting_front"] = w.result(m, S0)
    # (d) a wet cell draining into dry neighbours, closed ends: the thin film dries, solids to store
    N = 60; ds = 0.5
    # a ridge, so that the water drains away both sides and the crest cells actually dry
    cells = [rectangle(-0.02 * abs(i - N // 2), 1.0) for i in range(N)]
    m = Model(cells, ds, bc_left={"type": "wall"}, bc_right={"type": "wall"})
    eta = m.C.z.copy(); eta[N // 2] += 0.5
    m.set_stage(eta, C=np.where(np.arange(N) == N // 2, 1.0, 0.0))
    S0 = m.solids(); w = _Watch(1.0)
    m.run(30.0, callback=w, every=1)
    out["drain_into_dry"] = w.result(m, S0)
    return out
