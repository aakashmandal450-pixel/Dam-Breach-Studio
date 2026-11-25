"""Piping stage 2: roof check along the pipe (Theory Part 5, sections 5.5 and 5.5b,
docs/theory/05_piping.md).

At sections x along the pipe, spaced dx (= b_p/2 by default, 5.5b):
    cover          C(x)   = z_dam(x) - z_cr
    surface load   sigma_s = gamma_w max(z_s - z_dam(x), 0) on the upstream face, 0 on crest and downstream face
    soffit         p_s(x) from (5.8): full pipe only, falls with entrance loss and friction, >= 0
    unit weight    gamma_bar from (5.24): saturated below the phreatic level z_ph = z_s, moist above
    criterion      c_u0 N_b < sigma_s - p_s < c_u0 N_c                         (5.15)
                   N from the stability table; full pipe through the exact identity (5.16b);
                   part-full pipe: N_0 (crown pressure 0), the lower edge of the band (5.16)
    margins        M_c = c_u0 N_c - (sigma_s - p_s),  M_b = (sigma_s - p_s) - c_u0 N_b

Policy (5.5b, decided 2026-11-25): a section whose table query meets a no-stable-state node is
collapsed (margin -inf) and listed in `no_stable` with the table status; a table range error is a
numerical error and is raised, never turned into a collapse.

End lips (decision for review, draft 5.5): sections where the cover is thinner than the table's
smallest C/b_p (0.25) lie at the two ends of the pipe, where the pipe meets the faces. The plane-strain
section model does not describe them, and the table does not cover them. They are not checked; their
extent is reported (`lips`). They are part of the face for the roof check. Their roof is removed by the
exit mechanisms of 5.6 at the downstream end and is under the reservoir at the upstream end.

Mechanism A (5.9) and B (5.10) are computed for comparison and as the separate push-out check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .geometry import Dam, integrate_positive
from .hydraulics import G, RHO_W
from .piping import K_U, Pipe, PipeFlow
from .stability_table import StabilityTable

GAMMA_W = RHO_W * G
C_MIN = 0.25          # smallest C/b_p in the table: thinner cover = end lip (not checked)


@dataclass
class Soil:
    c_u0: float           # undrained strength at the surface [Pa]
    rho: float            # increase of c_u with depth [Pa/m]
    gamma_sat: float      # [N/m3]
    gamma_moist: float    # [N/m3]


@dataclass
class RoofCheck:
    x: list               # section positions
    C: list               # cover above the crown
    net: list             # sigma_s - p_s
    M_c: list             # collapse margin [Pa] (-inf where no stable state)
    M_b: list             # blow-out margin [Pa]
    min_M_c: float
    x_star: float         # section of the smallest collapse margin (nan if no section checked)
    min_M_b: float
    x_star_b: float
    lips: tuple           # (upstream lip length, downstream lip length) not checked
    no_stable: list = field(default_factory=list)   # (x, statuses)
    FS_A: float = math.nan     # mechanism A, comparison only (nan when D_A <= 0)
    M_A: float = math.nan      # R_A - D_A [N/m]
    M_B: float = math.nan      # mechanism B margin 2 c_u A_r - 1/2 gamma_w (z_s - z_cr)^2 b_p [N/m]


def soffit_pressure(xi: float, z_s: float, z_cr: float, fl: PipeFlow, Ku: float = K_U) -> float:
    """(5.8): p_s = gamma_w max(z_s - (1 + K_u + f xi/(4R)) U^2/2g - z_cr, 0) when full, else 0."""
    if fl.w == 0 or fl.Q <= 0.0:
        return 0.0
    head = z_s - (1.0 + Ku + fl.f * xi / (4.0 * fl.R)) * fl.U ** 2 / (2.0 * G)
    return GAMMA_W * max(head - z_cr, 0.0)


def surface_load(dam: Dam, x: float, z_s: float) -> float:
    """sigma_s: hydrostatic load of the reservoir on the upstream face (x <= x_c0), zero on the crest and
    the downstream face (5.5b; the same piecewise boundary condition as p_top in 5.6). Overflow on the
    crest is a flowing film, not standing water, and is not counted."""
    if x > dam.x_c0:
        return 0.0
    return GAMMA_W * max(z_s - dam.z_dam(x), 0.0)


def gamma_bar(C: float, z_cr: float, z_ph: float, soil: Soil) -> float:
    """(5.24): cover-weighted unit weight, saturated below the phreatic level, moist above."""
    t_s = min(max(z_ph - z_cr, 0.0), C)
    return (soil.gamma_sat * t_s + soil.gamma_moist * (C - t_s)) / C


def sections(x0: float, x1: float, dx: float):
    """Section positions from x0 to x1 inclusive, spacing at most dx."""
    n = max(1, int(math.ceil((x1 - x0) / dx - 1e-12)))
    return [x0 + (x1 - x0) * i / n for i in range(n + 1)]


def check(dam: Dam, pipe: Pipe, x_in: float, x_o: float, z_s: float, fl: PipeFlow, soil: Soil,
          table: StabilityTable, bound: str = "mid", dx: float | None = None,
          z_head: float | None = None, ab: bool = True) -> RoofCheck:
    """Evaluate (5.15) along the pipe from the inlet x_in to the outlet x_o. bound: 'lo' | 'mid' | 'hi'.
    z_s is the reservoir level (surface load, phreatic level). z_head is the energy level at the reach
    inlet for the soffit pressure (5.8): the reservoir for a pipe fed by it (default), the crater level
    for the downstream reach (5.7a.4). ab=False skips the mechanism A/B comparison."""
    z_head = z_s if z_head is None else z_head
    b, D, z_cr = pipe.b, pipe.D, pipe.z_cr
    dx = dx or 0.5 * b
    xs, Cs, nets, Mc, Mb, nst = [], [], [], [], [], []
    lip_up = lip_dn = 0.0
    checked = [x for x in sections(x_in, x_o, dx)]
    full = fl.w == 1 and fl.Q > 0.0
    for x in checked:
        C = dam.z_dam(x) - z_cr
        if C < C_MIN * b:                                    # end lip, outside the table
            if x < 0.5 * (x_in + x_o):
                lip_up = max(lip_up, x - x_in)
            else:
                lip_dn = max(lip_dn, x_o - x)
            continue
        xs.append(x); Cs.append(C)
        nets.append(surface_load(dam, x, z_s) - soffit_pressure(x - x_in, z_head, z_cr, fl))
    if xs:
        Ca = np.asarray(Cs)
        g_b = np.array([gamma_bar(C, z_cr, z_s, soil) for C in Cs]) * b / soil.c_u0
        args = (Ca / b, D / b, g_b, soil.rho * b / soil.c_u0)
        gw_b = GAMMA_W * b / soil.c_u0 if full else 0.0
        rc_ = table.query_many(*args, gw_b=gw_b, full=full, mechanism="collapse")
        rb_ = table.query_many(*args, gw_b=gw_b, full=full, mechanism="blowout")
        net = np.asarray(nets)
        mc = soil.c_u0 * rc_[bound] - net
        mb = net - soil.c_u0 * rb_[bound]
        uns = rc_["unstable"] | rb_["unstable"]
        mc[uns] = -np.inf
        mb[uns] = np.nan
        Mc, Mb = mc.tolist(), mb.tolist()
        for k in np.nonzero(uns)[0]:
            nst.append((xs[k], tuple(sorted(rc_["statuses"][k] | rb_["statuses"][k]))))
    rc = RoofCheck(xs, Cs, nets, Mc, Mb, math.inf, math.nan, math.inf, math.nan, (lip_up, lip_dn), nst)
    if Mc:
        i = min(range(len(Mc)), key=lambda k: Mc[k])
        rc.min_M_c, rc.x_star = Mc[i], xs[i]
        finite = [k for k in range(len(Mb)) if not math.isnan(Mb[k])]
        if finite:
            j = min(finite, key=lambda k: Mb[k])
            rc.min_M_b, rc.x_star_b = Mb[j], xs[j]
    if ab:
        _mechanisms_ab(rc, dam, pipe, x_in, x_o, z_s, fl, soil)
    return rc


def _area_above(dam: Dam, level: float, xa: float, xb: float) -> float:
    pts = sorted({xa, xb} | {x for x in (dam.x_c0, dam.x_c1) if xa < x < xb})
    return integrate_positive(lambda x: dam.z_dam(x) - level, pts)


def _mechanisms_ab(rc: RoofCheck, dam: Dam, pipe: Pipe, x_in: float, x_o: float, z_s: float,
                   fl: PipeFlow, soil: Soil) -> None:
    """(5.9) fall-in of the rigid roof block (comparison) and (5.10) horizontal push-out."""
    b, z_cr = pipe.b, pipe.z_cr
    xa = dam.x_up(z_cr)
    A_r = _area_above(dam, z_cr, xa, x_o)
    if A_r <= 0.0:
        return
    A_dry = _area_above(dam, max(z_s, z_cr), xa, x_o)            # roof above the phreatic level
    W = soil.gamma_sat * (A_r - A_dry) + soil.gamma_moist * A_dry
    z_top = min(z_s, dam.H)
    A_w = 0.0
    if z_top > z_cr:                                             # water over the upstream face above the roof
        x1 = dam.x_up(z_top)
        A_w = integrate_positive(lambda x: z_s - dam.z_dam(x), [xa, x1])
    ps_int = 0.0                                                 # integral of p_s along the pipe (exact)
    if fl.w == 1 and fl.Q > 0.0:
        head = lambda x: z_s - (1.0 + K_U + fl.f * (x - x_in) / (4.0 * fl.R)) * fl.U ** 2 / (2.0 * G) - z_cr
        ps_int = GAMMA_W * integrate_positive(head, [x_in, x_o])
    D_A = b * W + GAMMA_W * b * A_w - b * ps_int
    R_A = 2.0 * soil.c_u0 * A_r
    rc.M_A = R_A - D_A
    rc.FS_A = R_A / D_A if D_A > 0.0 else math.nan
    rc.M_B = 2.0 * soil.c_u0 * A_r - 0.5 * GAMMA_W * max(z_s - z_cr, 0.0) ** 2 * b


def failing_reaches(rc: RoofCheck, tol: float = 0.0):
    """Contiguous reaches of checked sections with M_c <= 0, as (x_first, x_last, touches_upstream_end,
    touches_downstream_end). 'Touches' means the reach starts at the first (or ends at the last) checked
    section, i.e. it is joined to an end lip. Used by the event logic (stage 3) to tell an interior
    collapse from failure at a pipe end."""
    out, start = [], None
    n = len(rc.x)
    for k in range(n + 1):
        bad = k < n and rc.M_c[k] <= -tol
        if bad and start is None:
            start = k
        if not bad and start is not None:
            out.append((rc.x[start], rc.x[k - 1], start == 0, k - 1 == n - 1))
            start = None
    return out


def crossing_fraction(m0: float, m1: float) -> float:
    """Fraction of a step at which a margin crossing m0 > 0 -> m1 <= 0 occurs (linear, 5.5)."""
    if m1 > 0.0 or m0 <= 0.0:
        raise ValueError("no crossing in this step")
    if math.isinf(m1):
        return 1.0
    return m0 / (m0 - m1)
