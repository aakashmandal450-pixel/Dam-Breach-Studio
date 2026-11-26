"""Piping stage 3b: the crater after an interior roof collapse (Theory Part 5, section 5.7a,
docs/theory/05_piping.md). Promoted from the reference implementation
verification/crater_balance_check.py, with the crater ends tied to the dam profile.

State (5.7a.2): x_1, x_2 (crater ends at the ground surface), W (width, starts at b_p), V_fall (intact
bulk volume of all soil that has fallen), V_pipe (pipe void inside the crater reach), V_exp (bulk debris
carried out), V_spoil (bulk debris set beside the crater when it would overfill it), W_c (all crater
water: free + pore), released (cumulative pore water brought in by fallen soil).

Geometry:
  V_open = V_pipe - (kappa - 1) V_fall + V_exp + V_spoil,  kappa = (1 - n)/(1 - n_d)     (5.18)
  z_d    = zbar_g - V_open / A_c,  A_c = (x_2 - x_1) W                                   (5.19)
  S(z)   = V_p(z) + A_c max(z - z_d, 0),  z_c = S^-1(W_c)                               (5.20)
Outflows: downstream reach entrance of open height a_open (5.25) as a pipe (5.2)-(5.4), spill (5.21).
Walls: undrained cut height (5.17) with the validity-domain guard; retreat by Delta = H_w/2 (5.7a.3).
Remnants: push-out (5.23).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .geometry import Dam, integrate_positive
from .hydraulics import G, RHO_W
from . import piping as pp

GAMMA_W = RHO_W * G
C_INLET = pp.C_INLET                    # 1.705 of (5.2) and (5.21)
WALL_DOMAIN = dict(r=(0.4, 0.6), xi=(0.0, 1.0), rho_p=(0.0, 0.5))


class DomainError(ValueError):
    """A wall check outside the range covered by the bound checks of (5.17) (5.7a.5)."""


def wall_critical_height(c0: float, gam: float, gw: float, rho: float, h_w: float, H_w: float,
                         tension: bool = True) -> float:
    """H_c = k c_u0 / (gamma - gamma_w xi^2 - 2 rho), k = 3.776 (2 with a tension cut-off) (5.17)."""
    xi = h_w / H_w if H_w > 0 else 0.0
    rho_p = rho * H_w / c0
    r = gw / gam
    if not (WALL_DOMAIN["xi"][0] <= xi <= WALL_DOMAIN["xi"][1] + 1e-12):
        raise DomainError(f"xi = h_w/H_w = {xi:g} outside [0, 1]")
    if xi > 0 and not (WALL_DOMAIN["r"][0] <= r <= WALL_DOMAIN["r"][1]):
        raise DomainError(f"gamma_w/gamma = {r:g} outside the checked range [0.4, 0.6]")
    if not (WALL_DOMAIN["rho_p"][0] <= rho_p <= WALL_DOMAIN["rho_p"][1]):
        raise DomainError(f"rho' = rho H_w/c_u0 = {rho_p:g} outside the checked range [0, 0.5]")
    den = gam - gw * xi * xi - 2.0 * rho
    if den <= 0:
        raise DomainError(f"denominator gamma - gamma_w xi^2 - 2 rho = {den:g} <= 0")
    return (3.776 if tension else 2.0) * c0 / den


def mean_ground(dam: Dam, x1: float, x2: float) -> float:
    pts = sorted({x1, x2} | {x for x in (dam.x_c0, dam.x_c1) if x1 < x < x2})
    return integrate_positive(dam.z_dam, pts) / (x2 - x1)


@dataclass
class Crater:
    dam: Dam
    x1: float
    x2: float
    W: float
    z_inv: float
    a_p: float
    b_p: float
    L_down: float          # downstream pipe reach length (crater end x_2 to the outlet)
    n: float = 0.35
    n_d: float = 0.35
    n_p: float = 0.016     # pipe Manning n
    V_fall: float = 0.0
    V_pipe: float = 0.0
    V_exp: float = 0.0
    V_spoil: float = 0.0
    W_c: float = 0.0
    released: float = 0.0
    pore_storage: bool = True
    debris: str = "level"      # 'level' (5.18-5.20, default) | 'instant' (removal) | 'tank' (DL Breach virtual tank)
    V_tank: float = 0.0        # bulk debris held in the virtual tank ('tank' mode)
    V_exp_out: float = 0.0     # bulk debris that has left the model domain (system export)

    # ---------------------------------------------------------------- geometry (5.18)-(5.19)
    @property
    def ell(self) -> float:
        return self.x2 - self.x1

    @property
    def zg(self) -> float:
        key = (self.x1, self.x2)
        if getattr(self, "_zg_key", None) != key:          # cache: the ends change only at events
            self._zg_key, self._zg = key, mean_ground(self.dam, self.x1, self.x2)
        return self._zg

    @property
    def z_rim(self) -> float:
        """Lowest ground elevation on the rim (the dam profile is concave, so at an end)."""
        return min(self.dam.z_dam(self.x1), self.dam.z_dam(self.x2))

    @property
    def kappa(self) -> float:
        return (1.0 - self.n) / (1.0 - self.n_d)

    @property
    def A_c(self) -> float:
        return self.ell * self.W

    @property
    def V_open(self) -> float:
        return self.V_pipe - (self.kappa - 1.0) * self.V_fall + self.V_exp + self.V_spoil

    @property
    def z_d(self) -> float:
        return self.zg - self.V_open / self.A_c

    @property
    def V_db(self) -> float:
        return self.kappa * self.V_fall - self.V_exp - self.V_spoil

    @property
    def z_cr(self) -> float:
        return self.z_inv + self.a_p

    # ---------------------------------------------------------------- storage (5.20)
    def V_p(self, z: float) -> float:
        if not self.pore_storage or self.V_db <= 0.0:
            return 0.0
        span = self.z_d - self.z_inv
        frac = 1.0 if span <= 0 else min(max((z - self.z_inv) / span, 0.0), 1.0)
        return self.n_d * self.V_db * frac

    def S(self, z: float) -> float:
        return self.V_p(z) + self.A_c * max(z - self.z_d, 0.0)

    def level(self) -> float:
        """z_c = S^-1(W_c) by bisection (S continuous and non-decreasing)."""
        if self.W_c <= 0.0:
            return self.z_inv
        lo, hi = self.z_inv, max(self.zg, self.z_d) + 1.0
        while self.S(hi) < self.W_c:
            hi += 10.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if self.S(mid) < self.W_c:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def free_water(self) -> float:
        return self.A_c * max(self.level() - self.z_d, 0.0)

    # ---------------------------------------------------------------- outflows (5.21), (5.25)
    def a_open(self) -> float:
        return min(max(self.z_cr - max(self.z_d, self.z_inv), 0.0), self.a_p)

    def Q_out(self, z_c: float | None = None) -> float:
        z_c = self.level() if z_c is None else z_c
        ao = self.a_open()
        if ao <= 0.0 or self.L_down <= 0.0:
            return 0.0
        z_o = max(self.z_d, self.z_inv)               # bottom of the open part of the entrance
        return pp.pipe_flow(z_c - z_o, self.b_p, ao, self.L_down, self.n_p).Q

    def Q_spill(self, z_c: float | None = None) -> float:
        z_c = self.level() if z_c is None else z_c
        return C_INLET * self.W * (z_c - self.z_rim) ** 1.5 if z_c > self.z_rim else 0.0

    # ---------------------------------------------------------------- events
    def fall(self, dV: float, S_r: float = 1.0, new_pipe: float = 0.0) -> None:
        """Soil of intact bulk volume dV falls in, bringing S_r n dV of pore water; new_pipe adds pipe void.
        Comparison treatments (5.7): 'instant' exports the bulked debris (kappa dV) out of the model domain at
        once; 'tank' removes it from the crater into the virtual tank. In both, the soil's pore water leaves
        with it and is not added to the crater water (it was never part of the water budget)."""
        self.V_fall += dV
        self.V_pipe += new_pipe
        if self.debris in ("instant", "tank"):
            moved = self.kappa * dV
            self.V_exp += moved                  # leaves the crater control volume
            if self.debris == "instant":
                self.V_exp_out += moved          # and the model domain
            else:
                self.V_tank += moved             # held in the virtual tank (inside the model)
            return
        if self.V_open < 0.0:                          # bulked debris would overfill: excess to spoil
            self.V_spoil += -self.V_open
        if self.pore_storage:
            w = S_r * self.n * dV
            self.W_c += w
            self.released += w

    def wall_heights(self):
        """Exposed height H_w and water depth h_w of the four walls: up end, down end, two sides (5.7a.3)."""
        zd, zc = self.z_d, self.level()
        z_up, z_dn, z_side = self.dam.z_dam(self.x1), self.dam.z_dam(self.x2), self.zg
        out = {}
        for k, zg in (("up", z_up), ("down", z_dn), ("side", z_side)):
            Hw = max(zg - zd, 0.0)
            out[k] = (Hw, max(0.0, min(zc, zg) - zd))
        return out

    def retreat_wall(self, which: str, S_r: float = 1.0) -> float:
        """Fail wall 'up' | 'down' | 'side' | 'sides' (both sides): vertical retreat by Delta = H_w/2, wedge
        volume 1/2 H_w^2 per unit length into V_fall; end walls also expose the pipe void below the floor,
        b_p clip(z_d - z_inv, 0, a_p) Delta (= b_p a_p Delta while the debris is above the crown)."""
        H = self.wall_heights()
        if which in ("up", "down"):
            Hw = H[which][0]
            d = 0.5 * Hw
            zd = self.z_d
            xa, xb = (self.x1 - d, self.x1) if which == "up" else (self.x2, self.x2 + d)
            # soil above the floor over the new strip, exact for the dam profile (draft 5.11 correction):
            # 1/2 H_w^2 W assumes level ground and over-counts on a sloping face, which breaks (5.18)-(5.19)
            pts = sorted({xa, xb} | {x for x in (self.dam.x_c0, self.dam.x_c1) if xa < x < xb})
            wedge = self.W * integrate_positive(lambda x: self.dam.z_dam(x) - zd, pts)
            if which == "up":
                self.x1 -= d
            else:
                self.x2 += d
            # newly exposed pipe void: only the part of the pipe below the floor; above the floor it lies inside
            # the wedge column already (draft 5.11 correction: needed once z_d < z_cr, e.g. instant removal)
            below = min(max(zd - self.z_inv, 0.0), self.a_p)
            self.fall(wedge, S_r, new_pipe=self.b_p * below * d)
            if which == "down":
                self.L_down = max(self.L_down - d, 0.0)
            return d
        Hw = H["side"][0]
        d = 0.5 * Hw
        nside = 2 if which == "sides" else 1
        self.W += nside * d
        self.fall(nside * 0.5 * Hw * Hw * self.ell, S_r)
        return d


def remnant_area_and_strength(dam: Dam, z_cr: float, xa: float, xb: float, c_u0: float, rho: float):
    """Remnant roof area A_r between xa and xb, and the mean c_u over its cover, c_u0 + rho dbar
    (dbar = mean depth below the ground over the remnant cover, exact for the piecewise-linear profile)."""
    if xb <= xa:
        return 0.0, c_u0
    pts = sorted({xa, xb} | {x for x in (dam.x_c0, dam.x_c1) if xa < x < xb})
    A = m1 = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        ta, tb = max(dam.z_dam(a) - z_cr, 0.0), max(dam.z_dam(b) - z_cr, 0.0)
        h = b - a
        A += 0.5 * (ta + tb) * h
        m1 += h * (ta * ta + ta * tb + tb * tb) / 6.0      # integral of t^2/2 for t linear
    if A <= 0.0:
        return 0.0, c_u0
    return A, c_u0 + rho * m1 / A


def pushout_margins(dam: Dam, z_cr: float, b_p: float, z_s: float, z_c: float,
                    x_in: float, x1: float, x2: float, x_o: float, c_u0: float, rho: float):
    """(5.23): resistance minus driving force of the upstream and downstream remnants [N/m width]."""
    A_up, c_up = remnant_area_and_strength(dam, z_cr, x_in, x1, c_u0, rho)
    A_dn, c_dn = remnant_area_and_strength(dam, z_cr, x2, x_o, c_u0, rho)
    pos = lambda v: max(v, 0.0)
    drive_up = 0.5 * GAMMA_W * b_p * (pos(z_s - z_cr) ** 2 - pos(z_c - z_cr) ** 2)
    drive_dn = 0.5 * GAMMA_W * b_p * pos(z_c - z_cr) ** 2
    return 2.0 * c_up * A_up - drive_up, 2.0 * c_dn * A_dn - drive_dn
