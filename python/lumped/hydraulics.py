"""Breach hydraulics — Theory Part 1 (docs/theory/01_reservoir_and_breach_hydraulics.md).

All functions are scalar and pure. Equation numbers refer to Part 1.
"""
from __future__ import annotations

import math

G = 9.81          # m/s2
RHO_W = 1000.0    # kg/m3


def bisect(f, lo: float, hi: float, rtol: float = 1e-12, maxit: int = 200) -> float:
    """Root of a function that changes sign on [lo, hi] (no scipy dependency)."""
    flo, fhi = f(lo), f(hi)
    if flo == 0.0:
        return lo
    if fhi == 0.0:
        return hi
    if flo * fhi > 0.0:
        raise ValueError(f"root not bracketed on [{lo}, {hi}]: f = {flo}, {fhi}")
    for _ in range(maxit):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if fm == 0.0 or (hi - lo) <= rtol * max(abs(mid), 1e-300):
            return mid
        if flo * fm < 0.0:
            hi = mid
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


# ---- trapezoid section: bottom width b, side slope m (horizontal : vertical) ----------------------

def area(b: float, m: float, y: float) -> float:
    return (b + m * y) * y


def top_width(b: float, m: float, y: float) -> float:
    return b + 2.0 * m * y


def wetted_perimeter(b: float, m: float, y: float) -> float:
    return b + 2.0 * y * math.sqrt(1.0 + m * m)


def hydraulic_radius(b: float, m: float, y: float) -> float:
    p = wetted_perimeter(b, m, y)
    return area(b, m, y) / p if p > 0.0 else 0.0


# ---- weir control: (1.4)-(1.6) ----------------------------------------------------------------------

def critical_depth(b: float, m: float, H: float) -> float:
    """Critical depth y_c on the breach top for specific energy H (1.4): y + A/(2T) = H."""
    if H <= 0.0 or (b <= 0.0 and m <= 0.0):
        return 0.0
    f = lambda y: y + area(b, m, y) / (2.0 * top_width(b, m, y)) - H
    return bisect(f, 1e-15 * H, H)


def weir_exact(b: float, m: float, H: float, Cd: float = 1.0) -> float:
    """Free breach discharge from exact critical flow in a trapezoid (1.5). Default weir."""
    y = critical_depth(b, m, H)
    if y <= 0.0:
        return 0.0
    A, T = area(b, m, y), top_width(b, m, y)
    return Cd * math.sqrt(G * A ** 3 / T)


def weir_dlbreach(b: float, m: float, H: float, c1: float = 1.7, c2: float = 1.3) -> float:
    """DL Breach weir formula (1.6), Wu (2016) Eq. 3.1 — option for the benchmark."""
    if H <= 0.0:
        return 0.0
    return c1 * b * H ** 1.5 + c2 * m * H ** 2.5


def submergence(z_s: float, z_t: float, z_b: float) -> float:
    """Tailwater submergence factor k_sm (1.7), Wu (2016) Eq. 3.2."""
    if z_s <= z_b:
        return 0.0
    S = (z_t - z_b) / (z_s - z_b)
    if S < 0.67:
        return 1.0
    return max(1.0 - 27.8 * (S - 0.67) ** 3, 0.0)


def crest_overflow(length: float, head: float) -> float:
    """Rectangular broad-crested overflow on the intact crest (1.8), C_d = 1."""
    if length <= 0.0 or head <= 0.0:
        return 0.0
    return math.sqrt(G) * (2.0 / 3.0) ** 1.5 * length * head ** 1.5


# ---- uniform flow and shear: (1.11)-(1.12) ----------------------------------------------------------

def normal_depth(Q: float, b: float, m: float, n: float, S0: float) -> float:
    """Manning normal depth on the downstream slope (1.11)."""
    if Q <= 0.0 or S0 <= 0.0:
        return 0.0
    f = lambda h: area(b, m, h) * hydraulic_radius(b, m, h) ** (2.0 / 3.0) * math.sqrt(S0) / n - Q
    hi = 1e-3
    while f(hi) < 0.0:
        hi *= 2.0
        if hi > 1e6:
            raise ValueError("normal depth not bracketed")
    return bisect(f, 1e-15, hi)


def manning_shear(Q: float, A: float, R: float, n: float) -> float:
    """Bed shear from Manning (1.12): tau = rho g n^2 Q^2 / (A^2 R^(1/3))."""
    if Q <= 0.0 or A <= 0.0 or R <= 0.0:
        return 0.0
    return RHO_W * G * n * n * Q * Q / (A * A * R ** (1.0 / 3.0))
