"""Piping: widening of the pipe exit at the downstream face, mechanism H1-a (Theory Part 5, note H-1,
reviewed 2026-11-26: approved for verification and one controlled coupled test; optional, off by default).

The pipe inside the dam stays a uniform rectangle b x D (5.4). One state variable, the exit width
B_e >= b, is the width of the open notch at the downstream face: the reach from the crown daylight
x_d = x_t - m z_cr down the face to where the invert reaches it, x_i = x_t - m z_inv. The notch carries
the outlet discharge as a free-surface channel of width B_e on the face slope, Manning normal flow
(the 5.6 stage-1 channel, same n; a stated approximation: the pipe-to-notch transition is not resolved).
Its two side walls retreat at the bed-erosion rate (Part 3 / DL Breach convention, no side-wall factor):

    dB_e/dt = 2 k_d max(tau_e - tau_c, 0)                                             (H.1)

The wall profile is the face above the notch floor (the pipe invert, horizontal) over x_d..x_i, a
triangle of area A_w = m D^2 / 2 per wall-width, so widening by dB removes the bulk volume A_w dB
(both walls together). Only widening beyond the pipe width counts here; the pipe walls themselves are
eroded and booked by 5.4. Not represented: H1-b (roof-lip erosion, inactive in the first
implementation), H1-c (roof failure over the wider span, a separate second experiment).
"""
from __future__ import annotations

from . import hydraulics as hy
from . import sediment as sd


def notch_flow(Q: float, B: float, m: float, n: float):
    """(depth, shear) of the outlet discharge Q in the notch of width B on the face slope 1/m."""
    if Q <= 0.0 or B <= 0.0:
        return 0.0, 0.0
    y = hy.normal_depth(Q, B, 0.0, n, 1.0 / m)
    A = B * y
    return y, hy.manning_shear(Q, A, A / (B + 2.0 * y), n)


def rate(Q: float, B: float, m: float, n: float, kd: float, tau_c: float) -> float:
    """(H.1): dB_e/dt [m/s]; zero below the critical shear (review correction A)."""
    _, tau = notch_flow(Q, B, m, n)
    return 2.0 * sd.cohesive_rate(tau, tau_c, kd)


def wall_area(D: float, m: float) -> float:
    """Profile area of one notch wall: the face above the pipe invert between the crown and invert
    daylight points (triangle, height D, horizontal length m D)."""
    return 0.5 * m * D * D


def step(B_e: float, b_new: float, D: float, Q: float, m: float, n: float, kd: float, tau_c: float, dt: float):
    """Advance B_e by dt (explicit: rate at the start of the step, at the old width). The notch walls
    retreat at the notch rate from where they were; where the pipe (5.4) has grown past them, the pipe
    width governs and that soil is already booked as pipe erosion. Returns (B_new, bulk volume removed
    beyond the pipe width in this step)."""
    B_adv = B_e + rate(Q, B_e, m, n, kd, tau_c) * dt
    B1 = max(B_adv, b_new)
    dV = wall_area(D, m) * max(B_adv - max(B_e, b_new), 0.0)
    return B1, dV
