"""Plane-strain vertical cut in undrained (Tresca) clay: critical gamma*H/c_u0, lower and upper bounds.
Cut height H = 1, c_u = c_u0 + rho*d with d = -z the depth below the original ground surface (c_u0 = 1).
Soil occupies x < 0 (z < 0) and x > 0 (z < -1). Free surfaces: ground (z = 0, x < 0), the wall (x = 0)
and the cut floor (z = -1, x > 0). The domain is bounded by rigid, rough boundaries at x = -L1, x = L2
and z = -Z (a firm stratum); for that problem both bounds are rigorous, and L1, L2, Z are increased until
they no longer matter. The load factor is the unit weight: the lower bound maximises gamma over admissible
stress fields; the upper bound minimises dissipation for unit gravity power.
Reference (rho = 0, no tension cut-off): 3.77522 <= gamma*H/c <= 3.77649 (Pastor, Loute & Pastor 2009;
as cited by Salencon 2024)."""
import math, sys
import numpy as np, cvxpy as cp, scipy.sparse as sp
import fela_v2 as f

def mesh(h, L1=3.0, L2=3.0, Z=3.0):
    xl = np.unique(np.round(np.concatenate([f.graded(-L1, 0.0, h, 0.4, fine_at="b"), f.graded(0.0, L2, h, 0.4)]), 9))
    zl = np.unique(np.round(np.concatenate([f.graded(-Z, -1.0, h, 0.4, fine_at="b"), f.uniform(-1.0, 0.0, h)]), 9))
    b = f._Builder()
    for i in range(len(xl) - 1):
        for j in range(len(zl) - 1):
            if 0.5 * (xl[i] + xl[i + 1]) > 0 and 0.5 * (zl[j] + zl[j + 1]) > -1.0:
                continue
            b.quad([(xl[i], zl[j]), (xl[i + 1], zl[j]), (xl[i + 1], zl[j + 1]), (xl[i], zl[j + 1])])
    P, T = b.finish()
    return P, T, (L1, L2, Z)

def edges(P, T, dom):
    L1, L2, Z = dom
    E = {}
    for t, tri in enumerate(T):
        for k in range(3):
            a, c = int(tri[k]), int(tri[(k + 1) % 3])
            E.setdefault((min(a, c), max(a, c)), []).append(t)
    kinds = {}
    tol = 1e-9
    for (a, c), own in E.items():
        if len(own) == 2:
            kinds[(a, c)] = "interior"; continue
        (xa, za), (xc, zc) = P[a], P[c]
        if (abs(xa + L1) < tol and abs(xc + L1) < tol) or (abs(xa - L2) < tol and abs(xc - L2) < tol) \
                or (abs(za + Z) < tol and abs(zc + Z) < tol):
            kinds[(a, c)] = "rigid"
        else:
            kinds[(a, c)] = "free"
    return E, kinds

def lower(h, rho=0.0, **dom):
    P, T, d = mesh(h, **dom); nt = len(T); N3 = 3 * nt
    A, bx, cz = f.shape_grads(P, T)
    S = cp.Variable((N3, 3)); g = cp.Variable()
    idx = np.arange(N3).reshape(nt, 3); rr = np.repeat(np.arange(nt), 3)
    Bx = sp.csr_matrix((bx.ravel(), (rr, idx.ravel())), shape=(nt, N3))
    Cz = sp.csr_matrix((cz.ravel(), (rr, idx.ravel())), shape=(nt, N3))
    cons = [Bx @ S[:, 0] + Cz @ S[:, 2] == 0, Bx @ S[:, 2] + Cz @ S[:, 1] - g * np.ones(nt) == 0]
    E, kinds = edges(P, T, d)
    loc = {(int(T[t, k]), t): 3 * t + k for t in range(nt) for k in range(3)}
    groups = {}
    for (a, c), own in E.items():
        kind = kinds[(a, c)]
        if kind == "rigid":
            continue
        nx, nz = f._unit(P, a, c)
        for nd in (a, c):
            ents = [loc[(nd, t)] for t in own]
            if kind == "interior":
                r1, r2 = ents
                groups.setdefault(nd, []).append([(r1, 0, nx), (r1, 2, nz), (r2, 0, -nx), (r2, 2, -nz)])
                groups.setdefault(nd, []).append([(r1, 2, nx), (r1, 1, nz), (r2, 2, -nx), (r2, 1, -nz)])
            else:
                r = ents[0]
                groups.setdefault(nd, []).append([(r, 0, nx), (r, 2, nz)])
                groups.setdefault(nd, []).append([(r, 2, nx), (r, 1, nz)])
    rI, cI, vI = [], [], []; nrow = 0
    import scipy.linalg as sla
    for nd, rows_ in groups.items():
        cols = sorted({col * N3 + r for terms in rows_ for (r, col, v) in terms}); cpos = {c_: i for i, c_ in enumerate(cols)}
        M = np.zeros((len(rows_), len(cols)))
        for i, terms in enumerate(rows_):
            for (r, col, v) in terms: M[i, cpos[col * N3 + r]] += v
        _, R, piv = sla.qr(M.T, pivoting=True)
        dg = np.abs(np.diag(R)); rank = int((dg > 1e-10 * max(dg.max(initial=0), 1)).sum())
        for i in piv[:rank]:
            for j, c_ in enumerate(cols):
                if M[i, j] != 0: rI.append(nrow); cI.append(c_); vI.append(M[i, j])
            nrow += 1
    Mg = sp.csr_matrix((vI, (rI, cI)), shape=(nrow, 3 * N3))
    cons.append(Mg @ cp.vec(S, order="F") == np.zeros(nrow))
    zrow = np.array([P[T[r // 3, r % 3], 1] for r in range(N3)])
    crow = f.strength(rho, zrow)
    cons.append(cp.SOC(2.0 * (1 - f.DELTA) * crow, cp.vstack([S[:, 0] - S[:, 1], 2 * S[:, 2]]), axis=0))
    prob = f.solve(cp.Problem(cp.Maximize(g), cons))
    Sv = S.value; gv = float(g.value)
    # independent audit: equilibrium, free-surface tractions, interior jumps, yield
    eq = max(np.abs(Bx @ Sv[:, 0] + Cz @ Sv[:, 2]).max(), np.abs(Bx @ Sv[:, 2] + Cz @ Sv[:, 1] - gv).max())
    res = 0.0
    for (a, c), own in E.items():
        if kinds[(a, c)] == "rigid": continue
        nx, nz = f._unit(P, a, c)
        for nd in (a, c):
            tr = [np.array([Sv[loc[(nd, t)], 0] * nx + Sv[loc[(nd, t)], 2] * nz, Sv[loc[(nd, t)], 2] * nx + Sv[loc[(nd, t)], 1] * nz]) for t in own]
            res = max(res, np.abs(tr[0] - tr[1]).max() if len(tr) == 2 else np.abs(tr[0]).max())
    tau = np.sqrt(0.25 * (Sv[:, 0] - Sv[:, 1]) ** 2 + Sv[:, 2] ** 2)
    return gv, nt, max(eq, res), float(max(0, (tau / crow - 1).max()))

def upper(h, rho=0.0, **dom):
    P, T, d = mesh(h, **dom); nn, nt = len(P), len(T)
    A, bx, cz = f.shape_grads(P, T); rr = np.repeat(np.arange(nt), 3)
    Gx = sp.csr_matrix((bx.ravel(), (rr, T.ravel())), shape=(nt, nn)); Gz = sp.csr_matrix((cz.ravel(), (rr, T.ravel())), shape=(nt, nn))
    u, w, s = cp.Variable(nn), cp.Variable(nn), cp.Variable(nt)
    exx, ezz, gxz = Gx @ u, Gz @ w, Gz @ u + Gx @ w
    L1, L2, Z = d; tol = 1e-9
    fix = np.where((np.abs(P[:, 0] + L1) < tol) | (np.abs(P[:, 0] - L2) < tol) | (np.abs(P[:, 1] + Z) < tol))[0]
    grav = sp.csr_matrix(((A[:, None] / 3 * np.ones((nt, 3))).ravel(), (np.zeros(3 * nt, int), T.ravel())), shape=(1, nn))
    wD = A * f.strength(rho, P[T, 1].mean(1))
    cons = [exx + ezz == 0, cp.SOC(s, cp.vstack([exx - ezz, gxz]), axis=0), u[fix] == 0, w[fix] == 0, -(grav @ w) == 1.0]
    prob = f.solve(cp.Problem(cp.Minimize(wD @ s), cons))
    uv, wv = u.value, w.value
    e1, e2, e3 = Gx @ uv, Gz @ wv, Gz @ uv + Gx @ wv
    Dv = float(wD @ np.sqrt((e1 - e2) ** 2 + e3 ** 2)); Pg = float(-(grav @ wv)[0])
    return Dv / Pg, nt, float(np.abs(e1 + e2).max() / np.abs(np.sqrt((e1 - e2) ** 2 + e3 ** 2)).max())

if __name__ == "__main__":
    out = []
    def run(label, h, rho=0.0, **dom):
        lb = lower(h, rho, **dom); ub = upper(h, rho, **dom)
        s = (f"{label:34s} ntri={lb[1]:6d}  gamma*H/c_u0: lower {lb[0]:.4f}  upper {ub[0]:.4f}   "
             f"audit eq/trac {lb[2]:.0e} yield+ {lb[3]:.0e} vol {ub[2]:.0e}")
        print(s, flush=True); out.append(s)
    for h in (0.1, 0.05, 0.025):
        run(f"rho=0, h={h}", h)
    run("rho=0, h=0.05, domain x2", 0.05, L1=6.0, L2=6.0, Z=6.0)
    for rho in (0.25, 0.5):
        run(f"rho*H/c_u0={rho}, h=0.05", 0.05, rho)
    open(sys.argv[1], "w").write("\n".join(out) + "\n")
