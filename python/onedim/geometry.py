"""Cross-section geometry for the distributed 1-D engine (Part 6 §6.2.3, §6.5.2).

A section is a piecewise-linear width function sigma(eta) above a bottom elevation z, written as
nodes (y_k, w_k) with y the height above the bottom (y_0 = 0, non-decreasing). Consecutive nodes
with the same y are a jump in width (a roof or a floor step, for example the conduit crown where
the width drops from b_p to the slot width T_s). Widths are right-continuous: at a jump the value
above applies from that level up. Above the last node the width stays constant (the slot, or the
vertical stream tube of (6.2)).

Each segment carries a friction flag: 1 if its two side walls are friction surfaces (perimeter),
0 if not (slot walls, stream tube above the ground). A zero-length segment (a jump) with flag 1
contributes its horizontal width change |dw| to the perimeter once the water is above it (the
wetted roof of a full conduit, (6.3)). The bottom width always counts once the cell is wet.
Above the last node the walls are frictionless.

Sections are symmetric: each side wall moves out by dw/2 per unit height.

SectionSet packs N sections into padded arrays so that the section functions of (6.1) are
evaluated for all cells at once:
    area A(eta), top width T(eta), first moment I1(eta), wetted perimeter P(eta),
    and the inverse eta(A).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

_PAD_STEP = 1.0e6          # height of padding segments above the last node (never reached)


@dataclass
class Section:
    z: float                                   # bottom elevation (lowest wetted point)
    y: list                                    # node heights above z, y[0] = 0, non-decreasing
    w: list                                    # node widths (>= 0)
    fr: list = field(default_factory=list)     # friction flag per segment, len = len(y) - 1
    kind: str = "open"                         # "open", "conduit" or "interface"

    def __post_init__(self):
        self.y = [float(v) for v in self.y]
        self.w = [float(v) for v in self.w]
        if not self.fr:
            self.fr = [1] * (len(self.y) - 1)
        if len(self.y) != len(self.w) or len(self.fr) != len(self.y) - 1:
            raise ValueError("section: y, w, fr lengths inconsistent")
        if self.y[0] != 0.0:
            raise ValueError("section: y[0] must be 0")
        if any(b < a for a, b in zip(self.y, self.y[1:])):
            raise ValueError("section: node heights must be non-decreasing")
        if any(v < 0 for v in self.w):
            raise ValueError("section: negative width")

    # -- scalar width evaluation, used to build intersections -------------------------------
    def _seg_width(self, k, yy):
        y0, y1, w0, w1 = self.y[k], self.y[k + 1], self.w[k], self.w[k + 1]
        if y1 == y0:
            return w1
        return w0 + (w1 - w0) * (yy - y0) / (y1 - y0)

    def _snap(self, yy):
        for v in self.y:
            if abs(yy - v) <= 1e-12 * (1.0 + abs(v)):
                return v
        return yy

    def width_right(self, e):
        """sigma just above absolute elevation e (right limit)."""
        yy = self._snap(e - self.z)
        if yy < 0:
            return 0.0
        for k in range(len(self.y) - 1):
            if self.y[k] <= yy < self.y[k + 1]:
                return self._seg_width(k, yy)
        return self.w[-1]

    def width_left(self, e):
        """sigma just below absolute elevation e (left limit)."""
        yy = self._snap(e - self.z)
        if yy <= 0:
            return 0.0
        for k in range(len(self.y) - 1):
            if self.y[k] < yy <= self.y[k + 1] and self.y[k + 1] > self.y[k]:
                return self._seg_width(k, yy)
        return self.w[-1]

    def breakpoints(self):
        return [self.z + v for v in self.y]


# ---------------------------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------------------------
def rectangle(z, b, height=1.0e4):
    """Open rectangular channel; walls are friction surfaces up to `height`."""
    return Section(z, [0.0, height], [b, b], [1])


def trapezoid(z, b, cot_beta, height, n_loc=2):
    """Open trapezoid (6.2): bottom width b, walls at cot_beta (H:V), n_loc sloping walls, up to
    `height` (the dam surface); above that the vertical stream tube (frictionless)."""
    return Section(z, [0.0, height], [b, b + n_loc * cot_beta * height], [1])


def conduit(z_inv, b, a, a_s, g=9.81, slot_height=1.0e3):
    """Rectangular conduit b x a with a Preissmann slot of width T_s = g b a / a_s^2 (6.9)."""
    ts = g * b * a / a_s ** 2
    return Section(z_inv, [0.0, a, a, a + slot_height], [b, b, ts, ts], [1, 1, 0], kind="conduit")


def intersection(sa: Section, sb: Section) -> Section:
    """Interface section (6.13): sigma = min(sigma_a, sigma_b) above z = max(z_a, z_b).

    Exact for piecewise-linear widths: the merged breakpoints are split again where the two
    linear pieces cross, and jumps are kept as zero-length segments."""
    z = max(sa.z, sb.z)
    cand = sorted({e for e in sa.breakpoints() + sb.breakpoints() if e > z} | {z})
    top = cand[-1] + 1.0
    cand.append(top)
    nodes = []                                   # (e, w)

    def push(e, w):
        if nodes and nodes[-1][0] == e and abs(nodes[-1][1] - w) <= 1e-15 * max(1.0, w):
            return
        nodes.append((e, w))

    for a, b in zip(cand[:-1], cand[1:]):
        da = sa.width_right(a) - sb.width_right(a)
        db = sa.width_left(b) - sb.width_left(b)
        va = min(sa.width_right(a), sb.width_right(a))
        push(a, va)
        if da * db < 0:                         # the two linear pieces cross inside (a, b)
            ec = a + (b - a) * da / (da - db)
            push(ec, min(sa.width_right(ec), sb.width_right(ec)))
        push(b, min(sa.width_left(b), sb.width_left(b)))
    ys = [e - z for e, _ in nodes]
    ws = [w for _, w in nodes]
    # drop the artificial top node; the last width extends upward
    if len(ys) > 2 and ys[-1] == ys[-2] + 1.0 and ws[-1] == ws[-2]:
        ys, ws = ys[:-1], ws[:-1]
    return Section(z, ys, ws, [0] * (len(ys) - 1), kind="interface")


# ---------------------------------------------------------------------------------------------
# Vectorised section functions
# ---------------------------------------------------------------------------------------------
class SectionSet:
    """N sections packed into padded arrays (N, K) for vectorised evaluation."""

    def __init__(self, sections):
        self.sections = list(sections)
        n = len(self.sections)
        k = max(len(s.y) for s in self.sections) + 1      # at least one padding segment
        Y = np.zeros((n, k)); W = np.zeros((n, k)); F = np.zeros((n, k - 1))
        for i, s in enumerate(self.sections):
            m = len(s.y)
            Y[i, :m] = s.y; W[i, :m] = s.w; F[i, :m - 1] = s.fr
            for j in range(m, k):                       # padding: constant width, frictionless
                Y[i, j] = s.y[-1] + _PAD_STEP * (j - m + 1)
                W[i, j] = s.w[-1]
        self.z = np.array([s.z for s in self.sections])
        self.Y, self.W, self.F = Y, W, F
        self.y0, self.y1 = Y[:, :-1], Y[:, 1:]
        self.w0, self.w1 = W[:, :-1], W[:, 1:]
        dy = self.y1 - self.y0
        self.dy = dy
        with np.errstate(divide="ignore", invalid="ignore"):
            self.slope = np.where(dy > 0, (self.w1 - self.w0) / np.where(dy > 0, dy, 1.0), 0.0)
        # cumulative area at the nodes, for the inverse
        seg_area = dy * (self.w0 + self.w1) / 2.0
        self.cum_area = np.concatenate([np.zeros((n, 1)), np.cumsum(seg_area, axis=1)], axis=1)
        # wall length factor per unit height (two symmetric walls), and jump perimeters
        self.wall = 2.0 * np.sqrt(1.0 + (self.slope / 2.0) ** 2) * self.F
        self.jump = np.where(dy == 0, np.abs(self.w1 - self.w0) * self.F, 0.0)
        self.bottom_width = W[:, 0]

    def __len__(self):
        return len(self.sections)

    def subset(self, idx):
        return SectionSet([self.sections[i] for i in idx])

    # internal: per-segment clipped height above each segment start
    def _clip(self, h, rows=None):
        y0 = self.y0 if rows is None else self.y0[rows]
        y1 = self.y1 if rows is None else self.y1[rows]
        hh = np.asarray(h)[:, None]
        return np.clip(hh, y0, y1) - y0               # height used inside each segment, >= 0

    def _rows(self, rows):
        if rows is None:
            return self.w0, self.slope, self.y0
        return self.w0[rows], self.slope[rows], self.y0[rows]

    def area_h(self, h, rows=None):
        """A as a function of depth h above the bottom (h <= 0 gives 0)."""
        d = self._clip(h, rows)
        w0, s, _ = self._rows(rows)
        return np.sum(d * (w0 + 0.5 * s * d), axis=1)

    def i1_h(self, h, rows=None):
        """I1 = int_0^h (h - y) sigma(y) dy, computed relative to the bottom (6.1)."""
        h = np.asarray(h, dtype=float)
        d = self._clip(h, rows)
        w0, s, y0 = self._rows(rows)
        # per segment: int_{y0}^{y0+d} (h - y)(w0 + s (y - y0)) dy, with u = y - y0, r = h - y0
        r = h[:, None] - y0
        seg = w0 * (r * d - 0.5 * d * d) + s * (0.5 * r * d * d - d ** 3 / 3.0)
        return np.sum(np.where(d > 0, seg, 0.0), axis=1)

    def width_h(self, h, rows=None):
        """Top width T at depth h (right-continuous)."""
        h = np.asarray(h, dtype=float)
        y0 = self.y0 if rows is None else self.y0[rows]
        y1 = self.y1 if rows is None else self.y1[rows]
        w0, s, _ = self._rows(rows)
        inside = (h[:, None] >= y0) & (h[:, None] < y1)
        val = np.where(inside, w0 + s * (h[:, None] - y0), 0.0)
        return np.sum(val, axis=1)

    def perimeter_h(self, h, rows=None):
        """Wetted perimeter P(h): bottom + frictional side walls + wetted jumps (roof)."""
        h = np.asarray(h, dtype=float)
        d = self._clip(h, rows)
        wall = self.wall if rows is None else self.wall[rows]
        jump = self.jump if rows is None else self.jump[rows]
        y0 = self.y0 if rows is None else self.y0[rows]
        bw = self.bottom_width if rows is None else self.bottom_width[rows]
        p = np.sum(d * wall, axis=1) + np.sum(np.where(h[:, None] > y0, jump, 0.0), axis=1)
        return np.where(h > 0, p + bw, 0.0)

    def depth_from_area(self, A, rows=None):
        """Inverse of area_h: depth h with A(h) = A (exact, segment by segment)."""
        A = np.asarray(A, dtype=float)
        cum = self.cum_area if rows is None else self.cum_area[rows]
        w0, s, y0 = self._rows(rows)
        kseg = np.sum(cum[:, 1:-1] <= A[:, None], axis=1)       # segment index containing A
        kseg = np.minimum(kseg, w0.shape[1] - 1)
        ii = np.arange(len(A))
        rem = np.maximum(A - cum[ii, kseg], 0.0)
        wk, sk = w0[ii, kseg], s[ii, kseg]
        root = np.sqrt(np.maximum(wk * wk + 2.0 * sk * rem, 0.0))
        denom = wk + root
        with np.errstate(divide="ignore", invalid="ignore"):
            d = np.where(denom > 0, 2.0 * rem / np.where(denom > 0, denom, 1.0), 0.0)
        return np.where(A > 0, y0[ii, kseg] + d, 0.0)

    # stage-based wrappers
    def area(self, eta, rows=None):
        z = self.z if rows is None else self.z[rows]
        return self.area_h(np.maximum(np.asarray(eta) - z, 0.0), rows)

    def i1(self, eta, rows=None):
        z = self.z if rows is None else self.z[rows]
        return self.i1_h(np.maximum(np.asarray(eta) - z, 0.0), rows)

    def eta_from_area(self, A, rows=None):
        z = self.z if rows is None else self.z[rows]
        return z + self.depth_from_area(A, rows)

    _GL = {}

    def phi_h(self, h, rows=None, npts=24):
        """Riemann function Phi = int sqrt(g T / A) d(eta) (6.8), by Gauss-Legendre in
        t with eta = z + h t^2 (removes the square-root singularity at the bottom)."""
        g = 9.81
        h = np.asarray(h, dtype=float)
        if npts not in SectionSet._GL:
            t, wq = np.polynomial.legendre.leggauss(npts)
            SectionSet._GL[npts] = (0.5 * (t + 1.0), 0.5 * wq)
        t, wq = SectionSet._GL[npts]
        n = h.shape[0]
        hk = (h[:, None] * (t * t)[None, :]).ravel()
        rr = None
        if rows is not None:
            rr = np.repeat(np.asarray(rows), npts)
        elif n != len(self.z):
            raise ValueError("phi_h needs rows when h is not one value per section")
        else:
            rr = np.repeat(np.arange(n), npts)
        Ak = self.area_h(hk, rr).reshape(n, npts)
        Tk = self.width_h(hk, rr).reshape(n, npts)
        with np.errstate(divide="ignore", invalid="ignore"):
            f = np.where(Ak > 0, np.sqrt(g * Tk / np.where(Ak > 0, Ak, 1.0)), 0.0)
        return np.sum(wq[None, :] * f * 2.0 * h[:, None] * t[None, :], axis=1)
