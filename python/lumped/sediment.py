"""Bed erosion — Theory Part 2 (docs/theory/02_bed_erosion.md). Scalar, pure functions."""
from __future__ import annotations

import math

from .hydraulics import G, RHO_W

NU = 1.0e-6   # kinematic viscosity of water [m2/s]


def settling_velocity(d: float, rho_s: float = 2650.0, nu: float = NU) -> float:
    """Soulsby (1997) settling velocity of a grain of size d [m/s] (same as the 2-D engine)."""
    s = rho_s / RHO_W
    dstar = d * ((s - 1.0) * G / nu ** 2) ** (1.0 / 3.0)
    return nu / d * (math.sqrt(10.36 ** 2 + 1.049 * dstar ** 3) - 10.36)


# ---- cohesive: (2.1) --------------------------------------------------------------------------------

def cohesive_rate(tau: float, tau_c: float, kd: float, n_exp: float = 1.0) -> float:
    """Excess-shear erosion rate eps = kd (tau - tau_c)^n [m/s]; kd in m3/(N s) (already x f_kd)."""
    ex = tau - tau_c
    return kd * ex ** n_exp if ex > 0.0 else 0.0


# ---- non-cohesive capacity, DL Breach combination: (2.3)-(2.5b) ------------------------------------

def critical_shear_wu(d: float, rho_s: float = 2650.0) -> float:
    """tau_c = 0.03 (gamma_s - gamma) d — Wu et al. (2000), as used in DL Breach."""
    return 0.03 * (rho_s - RHO_W) * G * d


def grain_shear_wu(tau_b: float, n: float, d: float) -> float:
    """tau_b' = (n'/n)^(3/2) tau_b, n' = d^(1/6)/20 — Wu et al. (2000)."""
    n_p = d ** (1.0 / 6.0) / 20.0
    return (n_p / n) ** 1.5 * tau_b


def slope_effective_shear(tau_p: float, tau_c: float, beta: float, phi_r: float) -> float:
    """DL Breach steep-slope correction (2.5a-b), Wu (2016) Eqs. 4.8-4.9. beta, phi_r in radians."""
    if beta <= 0.0:
        lam = 1.0
    else:
        lam = 1.0 + 0.22 * (max(tau_p, 0.0) / tau_c) ** 0.15 * math.exp(2.0 * math.sin(beta) / math.sin(phi_r))
    return tau_p + lam * tau_c * math.sin(beta) / math.sin(phi_r)


def chiew_parker_tau_c(tau_c: float, beta: float, phi: float) -> float:
    """Option: tau_c,beta = tau_c sin(phi - beta)/sin(phi) (2.5), Chiew & Parker (1994)."""
    return max(tau_c * math.sin(phi - beta) / math.sin(phi), 0.0)


def wu_bedload(tau_e: float, tau_c: float, d: float, rho_s: float = 2650.0) -> float:
    """Wu et al. (2000) single-size bed-load capacity q_b* [m2/s] (2.3)."""
    T = tau_e / tau_c - 1.0
    if T <= 0.0:
        return 0.0
    s = rho_s / RHO_W
    return 0.0053 * T ** 2.2 * math.sqrt((s - 1.0) * G * d ** 3)


def zhang_suspended_mass(U: float, R: float, ws: float) -> float:
    """Zhang (1961) suspended-load capacity, Guo (2002) fit (2.4a), Wu (2016) Eq. 4.6 [kg/m3]."""
    if U <= 0.0 or R <= 0.0:
        return 0.0
    X = U ** 3 / (G * R * ws)
    return (X ** 1.5 / 20.0) / (1.0 + (X / 45.0) ** 1.15)


def capacity_dlbreach(Q: float, U: float, R: float, b: float, tau_e: float, tau_c: float,
                      d: float, rho_s: float, ws: float, f_t: float) -> float:
    """Total-load capacity as a volume concentration (2.4b): f_t (C*/rho_s + q_b* b / Q)."""
    if Q <= 0.0:
        return 0.0
    c_s = zhang_suspended_mass(U, R, ws) / rho_s
    c_b = wu_bedload(tau_e, tau_c, d, rho_s) * b / Q
    return f_t * (c_s + c_b)


# ---- non-equilibrium relaxation: (2.7) --------------------------------------------------------------

def relax(c_in: float, c_star: float, length: float, ls: float) -> float:
    """C_out = C* + (C_in - C*) exp(-L/Ls), Wu (2016) Eq. 4.3."""
    if length <= 0.0:
        return c_in
    if ls <= 0.0:
        return c_star
    return c_star + (c_in - c_star) * math.exp(-length / ls)
