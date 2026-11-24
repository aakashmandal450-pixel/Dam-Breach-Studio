"""Finite element limit analysis (FELA) of openings in undrained (Tresca) clay -- version 2.

Plane strain, symmetric half domain (x >= 0), ground surface horizontal at z = 0, z upward,
tension positive, c_u = 1 (stresses in c_u, lengths in the opening width B or diameter D = 1).

Problems
  * rect   : rectangular opening, width 1, height D, cover C, uniform surcharge sigma_s, sigma_t = 0
  * circle : circular opening, diameter 1, cover C, uniform surcharge sigma_s, sigma_t = 0
  * footing: smooth strip footing of half-width 0.5 on a weightless half-space (Prandtl, N_c = 2 + pi)

Stability number N = (sigma_s - sigma_t)/c_u (Davis et al. 1980; Sloan & Assadi 1992).

Lower bound (static theorem)
  Linear stress triangles; a statically admissible discontinuity on every interior edge (normal and
  shear traction continuous, node by node); equilibrium with self-weight in every element; Tresca
  yield as a second-order cone at every element node (sufficient for a linear field, by convexity).
  Far field (new in v2): the stress field is extended to the infinite half-space analytically. Beyond
  the side boundary x = X the extension is sigma_zz = gam*z - s_ext, sigma_xz = 0, sigma_xx = g1(z);
  below the bottom z = -Z it is sigma_zz = gam*z - s_ext + f(x), sigma_xz = 0,
  sigma_xx = gam*z - s_ext + k. Both satisfy equilibrium exactly and stay within yield to infinity if
      side  : sigma_xz = 0,  |sigma_xx - (gam*z - s_ext)| <= 2
      bottom: sigma_xz = 0,  k - 2 <= sigma_zz + gam*Z + s_ext <= k + 2,  |k| <= 2
  (f = 0 for x > X so that the two extensions match on z = -Z). Imposed at the boundary nodes of the
  mesh, these conditions make the lower bound rigorous for the infinite domain.
  (v1 left the far boundaries traction-free, which does not guarantee an admissible extension.)

Upper bound (kinematic theorem)
  Linear velocity triangles on a "crossed" mesh (each quadrilateral split by its diagonals into four
  triangles), which does not lock under incompressibility; no velocity discontinuities; velocity
  zero on the far boundaries (so the field extends by zero and the bound is rigorous). Minimise
  internal dissipation minus the power of gravity for unit downward flux through the loaded surface.

Audit (post-solution, independent of the optimiser): equilibrium residual, traction jumps, boundary
residuals and yield excess of the lower-bound field; incompressibility, boundary residuals and the
recomputed bound of the upper-bound field.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field

import cvxpy as cp
import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp

TOL = 1e-7
DELTA = 1e-5          # lower-bound yield margin (fraction of c_u)


def solve(prob):
    """Clarabel. The lower-bound equality system is rank-deficient (redundant traction rows), which
    makes the interior-point KKT solve unstable near the optimum unless static regularisation is
    raised (1e-6 instead of the 1e-8 default). Rigour does not rest on the optimality gap: the audit
    checks that the returned field is admissible, and its load is then a valid bound."""
    base = dict(max_iter=300, tol_gap_abs=1e-6, tol_gap_rel=1e-6, tol_feas=1e-8)
    for kw in (dict(static_regularization_constant=1e-6),
               dict(static_regularization_constant=1e-7),
               dict(static_regularization_constant=1e-6, equilibrate_enable=False),
               dict(static_regularization_constant=1e-8),
               dict(static_regularization_constant=1e-6, iterative_refinement_max_iter=50,
                    iterative_refinement_stop_ratio=2),
               dict(static_regularization_constant=1e-5, tol_gap_abs=1e-4, tol_gap_rel=1e-4, tol_feas=1e-7)):
        try:
            prob.solve(solver=cp.CLARABEL, **{**base, **kw})
            if prob.status in ("optimal", "optimal_inaccurate"):
                return prob
        except cp.error.SolverError:
            pass
    raise RuntimeError("Clarabel failed at all regularisation levels")


def graded(a, b, h0, hmax, r=1.15, fine_at="a"):
    L = b - a
    if L <= 1e-12:
        return np.array([a])
    steps, h = [], h0
    while sum(steps) < L - 1e-12:
        steps.append(min(h, hmax))
        h *= r
    steps = np.array(steps) * L / sum(steps)
    if fine_at == "b":
        steps = steps[::-1]
    return a + np.concatenate([[0.0], np.cumsum(steps)])


def uniform(a, b, h):
    n = max(1, math.ceil((b - a) / h - 1e-9))
    return np.linspace(a, b, n + 1)


# ----------------------------------------------------------------------------------- meshes
@dataclass
class Mesh:
    P: np.ndarray
    T: np.ndarray
    X: float
    Z: float
    is_opening: callable            # (x, z) -> bool for a boundary point on the opening
    load_xmax: float                # surface loaded for 0 <= x <= load_xmax
    s_ext_is_load: bool             # True: surcharge continues to infinity (tunnel); False: footing
    info: dict = field(default_factory=dict)


class _Builder:
    def __init__(self):
        self.nodes, self.nid, self.tris = [], {}, []

    def node(self, x, z):
        k = (round(x, 9), round(z, 9))
        if k not in self.nid:
            self.nid[k] = len(self.nodes)
            self.nodes.append((float(x), float(z)))
        return self.nid[k]

    def quad(self, p):
        """p: four (x, z) corners in order around the quad; split at the diagonal intersection."""
        p = np.asarray(p, float)
        d1, d2 = p[2] - p[0], p[3] - p[1]
        M = np.array([d1, -d2]).T
        s = np.linalg.solve(M, p[1] - p[0])[0]
        c = p[0] + s * d1
        ids = [self.node(*q) for q in p]
        ic = self.node(*c)
        for k in range(4):
            self.tris.append((ids[k], ids[(k + 1) % 4], ic))

    def finish(self):
        P = np.array(self.nodes)
        T = np.array(self.tris)
        v1, v2 = P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]]
        cw = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0] < 0
        T[cw] = T[cw][:, [0, 2, 1]]
        return P, T


def rect_mesh(C, D, h, ext=3.0):
    X = 0.5 + max(ext * (C + D), 3.0)
    Z = C + D + max(0.5 * ext * (C + D), 2.0)
    xs = np.unique(np.round(np.concatenate([uniform(0.0, 0.5, h), graded(0.5, X, h, 1.0)]), 9))
    zs = np.unique(np.round(np.concatenate([graded(-Z, -C - D, h, 1.0, fine_at="b"), uniform(-C - D, -C, h),
                                            graded(-C, 0.0, h, max(h, min(0.5, C / 6)))]), 9))
    b = _Builder()
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
            if 0.5 * (x0 + x1) < 0.5 and -C - D < 0.5 * (z0 + z1) < -C:
                continue
            b.quad([(x0, z0), (x1, z0), (x1, z1), (x0, z1)])
    P, T = b.finish()
    is_open = lambda x, z: (abs(x - 0.5) < TOL and -C - D - TOL <= z <= -C + TOL) or \
                           (x <= 0.5 + TOL and (abs(z + C) < TOL or abs(z + C + D) < TOL))
    return Mesh(P, T, X, Z, is_open, X, True, dict(kind="rect", C=C, D=D, h=h))


def circle_mesh(C, h, ext=3.0):
    R, D = 0.5, 1.0
    zc = -(C + R)
    a = R + min(0.6 * C, 0.75)                  # half-size of the square box around the hole
    X = a + max(ext * (C + D), 3.0)
    Z = C + D + max(0.5 * ext * (C + D), 2.0)
    n = max(4, math.ceil(a / h))
    xb = np.linspace(0.0, a, n + 1)
    zb = np.linspace(zc - a, zc + a, 2 * n + 1)
    xs = np.unique(np.round(np.concatenate([xb, graded(a, X, a / n, 1.0)]), 9))
    zs = np.unique(np.round(np.concatenate([graded(-Z, zc - a, a / n, 1.0, fine_at="b"), zb,
                                            graded(zc + a, 0.0, a / n, max(a / n, min(0.5, C / 6)))]), 9))
    b = _Builder()
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
            if 0.5 * (x0 + x1) < a and zc - a < 0.5 * (z0 + z1) < zc + a:
                continue
            b.quad([(x0, z0), (x1, z0), (x1, z1), (x0, z1)])
    # half-box perimeter from bottom-centre, anticlockwise about the centre
    per = [(x, zc - a) for x in xb] + [(a, z) for z in zb[1:]] + [(x, zc + a) for x in xb[::-1][1:]]
    per = np.array(per)
    th = np.arctan2(per[:, 1] - zc, per[:, 0])
    circ = np.stack([R * np.cos(th), zc + R * np.sin(th)], 1)
    circ[0] = (0.0, zc - R); circ[-1] = (0.0, zc + R)
    m = max(3, math.ceil((a - R) / (0.8 * h)))
    s = (np.arange(m + 1) / m) ** 1.4               # finer next to the hole
    lay = [circ + sk * (per - circ) for sk in s]
    for k in range(m):
        for i in range(len(per) - 1):
            b.quad([lay[k][i], lay[k][i + 1], lay[k + 1][i + 1], lay[k + 1][i]])
    P, T = b.finish()
    is_open = lambda x, z: abs(math.hypot(x, z - zc) - R) < 1e-6
    return Mesh(P, T, X, Z, is_open, X, True, dict(kind="circle", C=C, D=D, h=h))


def footing_mesh(h, X=6.0, Z=4.0):
    xs = np.unique(np.round(np.concatenate([graded(0.0, 0.5, h, 0.1, fine_at="b"),
                                            graded(0.5, X, h, 0.5)]), 9))
    zs = np.unique(np.round(graded(-Z, 0.0, h, 0.5, fine_at="b"), 9))
    b = _Builder()
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            b.quad([(xs[i], zs[j]), (xs[i + 1], zs[j]), (xs[i + 1], zs[j + 1]), (xs[i], zs[j + 1])])
    P, T = b.finish()
    return Mesh(P, T, X, Z, lambda x, z: False, 0.5, False, dict(kind="footing", h=h))


# ----------------------------------------------------------------------------------- topology
def shape_grads(P, T):
    p0, p1, p2 = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    A2 = (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p2[:, 0] - p0[:, 0]) * (p1[:, 1] - p0[:, 1])
    bx = np.stack([p1[:, 1] - p2[:, 1], p2[:, 1] - p0[:, 1], p0[:, 1] - p1[:, 1]], 1) / A2[:, None]
    cz = np.stack([p2[:, 0] - p1[:, 0], p0[:, 0] - p2[:, 0], p1[:, 0] - p0[:, 0]], 1) / A2[:, None]
    return 0.5 * A2, bx, cz


def edges_of(m: Mesh):
    P, T = m.P, m.T
    edges = {}
    for t, tri in enumerate(T):
        for k in range(3):
            a, b = int(tri[k]), int(tri[(k + 1) % 3])
            edges.setdefault((min(a, b), max(a, b)), []).append(t)
    kinds = {}
    for (a, b), own in edges.items():
        if len(own) == 2:
            kinds[(a, b)] = "interior"; continue
        (xa, za), (xb, zb) = P[a], P[b]
        xm, zm = 0.5 * (xa + xb), 0.5 * (za + zb)
        if abs(za) < TOL and abs(zb) < TOL:
            kinds[(a, b)] = "load" if xm < m.load_xmax else "free"
        elif abs(xa) < TOL and abs(xb) < TOL:
            kinds[(a, b)] = "sym"
        elif abs(xa - m.X) < TOL and abs(xb - m.X) < TOL:
            kinds[(a, b)] = "side"
        elif abs(za + m.Z) < TOL and abs(zb + m.Z) < TOL:
            kinds[(a, b)] = "bottom"
        elif m.is_opening(xa, za) and m.is_opening(xb, zb):
            kinds[(a, b)] = "opening"
        else:
            raise ValueError(f"unclassified boundary edge {P[a]} {P[b]}")
    return edges, kinds


def _unit(P, a, b):
    (xa, za), (xb, zb) = P[a], P[b]
    L = math.hypot(xb - xa, zb - za)
    tx, tz = (xb - xa) / L, (zb - za) / L
    return tz, -tx                                # a unit normal


# ----------------------------------------------------------------------------------- strength and pressure
def strength(rho, z):
    """c_u(z)/c_u0 = 1 + rho*depth, depth = -z (z = 0 at the ground surface); rho = (dc_u/dz) B / c_u0."""
    return 1.0 + rho * np.maximum(-np.asarray(z, float), 0.0)


def outward_normal(P, T, t, a, b):
    """Unit normal of edge (a, b) of triangle t pointing out of the soil (T is counter-clockwise)."""
    tri = list(T[t])
    i, j = tri.index(a), tri.index(b)
    if (i + 1) % 3 != j:
        a, b = b, a
    (xa, za), (xb, zb) = P[a], P[b]
    L = math.hypot(xb - xa, zb - za)
    return (zb - za) / L, -(xb - xa) / L


def no_pressure(x, z):
    return 0.0


def hydrostatic(gw, zw, p0=0.0):
    """Water pressure on the opening walls: p = p0 + gw*max(zw - z, 0).
    Full pipe, crown pressure p0: zw = z_crown.  Part-full, free surface at zw: p0 = 0."""
    return lambda x, z: p0 + gw * max(zw - z, 0.0)


# ----------------------------------------------------------------------------------- lower bound
def lower_bound(m: Mesh, gam: float, rho: float = 0.0, pressure=no_pressure, rigorous_far=True):
    P, T = m.P, m.T
    nt = len(T); N3 = 3 * nt
    A, bx, cz = shape_grads(P, T)
    S = cp.Variable((N3, 3))                      # rows (tri, local node); cols sxx, szz, sxz
    p = cp.Variable()                             # load (surcharge or footing pressure)
    kf = cp.Variable()
    idx = np.arange(N3).reshape(nt, 3)
    rr = np.repeat(np.arange(nt), 3)
    Bx = sp.csr_matrix((bx.ravel(), (rr, idx.ravel())), shape=(nt, N3))
    Cz = sp.csr_matrix((cz.ravel(), (rr, idx.ravel())), shape=(nt, N3))
    cons = [Bx @ S[:, 0] + Cz @ S[:, 2] == 0, Bx @ S[:, 2] + Cz @ S[:, 1] == gam]
    edges, kinds = edges_of(m)
    loc = {(int(T[t, k]), t): 3 * t + k for t in range(nt) for k in range(3)}
    groups = {}                                   # node -> list of (terms, rhs)
    cur = [None]

    def add(terms, value):
        groups.setdefault(cur[0], []).append((terms, value))

    rows = {k: set() for k in ("load", "free", "side", "bottom")}
    for (a, b), own in edges.items():
        kind = kinds[(a, b)]
        if kind == "opening":
            nx, nz = outward_normal(P, T, own[0], a, b)
        else:
            nx, nz = _unit(P, a, b)
        for nd in (a, b):
            cur[0] = nd
            ents = [loc[(nd, t)] for t in own]
            if kind == "interior":
                r1, r2 = ents
                add([(r1, 0, nx), (r1, 2, nz), (r2, 0, -nx), (r2, 2, -nz)], 0.0)
                add([(r1, 2, nx), (r1, 1, nz), (r2, 2, -nx), (r2, 1, -nz)], 0.0)
            else:
                r = ents[0]
                if kind in ("load", "free", "sym", "side", "bottom"):
                    add([(r, 2, 1.0)], 0.0)           # zero shear traction on these boundaries
                if kind in rows:
                    rows[kind].add(r)
                if kind == "opening":                 # traction = -p n (water pressure pushes on the soil)
                    pv = pressure(*P[nd])
                    add([(r, 0, nx), (r, 2, nz)], -pv * nx)
                    add([(r, 2, nx), (r, 1, nz)], -pv * nz)
    # Continuity and boundary rows at a node involve only the stresses at that node, so linear
    # dependence (e.g. one redundant row wherever two straight edges cross at a node) is removed
    # node by node with a pivoted QR. A dropped row is kept anyway if its right-hand side is not
    # implied by the kept rows (cannot happen for a consistent load; checked, not assumed).
    rI, cI, vI, rhs = [], [], [], []
    nrow = ndrop = 0
    for nd, rows_ in groups.items():
        cols = sorted({col * N3 + r for terms, _ in rows_ for (r, col, v) in terms})
        cpos = {c: i for i, c in enumerate(cols)}
        Mloc = np.zeros((len(rows_), len(cols)))
        bloc = np.array([v for _, v in rows_])
        for i, (terms, _) in enumerate(rows_):
            for (r, col, v) in terms:
                Mloc[i, cpos[col * N3 + r]] += v
        _, R, piv = sla.qr(Mloc.T, pivoting=True)
        d = np.abs(np.diag(R)) if R.size else np.array([])
        rank = int((d > 1e-10 * max(d.max(initial=0.0), 1.0)).sum())
        keep = list(piv[:rank])
        if rank < len(rows_):
            K = Mloc[keep]
            for i in piv[rank:]:
                coef, *_ = np.linalg.lstsq(K.T, Mloc[i], rcond=None)
                if abs(coef @ bloc[keep] - bloc[i]) > 1e-9 * max(1.0, abs(bloc[i])):
                    keep.append(i)
                else:
                    ndrop += 1
        for i in keep:
            for j, c in enumerate(cols):
                if Mloc[i, j] != 0.0:
                    rI.append(nrow); cI.append(c); vI.append(Mloc[i, j])
            rhs.append(bloc[i]); nrow += 1
    M = sp.csr_matrix((vI, (rI, cI)), shape=(nrow, 3 * N3))
    rhs = np.array(rhs)
    cons.append(M @ cp.vec(S, order="F") == rhs)
    lr = np.array(sorted(rows["load"])); cons.append(S[lr, 1] == -p)
    if rows["free"]:
        fr = np.array(sorted(rows["free"])); cons.append(S[fr, 1] == 0)
    s_ext = p if m.s_ext_is_load else 0.0
    zrow = np.array([P[T[r // 3, r % 3], 1] for r in range(N3)])
    if rigorous_far:
        sr = np.array(sorted(rows["side"])); br = np.array(sorted(rows["bottom"]))
        cside = 2.0 * strength(rho, zrow[sr])          # exterior beyond x = X has strength c(z)
        cbot = 2.0 * float(strength(rho, -m.Z))        # exterior below z = -Z: weakest at z = -Z (rho >= 0)
        geo_side = gam * zrow[sr]
        cons += [S[sr, 0] - geo_side + s_ext <= cside, S[sr, 0] - geo_side + s_ext >= -cside]
        ub_ = S[br, 1] + gam * m.Z + s_ext
        cons += [ub_ <= kf + cbot, ub_ >= kf - cbot, kf <= cbot, kf >= -cbot]
    # yield imposed with a margin DELTA so that solver feasibility error cannot push the field past c_u
    crow = strength(rho, zrow)
    cons.append(cp.SOC(2.0 * (1.0 - DELTA) * crow, cp.vstack([S[:, 0] - S[:, 1], 2 * S[:, 2]]), axis=0))
    prob = solve(cp.Problem(cp.Maximize(p), cons))
    out = dict(value=float(p.value), status=prob.status, ntri=nt, dropped_rows=ndrop)
    out["audit"] = audit_lower(m, gam, S.value, float(p.value), Bx, Cz, rows,
                               float(kf.value) if rigorous_far else None, rho, pressure)
    return out


def audit_lower(m, gam, Sv, p, Bx, Cz, rows, kf, rho=0.0, pressure=no_pressure):
    P, T = m.P, m.T
    eq = np.concatenate([Bx @ Sv[:, 0] + Cz @ Sv[:, 2], Bx @ Sv[:, 2] + Cz @ Sv[:, 1] - gam])
    # independent of the (reduced) constraint matrix: every edge, every node, from the field itself
    edges, kinds = edges_of(m)
    loc = {(int(T[t, k]), t): 3 * t + k for t in range(len(T)) for k in range(3)}
    res = [0.0]
    for (a_, b_), own in edges.items():
        kind = kinds[(a_, b_)]
        nx, nz = outward_normal(P, T, own[0], a_, b_) if kind == "opening" else _unit(P, a_, b_)
        for nd in (a_, b_):
            sg = [Sv[loc[(nd, t)]] for t in own]
            tr = [np.array([s_[0] * nx + s_[2] * nz, s_[2] * nx + s_[1] * nz]) for s_ in sg]
            if kind == "interior":
                res.append(np.abs(tr[0] - tr[1]).max())
            elif kind == "opening":
                pv = pressure(*P[nd])
                res.append(np.abs(tr[0] + pv * np.array([nx, nz])).max())
            else:
                res.append(abs(sg[0][2]))
                if kind == "free":
                    res.append(abs(sg[0][1]))
    lin = np.array(res)
    zrow = np.array([P[T[r // 3, r % 3], 1] for r in range(len(Sv))])
    crow = strength(rho, zrow)
    tau = np.sqrt(0.25 * (Sv[:, 0] - Sv[:, 1]) ** 2 + Sv[:, 2] ** 2)
    a = dict(equilibrium=float(np.abs(eq).max()), traction_and_bc=float(np.abs(lin).max()),
             yield_excess=float(max(0.0, (tau / crow - 1.0).max())), max_tau=float((tau / crow).max()))
    lr = np.array(sorted(rows["load"])); a["load_bc"] = float(np.abs(Sv[lr, 1] + p).max())
    if kf is not None:
        s_ext = p if m.s_ext_is_load else 0.0
        sr = np.array(sorted(rows["side"])); br = np.array(sorted(rows["bottom"]))
        z = zrow[sr]
        a["side_excess"] = float(max(0.0, (np.abs(Sv[sr, 0] - gam * z + s_ext) - 2 * strength(rho, z)).max()))
        cb = 2 * float(strength(rho, -m.Z))
        v = Sv[br, 1] + gam * m.Z + s_ext
        a["bottom_excess"] = float(max(0.0, (np.abs(v - kf) - cb).max(), abs(kf) - cb))
    return a


# ----------------------------------------------------------------------------------- upper bound
def _pressure_row(m, pressure):
    """Row r with r @ v_n-form: returns sparse rows (Ru, Rw) so that the power of the opening water
    pressure on the soil is -(Ru @ u + Rw @ w), i.e. P_water = -integral of p (n . v) ds, n out of the soil.
    p and v are linear along each edge, so the integral is exact."""
    P, T = m.P, m.T
    edges, kinds = edges_of(m)
    ru, rw = np.zeros(len(P)), np.zeros(len(P))
    for (a, b), own in edges.items():
        if kinds[(a, b)] != "opening":
            continue
        nx, nz = outward_normal(P, T, own[0], a, b)
        L = math.hypot(*(P[b] - P[a]))
        pa, pb = pressure(*P[a]), pressure(*P[b])
        wa, wb = L / 6 * (2 * pa + pb), L / 6 * (pa + 2 * pb)   # integral of p*N_a, p*N_b
        ru[a] += wa * nx; ru[b] += wb * nx
        rw[a] += wa * nz; rw[b] += wb * nz
    return ru, rw


def upper_bound(m: Mesh, gam: float, rho: float = 0.0, pressure=no_pressure):
    P, T = m.P, m.T
    nn, nt = len(P), len(T)
    A, bx, cz = shape_grads(P, T)
    u, w = cp.Variable(nn), cp.Variable(nn)
    rr = np.repeat(np.arange(nt), 3)
    Gx = sp.csr_matrix((bx.ravel(), (rr, T.ravel())), shape=(nt, nn))
    Gz = sp.csr_matrix((cz.ravel(), (rr, T.ravel())), shape=(nt, nn))
    exx, ezz, gxz = Gx @ u, Gz @ w, Gz @ u + Gx @ w
    s = cp.Variable(nt)
    far = np.where((np.abs(P[:, 0] - m.X) < TOL) | (np.abs(P[:, 1] + m.Z) < TOL))[0]
    sym = np.where(np.abs(P[:, 0]) < TOL)[0]
    cons = [exx + ezz == 0, cp.SOC(s, cp.vstack([exx - ezz, gxz]), axis=0),
            u[far] == 0, w[far] == 0, u[sym] == 0]
    flux = _flux_row(m)
    cons.append(flux @ w == 1.0)
    grav = _grav_row(m, A)
    zc = P[T, 1].mean(1)
    wD = A * strength(rho, zc)          # c(z) is linear in z, so its element integral is A*c(centroid)
    ru, rw = _pressure_row(m, pressure)
    # load power = dissipation - gravity power - water power;  p_load*1 = D + gam*int(w) + int p n.v
    prob = solve(cp.Problem(cp.Minimize(wD @ s + gam * (grav @ w) + ru @ u + rw @ w), cons))
    out = dict(value=float(prob.value), status=prob.status, ntri=nt)
    out["audit"] = audit_upper(m, gam, u.value, w.value, Gx, Gz, wD, flux, grav, far, sym,
                               float(prob.value), ru, rw)
    return out


def _flux_row(m):
    edges, kinds = edges_of(m)
    fc, fv = [], []
    for (a, b), k in kinds.items():
        if k == "load":
            L = abs(m.P[b, 0] - m.P[a, 0])
            fc += [a, b]; fv += [-0.5 * L, -0.5 * L]
    return sp.csr_matrix((fv, (np.zeros(len(fc), int), fc)), shape=(1, len(m.P)))


def _grav_row(m, A):
    nt = len(m.T)
    return sp.csr_matrix(((A[:, None] / 3.0 * np.ones((nt, 3))).ravel(),
                          (np.zeros(3 * nt, int), m.T.ravel())), shape=(1, len(m.P)))   # = integral of w


def audit_upper(m, gam, uv, wv, Gx, Gz, wD, flux, grav, far, sym, objective, ru=None, rw=None):
    exx, ezz, gxz = Gx @ uv, Gz @ wv, Gz @ uv + Gx @ wv
    shear = np.sqrt((exx - ezz) ** 2 + gxz ** 2)
    Dint = float(wD @ shear)
    F = float((flux @ wv)[0]); G = float((grav @ wv)[0])
    Wp = float(ru @ uv + rw @ wv) if ru is not None else 0.0
    return dict(incompressibility=float(np.abs(exx + ezz).max() / max(shear.max(), 1e-30)),
                far_bc=float(max(np.abs(uv[far]).max(), np.abs(wv[far]).max())),
                sym_bc=float(np.abs(uv[sym]).max()), flux=F,
                recomputed=(Dint + gam * G + Wp) / F, objective=objective,
                gravity_power=float(-gam * G), water_power=-Wp, dissipation=Dint)


def block(C, gam):
    return 2.0 * C - gam * C


def run(kind, C, D, gam, h, ext=3.0, rho=0.0, pressure=no_pressure):
    m = {"rect": lambda: rect_mesh(C, D, h, ext), "circle": lambda: circle_mesh(C, h, ext),
         "footing": lambda: footing_mesh(h)}[kind]()
    return lower_bound(m, gam, rho, pressure), upper_bound(m, gam, rho, pressure), m


if __name__ == "__main__":
    kind = sys.argv[1]
    C, D, gam, h = (float(v) for v in sys.argv[2:6])
    lb, ub, m = run(kind, C, D, gam, h)
    print(f"{kind} C={C} D={D} gam={gam} h={h} ntri={lb['ntri']}: LB {lb['value']:.4f} ({lb['status']})"
          f"  UB {ub['value']:.4f} ({ub['status']})")
    print("  LB audit:", {k: f"{v:.2e}" for k, v in lb["audit"].items()})
    print("  UB audit:", {k: (f"{v:.2e}" if abs(v) < 1e-2 else f"{v:.4f}") for k, v in ub["audit"].items()})
