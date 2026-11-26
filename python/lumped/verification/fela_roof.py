"""Finite element limit analysis (FELA) of a rectangular opening in undrained (Tresca) clay.

Plane strain section across the pipe; symmetric half domain; ground surface horizontal at z = 0.
Opening: width B = 1 (half-width 0.5), height D, cover C above its crown. c_u = 1 (lengths in B,
stresses in c_u). Internal pressure sigma_t = 0; the bounds are on the surcharge sigma_s at collapse:

    N = (sigma_s - sigma_t)/c_u   (Davis et al. 1980 stability number for openings)

Lower bound: linear stress triangles with statically admissible discontinuities on every edge,
equilibrium with self-weight, traction boundary conditions, Tresca yield as a second-order cone
at every node; maximise sigma_s. (Far boundaries are left free; no extension elements, so the
lower bound is rigorous only as the domain grows.)

Upper bound: linear velocity triangles on a crossed ("union jack") mesh, which avoids
incompressibility locking; no velocity discontinuities; far boundaries fixed (so the field is
kinematically admissible in the infinite domain and the upper bound is rigorous); minimise
internal dissipation minus gravity power for unit surface flux.
"""
from __future__ import annotations

import math
import sys

import cvxpy as cp
import numpy as np
import scipy.sparse as sp


def solve(prob):
    """Clarabel at 1e-5 relative tolerance (bounds are reported to 3 decimals); SCS as fallback."""
    for kw in (dict(tol_gap_abs=1e-5, tol_gap_rel=1e-5, tol_feas=1e-6, tol_ktratio=1e-5, max_iter=300,
                    static_regularization_constant=1e-7),
               dict(tol_gap_abs=1e-4, tol_gap_rel=1e-4, tol_feas=1e-5, max_iter=300)):
        try:
            prob.solve(solver=cp.CLARABEL, **kw)
            return prob
        except cp.error.SolverError:
            pass
    prob.solve(solver=cp.SCS, eps=1e-7, max_iters=200000)
    return prob


def graded(a: float, b: float, h0: float, hmax: float, r: float = 1.15, fine_at: str = "a") -> np.ndarray:
    """Coordinates from a to b, spacing h0 at the 'fine' end growing by r up to hmax."""
    L = b - a
    steps, h = [], h0
    while sum(steps) < L - 1e-12:
        steps.append(min(h, hmax))
        h *= r
    steps = np.array(steps) * L / sum(steps)
    if fine_at == "b":
        steps = steps[::-1]
    return a + np.concatenate([[0.0], np.cumsum(steps)])


def mesh(C: float, D: float, h: float):
    X = 0.5 + max(3.0 * (C + D), 3.0)
    Z = C + D + max(1.5 * (C + D), 2.0)
    xs = np.unique(np.round(np.concatenate([graded(0.0, 0.5, h, h), graded(0.5, X, h, 1.0, fine_at="a")]), 9))
    zs = np.unique(np.round(np.concatenate([graded(-Z, -C - D, h, 1.0, fine_at="b"), graded(-C - D, -C, h, h),
                                   graded(-C, 0.0, h, max(h, min(0.5, C / 6)), fine_at="a")]), 9))
    nodes, nid = [], {}

    def node(x, z):
        k = (round(x, 10), round(z, 10))
        if k not in nid:
            nid[k] = len(nodes)
            nodes.append((x, z))
        return nid[k]

    tris = []
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
            xc, zc = 0.5 * (x0 + x1), 0.5 * (z0 + z1)
            if xc < 0.5 and -C - D < zc < -C:
                continue                                   # inside the opening
            a, b, c, d, e = node(x0, z0), node(x1, z0), node(x1, z1), node(x0, z1), node(xc, zc)
            tris += [(a, b, e), (b, c, e), (c, d, e), (d, a, e)]
    P = np.array(nodes)
    T = np.array(tris)
    # orient counter-clockwise
    v1, v2 = P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]]
    cw = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0] < 0
    T[cw] = T[cw][:, [0, 2, 1]]
    return P, T, X, Z


def shape_grads(P, T):
    p0, p1, p2 = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    A2 = (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p2[:, 0] - p0[:, 0]) * (p1[:, 1] - p0[:, 1])
    b = np.stack([p1[:, 1] - p2[:, 1], p2[:, 1] - p0[:, 1], p0[:, 1] - p1[:, 1]], 1) / A2[:, None]   # dN/dx
    c = np.stack([p2[:, 0] - p1[:, 0], p0[:, 0] - p2[:, 0], p1[:, 0] - p0[:, 0]], 1) / A2[:, None]   # dN/dz
    return 0.5 * A2, b, c


def classify_edges(P, T, C, D, X, Z):
    edges = {}
    for t, tri in enumerate(T):
        for k in range(3):
            a, b = tri[k], tri[(k + 1) % 3]
            edges.setdefault((min(a, b), max(a, b)), []).append((t, k))
    tol = 1e-9
    kinds = {}
    for (a, b), owners in edges.items():
        if len(owners) == 2:
            kinds[(a, b)] = "interior"
            continue
        (xa, za), (xb, zb) = P[a], P[b]
        if abs(za) < tol and abs(zb) < tol:
            kinds[(a, b)] = "surface"
        elif abs(xa) < tol and abs(xb) < tol:
            kinds[(a, b)] = "symmetry"
        elif abs(xa - X) < tol and abs(xb - X) < tol or abs(za + Z) < tol and abs(zb + Z) < tol:
            kinds[(a, b)] = "far"
        else:
            kinds[(a, b)] = "opening"
    return edges, kinds


def lower_bound(C, D, gam, h=0.1):
    P, T, X, Z = mesh(C, D, h)
    nt = len(T)
    A, bx, cz = shape_grads(P, T)
    S = cp.Variable((nt * 3, 3))          # rows: (tri, local node); cols: sxx, szz, sxz
    ss = cp.Variable()
    rows = lambda t: [3 * t, 3 * t + 1, 3 * t + 2]
    cons = []
    # equilibrium (vectorised): sum_k (bx_k sxx_k + cz_k sxz_k) = 0 ; sum_k (bx_k sxz_k + cz_k szz_k) = gam
    idx = np.arange(nt * 3).reshape(nt, 3)
    Bx = sp.csr_matrix((bx.ravel(), (np.repeat(np.arange(nt), 3), idx.ravel())), shape=(nt, 3 * nt))
    Cz = sp.csr_matrix((cz.ravel(), (np.repeat(np.arange(nt), 3), idx.ravel())), shape=(nt, 3 * nt))
    cons += [Bx @ S[:, 0] + Cz @ S[:, 2] == 0, Bx @ S[:, 2] + Cz @ S[:, 1] == gam]
    edges, kinds = classify_edges(P, T, C, D, X, Z)
    rI, cI, vI, rhs = [], [], [], []   # generic linear rows on vec(S) (column-major: col*3nt + row)
    nrow = 0
    N3 = 3 * nt

    def add(terms, value):
        nonlocal nrow
        for (r, col, v) in terms:
            rI.append(nrow); cI.append(col * N3 + r); vI.append(v)
        rhs.append(value); nrow += 1

    surf_rows = []
    for (a, b), owners in edges.items():
        kind = kinds[(a, b)]
        (xa, za), (xb, zb) = P[a], P[b]
        L = math.hypot(xb - xa, zb - za)
        tx, tz = (xb - xa) / L, (zb - za) / L   # L > 0 after coordinate rounding
        nx, nz = tz, -tx                       # a unit normal (sign irrelevant for continuity)
        for node in (a, b):
            ents = []
            for (t, k) in owners:
                loc = list(T[t]).index(node)
                ents.append(3 * t + loc)
            if kind == "interior":
                r1, r2 = ents
                add([(r1, 0, nx), (r1, 2, nz), (r2, 0, -nx), (r2, 2, -nz)], 0.0)   # t_x
                add([(r1, 2, nx), (r1, 1, nz), (r2, 2, -nx), (r2, 1, -nz)], 0.0)   # t_z
            else:
                r = ents[0]
                if kind == "surface":
                    add([(r, 2, 1.0)], 0.0)                     # sxz = 0
                    surf_rows.append(r)                        # szz = -ss (below)
                elif kind == "symmetry":
                    add([(r, 2, 1.0)], 0.0)                    # shear = 0 on symmetry line
                elif kind == "opening":
                    add([(r, 0, nx), (r, 2, nz)], 0.0)          # traction-free (sigma_t = 0)
                    add([(r, 2, nx), (r, 1, nz)], 0.0)
    M = sp.csr_matrix((vI, (rI, cI)), shape=(nrow, 3 * N3))
    s_vec = cp.vec(S, order="F")
    cons.append(M @ s_vec == np.array(rhs))
    sr = np.array(sorted(set(surf_rows)))
    cons.append(S[sr, 1] == -ss)
    # Tresca yield at every node
    cons.append(cp.SOC(2.0 * np.ones(N3), cp.vstack([S[:, 0] - S[:, 1], 2 * S[:, 2]]), axis=0))
    prob = solve(cp.Problem(cp.Maximize(ss), cons))
    return ss.value, len(T), prob.status


def upper_bound(C, D, gam, h=0.1):
    P, T, X, Z = mesh(C, D, h)
    nn, nt = len(P), len(T)
    A, bx, cz = shape_grads(P, T)
    u, w = cp.Variable(nn), cp.Variable(nn)
    rr = np.repeat(np.arange(nt), 3)
    Gx = sp.csr_matrix((bx.ravel(), (rr, T.ravel())), shape=(nt, nn))
    Gz = sp.csr_matrix((cz.ravel(), (rr, T.ravel())), shape=(nt, nn))
    exx, ezz, gxz = Gx @ u, Gz @ w, Gz @ u + Gx @ w
    s = cp.Variable(nt)
    cons = [exx + ezz == 0, cp.SOC(s, cp.vstack([exx - ezz, gxz]), axis=0)]
    tol = 1e-9
    far = np.where((np.abs(P[:, 0] - X) < tol) | (np.abs(P[:, 1] + Z) < tol))[0]
    sym = np.where(np.abs(P[:, 0]) < tol)[0]
    cons += [u[far] == 0, w[far] == 0, u[sym] == 0]
    # surface flux (downward), half domain
    edges, kinds = classify_edges(P, T, C, D, X, Z)
    fr, fc, fv = [], [], []
    for (a, b), k in kinds.items():
        if k == "surface":
            L = abs(P[b, 0] - P[a, 0])
            fc += [a, b]; fv += [-0.5 * L, -0.5 * L]
    flux = sp.csr_matrix((fv, (np.zeros(len(fc), int), fc)), shape=(1, nn))
    cons.append(flux @ w == 1.0)
    grav = sp.csr_matrix(((-A[:, None] / 3.0 * np.ones((nt, 3))).ravel(), (np.zeros(3 * nt, int), T.ravel())), shape=(1, nn))
    obj = A @ s - gam * (grav @ w)
    prob = solve(cp.Problem(cp.Minimize(cp.sum(obj)), cons))
    return prob.value, nt, prob.status


def block(C, gam):
    """Rigid two-plane block (mechanism A) = Terzaghi with phi = 0: an upper bound."""
    return 2.0 * C - gam * C


if __name__ == "__main__":
    C, D, gam, h = (float(v) for v in sys.argv[1:5])
    lb = lower_bound(C, D, gam, h)
    ub = upper_bound(C, D, gam, h)
    print(f"C/B={C} D/B={D} gB/cu={gam} h={h}: LB {lb[0]:.3f} ({lb[1]} tri, {lb[2]})  "
          f"UB {ub[0]:.3f} ({ub[2]})  block {block(C, gam):.3f}")
