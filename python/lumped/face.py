"""Stability of the downstream face at the pipe outlet (Theory Part 5, draft F-1, §5.6b; for review).

Standalone module: not yet called by the piping driver. Two alternative failure geometries, never
combined in one run, both by force equilibrium on a planar base (moments and toppling not checked):

  G1  finite face slab: base parallel to the original face (angle beta), vertical tension crack at x_b;
      where the base passes below the pipe crown (x_u < x < x_d) it lies in the pipe void (width b = w)
      and carries nothing: the outlet undermines the slab
  G2  Culmann wedge: base through the outlet toe point (x_d, z_cr) at angle alpha, crack at x_b; with
      u = 0, c_s = 0 and no sides it is the Part 3 planar wedge (3.9)-(3.10)

Both are one planar block: base angle theta, crown-level intersection x_u (G1: x_u < x_d; G2: x_u = x_d).

    D = W sin(theta) + F_w cos(theta)
    R = sum_base (c' + c_s) w ds + max(W cos(theta) - U - F_w sin(theta), 0) tan(phi') + 2 S_side   (F.4)
    S_side = int_A [(c' + c_s) + K0 (sigma_v - u) tan(phi')] dA,  K0 = 1 - sin(phi')                 (F.5)

Pore pressure and strength by scenario (each documented separately; the undrained c_u of the roof check
is not used here):
  P0  initial face: u = 0, c_s everywhere, moist unit weight
  P1  transient wetting from the pipe: a wetted zone of thickness delta above the crown (Green-Ampt, F.6),
      u = gamma_w h_p (1 - (z - z_cr)/delta) inside it, c_s = 0 and saturated weight inside
  P2  steady seepage (upper bound): Kozeny-Casagrande phreatic line, u = gamma_w (z_ph - z) cos^2(theta_ph)
      below it, c_s = 0 and saturated weight below; water in the tension crack below the line
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

GAMMA_W = 9810.0


# ------------------------------------------------------------------ soil and the local face profile
@dataclass(frozen=True)
class FaceSoil:
    c_eff: float          # drained cohesion c' [Pa]
    tan_phi: float        # tan phi' (drained)
    c_s: float            # apparent cohesion from suction of the unwetted soil [Pa] (scenario value)
    gamma_moist: float    # [N/m3]
    gamma_sat: float      # [N/m3]
    sides: bool = True    # lateral-plane resistance (F.5); False = plane strain per unit width
    K0: float | None = None   # None: Jaky 1 - sin(phi'); 0: cohesion only on the sides

    @property
    def k0(self) -> float:
        if self.K0 is not None:
            return self.K0
        return 1.0 - math.sin(math.atan(self.tan_phi))


@dataclass
class Profile:
    """Ground surface over the pipe column as a polyline (x increasing). Initially the dam section;
    each face failure cuts its block out (draft F-1, §5.3)."""
    x: list
    z: list

    @classmethod
    def from_dam(cls, dam) -> "Profile":
        xs = [0.0, dam.x_c0, dam.x_c1, dam.x_c1 + dam.zd * dam.H]
        return cls(xs, [0.0, dam.H, dam.H, 0.0])

    def __call__(self, x):
        return np.interp(x, self.x, self.z)

    def daylight(self, z_cr: float) -> float:
        """The outlet (F.2): going downstream from the highest point, the first x where the surface comes
        down to the crown level, i.e. where the continuous roof over the pipe ends."""
        xs, zs = self.x, self.z
        k0 = int(np.argmax(zs))
        for k in range(k0 + 1, len(xs)):
            za, zb = zs[k - 1], zs[k]
            if za <= z_cr:
                return xs[k - 1]
            if zb <= z_cr:
                return xs[k - 1] + (za - z_cr) / (za - zb) * (xs[k] - xs[k - 1])
        raise ValueError("the surface never comes down to the crown level")

    def cut(self, x_b: float, x_d: float, bottom, breaks=()) -> "Profile":
        """New profile with the block between x_b and x_d removed down to bottom(x). breaks: kinks of the
        bottom (e.g. x_u, where the slab base meets the crown) so the polyline follows it exactly."""
        inner = [x for x in list(self.x) + list(breaks) if x_b < x < x_d]
        xs = sorted(set(inner) | {x_b, x_d})
        top = self(np.array(xs))
        bot = np.minimum(np.array([bottom(x) for x in xs]), top)
        left = [(x, z) for x, z in zip(self.x, self.z) if x < x_b]
        right = [(x, z) for x, z in zip(self.x, self.z) if x > x_d]
        pts = left + [(x_b, float(self(x_b)))] + [(x, float(v)) for x, v in zip(xs, bot)] + right
        return Profile([p[0] for p in pts], [p[1] for p in pts])


# ------------------------------------------------------------------ pore-pressure scenarios
@dataclass(frozen=True)
class Scenario:
    kind: str                       # 'P0' | 'P1' | 'P2'
    delta: float = 0.0              # P1: wetted thickness above the crown [m]
    h_p: float = 0.0                # P1: pressure head at the crown near the outlet [m]
    phreatic: object = None         # P2: callable x -> (z_ph, theta_ph)


def casagrande_phreatic(dam, z_s: float):
    """P2: Kozeny basic parabola with focus at the downstream toe, d from the 0.3 rule (Casagrande 1937),
    lowered to the face where it would lie above it (exit-correction approximation, stated)."""
    m_u, m_d, H = dam.zu, dam.zd, dam.H
    x_t = dam.x_c1 + m_d * H
    Bp = m_u * z_s - 0.3 * m_u * z_s
    d = x_t - Bp
    y0 = math.sqrt(d * d + z_s * z_s) - d

    def f(x):
        xp = max(x_t - x, 0.0)
        y = math.sqrt(2.0 * y0 * xp + y0 * y0)
        dy = y0 / y                                   # -dz/dx of the parabola
        z_face = (x_t - x) / m_d if x > dam.x_c1 else H
        if y >= z_face:
            return z_face, math.atan(1.0 / m_d)
        return y, math.atan(dy)
    return f


def casagrande_exit(dam, z_s: float):
    """Exit point of the phreatic line on the downstream face (Casagrande; slope angle < 30 deg)."""
    m_u, m_d = dam.zu, dam.zd
    x_t = dam.x_c1 + m_d * dam.H
    beta = math.atan(1.0 / m_d)
    d = x_t - 0.7 * m_u * z_s
    a = d / math.cos(beta) - math.sqrt(d * d / math.cos(beta) ** 2 - z_s * z_s / math.sin(beta) ** 2)
    return x_t - a * math.cos(beta), a * math.sin(beta)


def green_ampt_up(delta0: float, dt: float, K_s: float, H: float, d_theta: float) -> float:
    """(F.6) without the crown-erosion term: upward wetting front from a pipe wall at constant head
    H = h_p + psi_f, gravity opposing. Exact: t(delta) = (d_theta/K_s) [-delta - H ln(1 - delta/H)],
    advanced by inverting t(delta0) + dt (bisection). delta -> H as t -> infinity."""
    if H <= 0.0:
        return delta0

    def T(d):
        return (d_theta / K_s) * (-d - H * math.log(1.0 - d / H))
    target = T(min(delta0, H * (1 - 1e-15))) + dt
    lo, hi = delta0, H * (1.0 - 1e-15)
    if T(hi) <= target:
        return hi
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if T(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return 0.5 * (lo + hi)


# ------------------------------------------------------------------ one planar block
@dataclass
class Block:
    geometry: str           # 'G1' | 'G2'
    theta: float            # base angle [rad]
    x_b: float              # back scarp (tension crack)
    x_u: float              # where the base reaches crown level
    x_d: float              # outlet (crown daylight)
    W: float = 0.0
    U: float = 0.0
    F_w: float = 0.0        # water in the crack (P2 only)
    C_base: float = 0.0     # cohesive base resistance
    friction: float = 0.0
    S_side: float = 0.0
    D: float = 0.0
    R: float = 0.0
    A: float = 0.0          # profile area of the block [m2]
    V: float = 0.0          # block volume w A [m3]
    t: float = 0.0          # G1: vertical slab thickness
    info: dict = field(default_factory=dict)

    @property
    def FS(self) -> float:
        return self.R / self.D if self.D > 0 else math.inf

    @property
    def M(self) -> float:
        return self.R - self.D


def evaluate(geometry: str, theta: float, x_b: float, x_u: float, x_d: float, z_cr: float, prof: Profile,
             soil: FaceSoil, sc: Scenario, w: float, nx: int = 160, nz: int = 24) -> Block:
    """Forces on the block between x_b and x_d with planar base z_p(x) = z_cr + (x_u - x) tan(theta);
    for x > x_u the block bottom is the pipe crown (void below, no base support)."""
    blk = Block(geometry, theta, x_b, x_u, x_d)
    if not x_b < x_u <= x_d:
        blk.D, blk.R = 0.0, math.inf
        return blk
    tt, ct, st = math.tan(theta), math.cos(theta), math.sin(theta)
    xs = np.linspace(x_b, x_d, nx + 1)
    xm = 0.5 * (xs[1:] + xs[:-1])
    dx = np.diff(xs)
    top = prof(xm)
    zp = z_cr + (x_u - xm) * tt
    supported = xm <= x_u
    bottom = np.where(supported, zp, z_cr)
    h = np.maximum(top - bottom, 0.0)
    # vertical point sets in each column (midpoint rule)
    fz = (np.arange(nz) + 0.5) / nz
    Z = bottom[:, None] + h[:, None] * fz[None, :]
    dA = (h * dx)[:, None] / nz * np.ones((1, nz))
    sat, u, cs = _fields(sc, soil, xm, Z, z_cr)
    gam = np.where(sat, soil.gamma_sat, soil.gamma_moist)
    W = w * float(np.sum(gam * dA))
    A = float(np.sum(dA))
    # base: supported columns only, at the base elevation
    _, u_b, cs_b = _fields(sc, soil, xm, zp[:, None], z_cr)
    u_b, cs_b = u_b[:, 0], cs_b[:, 0]
    ds = dx / ct
    U = w * float(np.sum(np.where(supported & (h > 0), u_b * ds, 0.0)))
    C_base = w * float(np.sum(np.where(supported & (h > 0), (soil.c_eff + cs_b) * ds, 0.0)))
    # water in the crack (P2): hydrostatic over the part of the scarp below the phreatic line
    F_w = 0.0
    if sc.kind == "P2" and h[0] > 0:
        z_ph, _ = sc.phreatic(x_b)
        hw = max(min(z_ph, float(prof(x_b))) - float(zp[0] if supported[0] else z_cr), 0.0)
        F_w = 0.5 * GAMMA_W * hw * hw * w
    N_eff = W * ct - U - F_w * st
    friction = max(N_eff, 0.0) * soil.tan_phi
    S_side = 0.0
    if soil.sides:
        # sigma_v at a point = weight of the column above it (unit weights by zone), per unit area
        cum = np.cumsum((gam * (h[:, None] / nz))[:, ::-1], axis=1)[:, ::-1] - 0.5 * gam * (h[:, None] / nz)
        sig_eff = np.maximum(cum - u, 0.0)
        S_side = float(np.sum(((soil.c_eff + cs) + soil.k0 * sig_eff * soil.tan_phi) * dA))
    blk.W, blk.U, blk.F_w, blk.C_base, blk.friction, blk.S_side, blk.A = W, U, F_w, C_base, friction, S_side, A
    blk.D = W * st + F_w * ct
    blk.R = C_base + friction + 2.0 * S_side
    blk.V = w * A
    blk.info = dict(N_eff=N_eff)
    return blk


def _fields(sc: Scenario, soil: FaceSoil, xm, Z, z_cr):
    """Saturated flag, pore pressure u and suction cohesion c_s at points Z[i, j] above x = xm[i]."""
    if sc.kind == "P0":
        return np.zeros(Z.shape, bool), np.zeros(Z.shape), np.full(Z.shape, soil.c_s)
    if sc.kind == "P1":
        rel = Z - z_cr
        wet = (rel >= -1e-12) & (rel <= sc.delta) if sc.delta > 0 else np.zeros(Z.shape, bool)
        u = np.where(wet, GAMMA_W * max(sc.h_p, 0.0) * (1.0 - np.clip(rel / max(sc.delta, 1e-12), 0, 1)), 0.0)
        return wet, u, np.where(wet, 0.0, soil.c_s)
    if sc.kind == "P2":
        ph = [sc.phreatic(float(x)) for x in xm]
        zph = np.array([p[0] for p in ph])[:, None]
        c2 = np.array([math.cos(p[1]) ** 2 for p in ph])[:, None]
        below = Z < zph
        u = np.where(below, GAMMA_W * (zph - Z) * c2, 0.0)
        return below, u, np.where(below, 0.0, soil.c_s)
    raise ValueError(sc.kind)


# ------------------------------------------------------------------ critical block searches
C_MIN = 0.25    # end-lip limit of the roof check (cover < 0.25 b is not checked), reused as the thinnest block


def critical_G1(prof: Profile, z_cr: float, beta: float, x_back_min: float, soil: FaceSoil, sc: Scenario,
                w: float, t_max: float, nt: int = 40, nb: int = 40, b: float | None = None, **kw) -> Block:
    """min FS over slab thickness t in [t_min, t_max] and back scarp x_b in [x_back_min, x_d - L_min].
    Resolution limits (no new parameter; draft F-1 review question): t_min = 0.25 b, the end-lip limit of
    the roof check, and L_min = b/2, the section spacing. Without them the minimum degenerates to a
    vanishing block at the outlet edge."""
    x_d = prof.daylight(z_cr)
    b = w if b is None else b
    t_min, L_min = C_MIN * b, 0.5 * b
    best = None
    for t in np.linspace(t_min, max(t_max, t_min), nt):
        x_u = x_d - t / math.tan(beta)
        x_hi = min(x_u - 1e-9, x_d - L_min)
        if x_hi <= x_back_min:
            continue
        for x_b in np.linspace(x_back_min, x_hi, nb + 1):
            blk = evaluate("G1", beta, float(x_b), float(x_u), x_d, z_cr, prof, soil, sc, w, **kw)
            blk.t = float(t)
            if blk.D > 0 and (best is None or blk.FS < best.FS):
                best = blk
    if best is not None:
        best.info["at_limit"] = (abs(best.t - t_min) < 1e-12 or abs((x_d - best.x_b) - L_min) < 1e-9)
        best.info["limits"] = dict(t_min=t_min, L_min=L_min)
    return best


def critical_G2(prof: Profile, z_cr: float, beta: float, x_back_min: float, soil: FaceSoil, sc: Scenario,
                w: float, na: int = 40, nb: int = 40, alpha_min: float = math.radians(1.0), crack: bool = True,
                b: float | None = None, **kw) -> Block:
    """min FS over the plane angle alpha in [alpha_min, beta) through the toe point and x_b. crack=False:
    no tension crack, the plane runs out to the surface (x_b at the intersection; the Culmann wedge of
    Part 3). A crack carries no resistance, so with it the minimum FS is lower than Culmann's."""
    x_d = prof.daylight(z_cr)
    bw = w if b is None else b
    L_min, t_min = 0.5 * bw, C_MIN * bw
    tb = math.tan(beta)
    best = None
    for a in np.linspace(alpha_min, beta, na + 1)[:-1]:
        # thinnest block: the wedge's depth at the scarp, (x_d - x_b)(tan beta - tan alpha), >= t_min
        x_hi = min(x_d - L_min, x_d - t_min / max(tb - math.tan(a), 1e-12))
        if crack:
            if x_hi <= x_back_min:
                continue
            xbs = np.linspace(x_back_min, x_hi, nb + 1)
        else:
            xbs = [_runout(prof, z_cr, x_d, float(a), x_back_min)]
        for x_b in xbs:
            blk = evaluate("G2", float(a), float(x_b), x_d, x_d, z_cr, prof, soil, sc, w, **kw)
            if blk.D > 0 and (best is None or blk.FS < best.FS):
                best = blk
    if best is not None:
        depth = (x_d - best.x_b) * (tb - math.tan(best.theta))
        best.t = depth
        best.info["at_limit"] = crack and (abs(depth - t_min) < 1e-6 or abs((x_d - best.x_b) - L_min) < 1e-9)
        best.info["limits"] = dict(t_min=t_min, L_min=L_min)
    return best


def _runout(prof: Profile, z_cr: float, x_d: float, a: float, x_min: float) -> float:
    """Upstream point where the plane z_cr + (x_d - x) tan(a) meets the surface (x_min if it never does)."""
    f = lambda x: float(prof(x)) - (z_cr + (x_d - x) * math.tan(a))
    lo, hi = x_min, x_d - 1e-9
    if f(lo) > 0:
        return x_min
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)
