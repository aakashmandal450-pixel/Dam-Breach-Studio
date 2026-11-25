"""Piping stage 3a: classification of roof failures and end retreat (Theory Part 5, section 5.5b,
"End failures", decided 2026-11-25; docs/theory/05_piping.md).

Three outcomes are kept separate:
  upstream-end failure    a failing reach joined to the upstream end lip: the inlet moves downstream
  downstream-end failure  a failing reach joined to the downstream end lip: the outlet moves upstream
  interior failure        a failing reach joined to neither end: starts the crater (section 5.7a)

Retreat distance comes from the failed reach itself: the new end is where the collapse margin crosses
zero between the last failing and the first stable section (linear in x, as for x*). If that last
failing section has no stable state (margin -inf), the new end is that section (no interpolation into
an unstable region). The end never moves past the failed geometry.

Volumes: the roof over the retreated reach (lip included) is the dam section above the crown between
the old and new end, times b_p. First-version assumption: it is carried out by the flow at once
(upstream: through the pipe; downstream: by the outlet jet) and recorded as exported end debris,
separately for the two ends. It is not a crater, and it is never counted again: a later retreat starts
from the new end. The opened slot holds reservoir water (upstream) or drains (downstream); like the pipe
void itself, its water is not stored in the quasi-steady model.

Mechanism C (uplift, 5.6) also moves the outlet but is a separate rule with its own budget term.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .geometry import Dam, integrate_positive
from .roof import RoofCheck, failing_reaches


@dataclass(frozen=True)
class Failures:
    x_up: float | None        # new inlet position after an upstream-end failure (None: no such failure)
    x_dn: float | None        # new outlet position after a downstream-end failure
    interior: list            # interior failing reaches (x_first, x_last)
    whole: bool               # every checked section failed: the roof is gone end to end


def _zero(x0, m0, x1, m1):
    """x where the margin crosses zero between a failing (m0 <= 0) and a stable (m1 > 0) section."""
    if math.isinf(m0):
        return x0
    return x0 + (x1 - x0) * (-m0) / (m1 - m0)


def classify(rc: RoofCheck) -> Failures:
    """Split the failing reaches of one roof check into upstream-end, downstream-end and interior."""
    x_up = x_dn = None
    interior = []
    reaches = failing_reaches(rc)
    n = len(rc.x)
    whole = n > 0 and len(reaches) == 1 and reaches[0][2] and reaches[0][3]
    if whole:
        return Failures(None, None, [], True)
    for xa, xb, up, dn in reaches:
        if up:
            k = rc.x.index(xb)                       # last failing section; k + 1 is stable
            x_up = _zero(rc.x[k], rc.M_c[k], rc.x[k + 1], rc.M_c[k + 1])
        elif dn:
            k = rc.x.index(xa)                       # first failing section; k - 1 is stable
            x_dn = _zero(rc.x[k], rc.M_c[k], rc.x[k - 1], rc.M_c[k - 1])
        else:
            interior.append((xa, xb))
    return Failures(x_up, x_dn, interior, False)


def roof_area(dam: Dam, z_cr: float, xa: float, xb: float) -> float:
    """Longitudinal area of the dam section above the crown between xa and xb (exact, piecewise linear)."""
    if xb <= xa:
        return 0.0
    pts = sorted({xa, xb} | {x for x in (dam.x_c0, dam.x_c1) if xa < x < xb})
    return integrate_positive(lambda x: dam.z_dam(x) - z_cr, pts)


@dataclass(frozen=True)
class Retreat:
    x_in: float
    x_o: float
    V_up: float          # bulk roof volume removed at the upstream end in this event [m3]
    V_dn: float          # bulk roof volume removed at the downstream end in this event [m3]


def retreat(dam: Dam, b: float, z_cr: float, x_in: float, x_o: float, f: Failures) -> Retreat:
    """Apply the end failures of one pass. The interior is not touched here (crater, 5.7a)."""
    new_in, new_o = x_in, x_o
    V_up = V_dn = 0.0
    if f.x_up is not None:
        new_in = min(max(f.x_up, x_in), x_o)
        V_up = b * roof_area(dam, z_cr, x_in, new_in)
    if f.x_dn is not None:
        new_o = max(min(f.x_dn, x_o), new_in)
        V_dn = b * roof_area(dam, z_cr, new_o, x_o)
    return Retreat(new_in, new_o, V_up, V_dn)
