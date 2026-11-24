"""Vertical undrained cut with water standing in the excavation to height xi*H above the toe.
Water pressure p = lam*gw_hat*(z_w - z) acts on the wall below z_w and on the floor; the soil unit weight
is lam*1 (gw_hat = gamma_w/gamma). Lower bound: maximise lam over admissible fields (rigorous for the
bounded problem, as in fela_cut.py). Result: critical gamma*H/c_u0 as a function of xi.
Exact check: xi = 1 is the dry problem with buoyant weight (gamma - gamma_w), i.e. lam_wet = lam_dry/(1 - gw_hat)."""
import sys
import numpy as np, cvxpy as cp, scipy.sparse as sp, scipy.linalg as sla
import fela_v2 as f, fela_cut as fc

def lower_wet(h, xi, gw_hat=0.5, rho=0.0, **dom):
    P, T, d = fc.mesh(h, **dom); nt = len(T); N3 = 3 * nt
    A, bx, cz = f.shape_grads(P, T)
    S = cp.Variable((N3, 3)); g = cp.Variable()
    idx = np.arange(N3).reshape(nt, 3); rr = np.repeat(np.arange(nt), 3)
    Bx = sp.csr_matrix((bx.ravel(), (rr, idx.ravel())), shape=(nt, N3))
    Cz = sp.csr_matrix((cz.ravel(), (rr, idx.ravel())), shape=(nt, N3))
    cons = [Bx @ S[:, 0] + Cz @ S[:, 2] == 0, Bx @ S[:, 2] + Cz @ S[:, 1] - g * np.ones(nt) == 0]
    E, kinds = fc.edges(P, T, d)
    loc = {(int(T[t, k]), t): 3 * t + k for t in range(nt) for k in range(3)}
    zw = -1.0 + xi
    groups = {}
    for (a, c), own in E.items():
        kind = kinds[(a, c)]
        if kind == "rigid": continue
        if kind == "free":
            nx, nz = f.outward_normal(P, T, own[0], a, c)
        else:
            nx, nz = f._unit(P, a, c)
        for nd in (a, c):
            ents = [loc[(nd, t)] for t in own]
            if kind == "interior":
                r1, r2 = ents
                groups.setdefault(nd, []).append(([(r1, 0, nx), (r1, 2, nz), (r2, 0, -nx), (r2, 2, -nz)], 0.0))
                groups.setdefault(nd, []).append(([(r1, 2, nx), (r1, 1, nz), (r2, 2, -nx), (r2, 1, -nz)], 0.0))
            else:
                r = ents[0]; x0, z0 = P[nd]
                wet = (x0 >= -1e-9) and (z0 < zw - 1e-12)      # wall (x = 0) or floor (x > 0) below water
                pw = gw_hat * (zw - z0) if wet else 0.0          # per unit lam
                # sigma.n + lam*pw*n = 0
                groups.setdefault(nd, []).append(([(r, 0, nx), (r, 2, nz)], pw * nx))
                groups.setdefault(nd, []).append(([(r, 2, nx), (r, 1, nz)], pw * nz))
    rI, cI, vI, gI, gV = [], [], [], [], []; nrow = 0
    for nd, rows_ in groups.items():
        cols = sorted({col * N3 + r for terms, _ in rows_ for (r, col, v) in terms}); cpos = {c_: i for i, c_ in enumerate(cols)}
        M = np.zeros((len(rows_), len(cols) + 1))
        for i, (terms, gc) in enumerate(rows_):
            for (r, col, v) in terms: M[i, cpos[col * N3 + r]] += v
            M[i, -1] = gc
        _, R, piv = sla.qr(M.T, pivoting=True)
        dg = np.abs(np.diag(R)); rank = int((dg > 1e-10 * max(dg.max(initial=0), 1)).sum())
        for i in piv[:rank]:
            for j, c_ in enumerate(cols):
                if M[i, j] != 0: rI.append(nrow); cI.append(c_); vI.append(M[i, j])
            gI.append(nrow); gV.append(M[i, -1]); nrow += 1
    Mg = sp.csr_matrix((vI, (rI, cI)), shape=(nrow, 3 * N3)); gvec = np.zeros(nrow); gvec[gI] = gV
    cons.append(Mg @ cp.vec(S, order="F") + g * gvec == 0)
    zrow = np.array([P[T[r // 3, r % 3], 1] for r in range(N3)])
    crow = f.strength(rho, zrow)
    cons.append(cp.SOC(2.0 * (1 - f.DELTA) * crow, cp.vstack([S[:, 0] - S[:, 1], 2 * S[:, 2]]), axis=0))
    f.solve(cp.Problem(cp.Maximize(g), cons))
    Sv, gv = S.value, float(g.value)
    # audit: equilibrium, tractions (with the water load), yield
    eq = max(np.abs(Bx @ Sv[:, 0] + Cz @ Sv[:, 2]).max(), np.abs(Bx @ Sv[:, 2] + Cz @ Sv[:, 1] - gv).max())
    res = 0.0
    for (a, c), own in E.items():
        if kinds[(a, c)] == "rigid": continue
        nx, nz = f.outward_normal(P, T, own[0], a, c) if kinds[(a, c)] == "free" else f._unit(P, a, c)
        for nd in (a, c):
            tr = [np.array([Sv[loc[(nd, t)], 0] * nx + Sv[loc[(nd, t)], 2] * nz, Sv[loc[(nd, t)], 2] * nx + Sv[loc[(nd, t)], 1] * nz]) for t in own]
            if len(tr) == 2: res = max(res, np.abs(tr[0] - tr[1]).max())
            else:
                x0, z0 = P[nd]; wet = (x0 >= -1e-9) and (z0 < zw - 1e-12)
                pw = gv * gw_hat * (zw - z0) if wet else 0.0
                res = max(res, np.abs(tr[0] + pw * np.array([nx, nz])).max())
    tau = np.sqrt(0.25 * (Sv[:, 0] - Sv[:, 1]) ** 2 + Sv[:, 2] ** 2)
    return gv, max(eq, res), float(max(0, (tau / crow - 1).max()))

if __name__ == "__main__":
    out = []; base = None
    for xi in (0.0, 0.25, 0.5, 0.75, 1.0):
        lam, aud, ye = lower_wet(0.05, xi)
        base = base or lam
        r = 0.5
        s = (f"xi=h_w/H={xi:4.2f}  gamma_w/gamma=0.5: lower bound gamma*H/c = {lam:.4f}  ratio to dry {lam/base:.4f}  "
             f"| 1/(1-r*xi^2) {1/(1-r*xi*xi):.4f}  1/(1-r*xi^3) {1/(1-r*xi**3):.4f}  audit {aud:.0e} yield+ {ye:.0e}")
        print(s, flush=True); out.append(s)
    open(sys.argv[1], "w").write("\n".join(out) + "\n")
