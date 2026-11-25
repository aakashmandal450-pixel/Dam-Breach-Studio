"""Piping stage 1: pipe hydraulics and wall erosion (Theory Part 5, sections 5.2-5.4,
docs/theory/05_piping.md). Scalar, pure functions plus a small state record.

The pipe is a horizontal rectangle, width b, height D (= a_p), invert z_inv above the dam base,
length L. HW is the headwater above the invert, h_t the tailwater above the invert.

  inlet control (5.2)   Q_i: critical-depth entrance for HW <= 1.5 D, pressurised entrance above
  outlet control (5.3)  Q_o: energy equation reservoir -> outlet with entrance, friction and exit losses
  discharge (5.4)       Q_b = min(Q_i, Q_o)
  wall shear (5.5)      tau = rho f U^2 / 8 (friction part of the loss only)
  erosion (5.6)-(5.7)   eps = k_d (tau - tau_c); floor down, sides out, roof up only when wetted

Rectangle update (draft 5.4 correction of (5.7), for review): the sides of a part-full pipe are wetted
only to depth y, but the section is kept rectangular. The side retreat is therefore spread over the full
height so that the area added in a step equals the eroded volume per unit length exactly:
    d(b D) = (wetted erodible perimeter) * eps * dt,
which gives db/dt = 2 eps y/D (= 2 eps of (5.7) when full). The floor stops at the dam base (z = 0);
once it is there it no longer erodes and is not counted in the eroded perimeter.
Cohesive (detachment-limited) erosion only; the non-cohesive branch of 5.4 is a later stage.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .hydraulics import G, RHO_W

K_U = 0.05     # entrance loss (Part 1, 1.4)
K_D = 1.0      # exit velocity head (Part 1, 1.4)
C_INLET = math.sqrt(2.0 * G) * (2.0 / 3.0) * math.sqrt(1.0 / 3.0)   # 1.705 of (5.2)


@dataclass(frozen=True)
class PipeFlow:
    Q: float          # discharge Q_b [m3/s]
    Q_i: float        # inlet-control discharge
    Q_o: float        # outlet-control discharge
    control: str      # "inlet" | "outlet" | "none"
    w: int            # 1 when the pipe is full (roof wetted), else 0
    y: float          # flow depth used in the section (entrance depth, = D when full) [m]
    A: float
    P: float          # wetted perimeter, roof included when w = 1
    R: float
    f: float          # Darcy friction factor from Manning
    F: float          # f L / (4 R)
    U: float          # mean velocity Q/A


def darcy_f(n: float, R: float) -> float:
    """f = 8 g n^2 / R^(1/3) (Manning expressed as a Darcy factor)."""
    return 8.0 * G * n * n / R ** (1.0 / 3.0)


def inlet_control(HW: float, b: float, D: float, Ku: float = K_U) -> float:
    """(5.2): critical-depth entrance below HW = 1.5 D, full pressurised entrance above."""
    if HW <= 0.0:
        return 0.0
    if HW <= 1.5 * D:
        ye = 2.0 * HW / 3.0
        return b * ye * math.sqrt(2.0 * G * (HW - ye) / (1.0 + Ku))
    return b * D * math.sqrt(2.0 * G * (HW - 0.5 * D) / (1.0 + Ku))


def section(b: float, D: float, HW: float):
    """Entrance depth y_e, full flag w, area, wetted perimeter and hydraulic radius used in (5.3)."""
    if HW > 1.5 * D:
        y, w = D, 1
    else:
        y, w = min(2.0 * HW / 3.0, D), 0
    A = b * y
    P = b + 2.0 * y + w * b
    return y, w, A, P, (A / P if P > 0 else 0.0)


def outlet_control(HW: float, b: float, D: float, L: float, n: float,
                   Ku: float = K_U, Kd: float = K_D, h_t: float = 0.0) -> float:
    """(5.3): Q_o = A sqrt(2g (HW - max(y/2, h_t)) / (Ku + Kd + f L/(4R)))."""
    y, w, A, P, R = section(b, D, HW)
    head = HW - max(0.5 * y, h_t)
    if head <= 0.0 or A <= 0.0:
        return 0.0
    F = darcy_f(n, R) * L / (4.0 * R)
    return A * math.sqrt(2.0 * G * head / (Ku + Kd + F))


def pipe_flow(HW: float, b: float, D: float, L: float, n: float,
              Ku: float = K_U, Kd: float = K_D, h_t: float = 0.0) -> PipeFlow:
    """(5.4): Q_b = min(Q_i, Q_o), with the section quantities needed for the shear (5.5)."""
    y, w, A, P, R = section(b, D, max(HW, 0.0))
    if HW <= 0.0 or A <= 0.0:
        return PipeFlow(0.0, 0.0, 0.0, "none", 0, 0.0, 0.0, b, 0.0, 0.0, 0.0, 0.0)
    f = darcy_f(n, R)
    F = f * L / (4.0 * R)
    Qi = inlet_control(HW, b, D, Ku)
    Qo = outlet_control(HW, b, D, L, n, Ku, Kd, h_t)
    Q = min(Qi, Qo)
    return PipeFlow(Q, Qi, Qo, "inlet" if Qi <= Qo else "outlet", w, y, A, P, R, f, F, Q / A)


def wall_shear(fl: PipeFlow) -> float:
    """(5.5): tau_p = rho f U^2 / 8, from the friction part of the loss only."""
    return RHO_W * fl.f * fl.U ** 2 / 8.0


def erosion_rate(tau: float, kd: float, tau_c: float) -> float:
    """(5.6): eps = k_d (tau - tau_c) for tau > tau_c, else 0. kd in m3/(N s), result in m/s."""
    return kd * (tau - tau_c) if tau > tau_c else 0.0


@dataclass(frozen=True)
class Pipe:
    b: float          # width [m]
    D: float          # height a_p [m]
    z_inv: float      # invert above the dam base [m]
    L: float          # length [m]

    @property
    def z_cr(self) -> float:
        return self.z_inv + self.D


def erode(p: Pipe, eps: float, w: int, y: float, dt: float, z_base: float = 0.0):
    """Advance the pipe walls by one step of length dt at erosion rate eps (5.7, rectangle update above).

    Returns (new pipe, eroded volume [m3]). The eroded volume equals the wetted erodible area times
    eps * dt, and the area change of the rectangle times L equals it to round-off.
    """
    if eps <= 0.0 or dt <= 0.0:
        return p, 0.0
    d = eps * dt
    floor = min(d, max(p.z_inv - z_base, 0.0))      # the floor stops at the base
    roof = d if w else 0.0                          # roof erodes only when wetted
    y = min(max(y, 0.0), p.D)
    # erodible wetted perimeter x eps dt, per unit length; the floor counts only for the part it moves
    dA = p.b * floor + p.b * roof + 2.0 * y * d
    D_new = p.D + floor + roof
    b_new = (p.b * p.D + dA) / D_new                # exact: b_new * D_new - b D = dA
    new = replace(p, b=b_new, D=D_new, z_inv=p.z_inv - floor)
    return new, dA * p.L
