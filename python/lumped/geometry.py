"""Dam and breach geometry, side-slope stability — Theory Part 3
(docs/theory/03_widening_and_bank_stability.md).

Longitudinal coordinate x along the flow, x = 0 at the upstream toe, base at z = 0. The dam profile is
upstream face (H:V = zu), crest of width Wc at elevation H, downstream face (H:V = zd).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .hydraulics import G, RHO_W


@dataclass
class Dam:
    H: float          # dam height = crest elevation above base [m]
    Wc: float         # crest width in the flow direction [m]
    zu: float         # upstream slope, horizontal : vertical
    zd: float         # downstream slope, horizontal : vertical
    L_cr: float       # crest length across the valley (breach width limit) [m]

    @property
    def x_c0(self) -> float:          # upstream crest edge
        return self.zu * self.H

    @property
    def x_c1(self) -> float:          # downstream crest edge
        return self.zu * self.H + self.Wc

    @property
    def x_T(self) -> float:           # downstream toe
        return self.x_c1 + self.zd * self.H

    def z_dam(self, x: float) -> float:
        if x <= 0.0 or x >= self.x_T:
            return 0.0
        if x < self.x_c0:
            return x / self.zu
        if x <= self.x_c1:
            return self.H
        return (self.x_T - x) / self.zd

    def x_up(self, z: float) -> float:
        """x of the upstream face at elevation z."""
        return self.zu * min(max(z, 0.0), self.H)

    def x_down(self, z: float) -> float:
        """x of the original downstream face at elevation z."""
        return self.x_T - self.zd * min(max(z, 0.0), self.H)


def integrate_positive(f, xs) -> float:
    """Exact integral of max(f, 0) for f linear between the sorted breakpoints xs."""
    total = 0.0
    for a, b in zip(xs[:-1], xs[1:]):
        if b <= a:
            continue
        fa, fb = f(a), f(b)
        if fa >= 0.0 and fb >= 0.0:
            total += 0.5 * (fa + fb) * (b - a)
        elif fa > 0.0 or fb > 0.0:          # sign change: integrate the positive triangle
            xr = a + (b - a) * fa / (fa - fb)
            total += 0.5 * fa * (xr - a) if fa > 0.0 else 0.5 * fb * (b - xr)
    return total


def side_area_top(dam: Dam, x_a: float, x_b: float, z_b: float) -> float:
    """A_side on the flat top: dam section above z_b between x_a and x_b (Wu 2016, Fig. 4.6)."""
    pts = sorted({x_a, x_b} | {x for x in (dam.x_c0, dam.x_c1) if x_a < x < x_b})
    return integrate_positive(lambda x: dam.z_dam(x) - z_b, pts)


def side_area_slope(dam: Dam, x_e: float, z_e: float) -> float:
    """A_side on the downstream-slope reach: dam section above the line (x_e, z_e) -> toe."""
    xT = dam.x_T
    if xT - x_e <= 0.0:
        return 0.0
    line = lambda x: z_e * (xT - x) / (xT - x_e)
    pts = sorted({x_e, xT} | {x for x in (dam.x_c0, dam.x_c1) if x_e < x < xT})
    return integrate_positive(lambda x: dam.z_dam(x) - line(x), pts)


# ---- side slope from planar bank stability: (3.11)-(3.14) -------------------------------------------

def bulk_unit_weight(porosity: float, rho_s: float = 2650.0, f_w: float = 0.5) -> float:
    """gamma_b = (1 - p) gamma_s + f_w p gamma_w (3.11), Wu (2016) Eq. 4.23."""
    return ((1.0 - porosity) * rho_s + f_w * porosity * RHO_W) * G


def steepest_stable_slope(C: float, gamma_b: float, H: float, phi: float) -> float:
    """beta_s [rad] from (3.12), Wu (2016) Eq. 4.25. C = 0 -> phi."""
    if C <= 0.0 or H <= 0.0:
        return phi if C <= 0.0 else 0.5 * math.pi
    t = math.tan(phi)
    a = C / (gamma_b * H)
    root = math.sqrt((16.0 * a * a + 8.0 * a * t) * (1.0 + t * t))
    cot = 1.0 / t + (4.0 * a - root) / (t * t)
    return math.atan2(1.0, cot) if cot > 0.0 else 0.5 * math.pi


def failure_angle(C: float, gamma_b: float, H: float, phi: float, beta_s: float) -> float:
    """alpha_s [rad] from (3.13), Wu (2016) Eq. 4.26."""
    if C <= 0.0:
        return phi
    cot_b = math.cos(beta_s) / math.sin(beta_s)
    a = C / (gamma_b * H)
    tan_a = 0.5 * (1.0 + math.tan(phi) * cot_b) / (2.0 * a + cot_b)
    return math.atan(tan_a)


def side_slope_angle(C: float, gamma_b: float, H: float, phi: float) -> float:
    """beta = (alpha_s + beta_s)/2 (3.14), Wu (2016) Eq. 4.27 [rad].

    While even a vertical bank of height H is stable (no real root of (3.12)), no failure has happened
    yet and the wall stays vertical — Wu (2016, Sec. 4.4): the side slope starts vertical in a shallow
    pilot breach. (Averaging with the alpha of (3.13) there would make beta rise with H, which is not
    physical.)"""
    H = max(H, 1e-6)
    bs = steepest_stable_slope(C, gamma_b, H, phi)
    if bs >= 0.5 * math.pi - 1e-12:
        return 0.5 * math.pi
    return 0.5 * (failure_angle(C, gamma_b, H, phi, bs) + bs)


def culmann_critical_height(C: float, gamma_b: float, beta: float, phi: float) -> float:
    """Culmann H_c = 4C sin(beta) cos(phi) / (gamma_b (1 - cos(beta - phi))) — cross-check of (3.12)."""
    if beta <= phi:
        return math.inf
    return 4.0 * C * math.sin(beta) * math.cos(phi) / (gamma_b * (1.0 - math.cos(beta - phi)))
