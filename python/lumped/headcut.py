"""Stress-based headcut advance — Theory Part 4 (docs/theory/04_headcut.md, Eqs. 4.3-4.9).

Hanson, Robinson & Cook (2001) deterministic headcut model with Robinson (1992) overfall stresses, as
implemented in SIMBA/WinDAM and printed in DSO-2017-02, App. A1, Eqs. 2-8. SI units throughout.
"""
from __future__ import annotations

import math

from .hydraulics import G, RHO_W

GAMMA_W = RHO_W * G


def critical_depth_unit(q: float) -> float:
    """d_c = (q^2/g)^(1/3) for unit discharge q [m2/s]."""
    return (max(q, 0.0) ** 2 / G) ** (1.0 / 3.0)


def face_stress(Hh: float, dc: float, dbw: float) -> float:
    """Robinson (1992) stress on the headcut face tau_hf [Pa], Eqs. (4.3)-(4.7). 0 if not plunging."""
    dbw = max(dbw, dc)
    if dc <= 0.0 or Hh <= dbw:
        return 0.0
    r = (Hh - dbw) / Hh
    Cn = 0.146 + 27.5 * r * (dc / Hh) ** 0.852 * math.exp(-6.1 * r)
    Xws = dc * ((0.823 + (Hh - dbw) / dc) / 0.483) ** (1.0 / (Cn + 1.6))
    Sws = -0.483 * (Cn + 1.6) * (Xws / dc) ** (Cn + 0.6)
    Xp = Xws - dbw / Sws - 0.411 * dc
    if Xp <= 0.0:
        return 0.0
    return 0.025 * GAMMA_W * dc * (Hh / dc) ** 0.026 * (dc / Xp) ** 1.06 * (dbw / dc) ** 0.221


def undercut_at_failure(Hh: float, dc: float, dbw: float, cu: float, gamma_t: float) -> float:
    """E_v [m] at incipient face failure, Eq. (4.8). <= 0: the face cannot stand undercut."""
    dbw = max(dbw, dc)
    a = gamma_t / 2.0
    b = GAMMA_W * dc - gamma_t * Hh / 2.0 - 2.0 * cu
    c = cu * Hh + 0.5 * GAMMA_W * dbw ** 2 - 0.375 * gamma_t * Hh ** 2 - 0.5 * GAMMA_W * dc * Hh
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return 0.0
    return (-b - math.sqrt(disc)) / (2.0 * a)


def advance_rate(Hh: float, dc: float, dbw: float, cu: float, gamma_t: float, kd: float, tau_c: float,
                 cap: float) -> float:
    """Headcut advance dX/dt [m/s], Eq. (4.9), capped at the 0.5H:1V surface-erosion rate `cap`."""
    tau = face_stress(Hh, dc, dbw)
    Ev = undercut_at_failure(Hh, dc, dbw, cu, gamma_t)
    if Ev <= 0.0:
        return cap
    r = Hh / (2.0 * Ev) * kd * max(tau - tau_c, 0.0)
    return min(r, cap)
