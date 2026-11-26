"""Piping: exit headcut at the pipe outlet (Theory Part 5, section 5.6, optional, off by default;
implementation choices in draft 5.10). Uses the Part 4 machinery (headcut.py, Hanson-Robinson-Cook).

The jet leaving the outlet runs down the downstream face in a channel of the pipe width b_p, with unit
discharge q = Q_out / b_p. Geometry (lumped, one headcut):
  brink   at the outlet invert level z_brink = z_inv (the pipe floor), position x_h (starts at the outlet x_o)
  base    z_h, a horizontal channel bed from the headcut face at x_h to where it meets the downstream face
  drop    H_h = z_inv - z_h
Stage 1 (surface erosion): z_h falls at the face-flow erosion rate E_r (Manning normal flow on the face
slope 1/z_d, Part 4 (4.1)); the brink does not move.
Stage 2 (plunging, H_h > d_c, (4.2), no tailwater): the base deepens at the rate of max(tau_face_flow,
tau_hf) (4.3)-(4.7) and the face advances upstream at dX/dt of (4.9), capped at the 0.5H:1V surface rate.
When the brink passes the outlet (x_h < x_o), the outlet moves with it, x_o = x_h, and the pipe shortens.
The roof over the reach the brink has passed is removed with it (bulk volume recorded as V_hc_roof);
the soil below the invert is the headcut channel (V_hc). Both are carried away by the flow (exported),
recorded separately from all other mechanisms. The Robinson/Hanson relations were derived for a free
overfall with critical depth at the brink; a pipe jet leaves faster than critical, so this is an
approximation to be tested (5.6). Cohesive soils only.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from . import headcut as hc
from . import hydraulics as hy
from . import sediment as sd
from .ends import roof_area
from .geometry import Dam, integrate_positive


@dataclass(frozen=True)
class ExitHeadcut:
    x_h: float            # brink position (headcut face)
    z_h: float            # headcut base elevation
    stage: int = 1        # 1 surface erosion, 2 plunging
    vol: float = 0.0      # bulk volume of the headcut channel below the invert (cumulative, exported)
    V_roof: float = 0.0   # bulk roof removed where the brink passed the outlet (cumulative, exported)


def channel_area(dam: Dam, z_brink: float, x_h: float, z_h: float) -> float:
    """Longitudinal area of the channel below the brink level: from x_h to the face, between
    min(z_dam, z_brink) and z_h (exact for the piecewise-linear profile)."""
    x_b = dam.x_down(z_h)
    if x_b <= x_h:
        return 0.0
    cap = lambda x: min(dam.z_dam(x), z_brink)
    brk = [dam.x_down(z_brink), dam.x_c0, dam.x_c1]
    pts = sorted({x_h, x_b} | {x for x in brk if x_h < x < x_b})
    return integrate_positive(lambda x: cap(x) - z_h, pts)


def _rect_flow(Q: float, b: float, S0: float, n: float):
    y = hy.normal_depth(Q, b, 0.0, n, S0)
    A = b * y
    return y, hy.manning_shear(Q, A, A / (b + 2.0 * y), n)


def step(h: ExitHeadcut, dam: Dam, Q: float, b: float, z_inv: float, z_cr: float, x_o: float, dt: float,
         kd: float, tau_c: float, c_u: float, gamma_t: float, n: float, C_h: float = 1.0):
    """Advance the exit headcut by dt with outlet discharge Q. Returns (new state, new outlet x_o)."""
    if Q <= 0.0 or b <= 0.0 or dt <= 0.0:
        return h, x_o
    dc = hc.critical_depth_unit(Q / b)
    Hh = max(z_inv - h.z_h, 0.0)
    _, tau_s = _rect_flow(Q, b, 1.0 / dam.zd, n)
    Er = sd.cohesive_rate(tau_s, tau_c, kd)
    _, tau_cap = _rect_flow(Q, b, 2.0, n)
    Er_cap = sd.cohesive_rate(tau_cap, tau_c, kd)
    stage, dX = h.stage, 0.0
    if Hh > dc:                                          # plunging (4.2), no tailwater
        stage = 2
        tau_hf = hc.face_stress(Hh, dc, dc)
        dz = sd.cohesive_rate(max(tau_s, tau_hf), tau_c, kd) * dt
        dX = C_h * hc.advance_rate(Hh, dc, dc, c_u, gamma_t, kd, tau_c, Er_cap) * dt
    else:
        dz = Er * dt
    z_h = max(h.z_h - dz, 0.0)
    x_h = h.x_h - dX
    V_roof = h.V_roof
    if x_h < x_o:                                        # the brink passes the outlet: the outlet moves with it
        V_roof += b * roof_area(dam, z_cr, x_h, x_o)
        x_o = x_h
    vol = b * channel_area(dam, z_inv, x_h, z_h)
    return ExitHeadcut(x_h, z_h, stage, max(vol, h.vol), V_roof), x_o
