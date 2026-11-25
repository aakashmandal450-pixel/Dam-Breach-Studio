"""Pipe-roof stability table (Theory Part 5, §5.5b, (5.15)-(5.16a)).

Stores, on a 4-D grid of (C/b_p, a_p/b_p, gamma b_p/c_u0, rho b_p/c_u0):
  N_c0_lo, N_c0_hi   collapse (fall-in) stability number, single (crown) pressure: lower / upper bound
  N_b0_lo, N_b0_hi   blow-out stability number, single pressure: lower / upper end of the bracket
  beta_c_lo/hi, beta_b_lo/hi   support factors of the hydrostatic increase below the crown (full pipe),
                     from solves at one reference gamma_w b_p / c_u0 (stored as gw_ref)
Full pipe (5.16b), exact for Tresca: N_full(g, gw) = N_0(g - gw) - gw C/b_p, with gw = gamma_w b_p/c_u0 <= g.
(The support factors beta of the earlier reduced form (5.16a) are still stored but no longer used.)
Central estimate = midpoint of the two bounds (a central estimate, not a statistical expectation).

Overburden shift (5.15b), exact for undrained Tresca: the field sigma = sigma' + gamma z I is deviator-free, so
  N(C, a, g, rho) = N'(C, a, g, rho) - g (C/b_p + a_p/b_p),
where N' is the stability number of the weightless problem whose opening pressure varies by gamma over the
opening height; N' depends on g only through that gradient and is nearly linear in g. The table therefore
interpolates N' (stored internally) and adds back the exact shift at the query point.
Sparse self-weight axis: for C/b_p >= SPARSE_C_MIN the nodes g in SPARSE_G are not solved; N' and beta there
are filled by linear interpolation in g between the solved neighbours (flag meta["derived"]). Justified by the
check on 344 solved points (worst error 0.05 of the half-bracket for C/b_p >= 12; theory §5.5b, (5.15b)) and verified by the
acceptance test, which includes derived nodes.

Interpolation: multilinear in (C/b_p, log a_p/b_p, gamma b_p/c_u0, rho b_p/c_u0).
Outside the grid: TableRangeError naming the parameter and its value. No extrapolation.
Lengths are made dimensionless by b_p, stresses by c_u0 (surface strength).
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass

import numpy as np

AXES = ("C_b", "a_b", "g_b", "rho_b")
SPARSE_C_MIN = 12.0
SPARSE_G = (0.5, 1.0, 2.0)
A_FINE = (0.7071, 1.4142)  # extra a/b nodes (geometric midpoints), solved only for C/b <= A_FINE_C_MAX;
A_FINE_C_MAX = 4.0         # deeper slices get them by linear interpolation in log a (same function as before)
N_FIELDS = ("N_c0_lo", "N_c0_hi", "N_b0_lo", "N_b0_hi")
FIELDS = ("N_c0_lo", "N_c0_hi", "N_b0_lo", "N_b0_hi", "beta_c_lo", "beta_c_hi", "beta_b_lo", "beta_b_hi")


class TableRangeError(ValueError):
    """A query lies outside the tabulated range (no extrapolation)."""


class UnstableOpening(ValueError):
    """The query lies in a region where the bound solves show no stable state at any surface load.
    SELF_UNSTABLE: a kinematic mechanism collapses the opening under its own weight (rigorous: it
    collapses). NO_STATIC_BOUND: no admissible stress field exists (no certificate of stability; the
    lower bound is open). The engine treats both as collapse and flags the region (policy for review)."""


def _t(axis: str, v):
    """Interpolation coordinate. Linear in C/b_p: the weight and blow-out terms grow about linearly with
    cover (a log axis bent them and failed the acceptance test on a coarse grid). Logarithmic in a_p/b_p,
    whose nodes are a geometric series. Linear in the strength and weight ratios."""
    return np.log(v) if axis == "a_b" else np.asarray(v, float)


@dataclass
class StabilityTable:
    grid: dict            # axis -> sorted 1-D array of node values
    data: dict            # field -> 4-D array, shape = lengths of the axes in AXES order
    gw_ref: float
    meta: dict

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_csv(cls, path: str) -> "StabilityTable":
        rows, meta = [], {}
        with open(path, newline="") as fh:
            for line in fh:
                if line.startswith("#"):
                    k, _, v = line[1:].strip().partition("=")
                    meta[k.strip()] = v.strip()
                    continue
                fh.seek(0)
                break
            rdr = csv.DictReader(l for l in fh if not l.startswith("#"))
            for r in rdr:
                if r.get("status") not in ("OK", "SELF_UNSTABLE", "NO_STATIC_BOUND"):
                    continue                     # failed or unfinished rows are not part of the table
                row = {k: float(v) if v not in ("", None) else float("nan") for k, v in r.items() if k in AXES + FIELDS}
                row["status"] = r["status"]
                rows.append(row)
        grid = {a: np.array(sorted({r[a] for r in rows})) for a in AXES}
        shape = tuple(len(grid[a]) for a in AXES)
        data = {f: np.full(shape, np.nan) for f in FIELDS}
        status = np.full(shape, "", dtype=object)
        for r in rows:
            idx = tuple(int(np.searchsorted(grid[a], r[a])) for a in AXES)
            for f in FIELDS:
                data[f][idx] = r[f]
            status[idx] = r["status"]
        # stored N -> N' (5.15b): add the exact overburden shift g (C + a)
        Cg, Ag, Gg = np.meshgrid(grid["C_b"], grid["a_b"], grid["g_b"], indexing="ij")
        shift = (Gg * (Cg + Ag))[..., None]
        for f in N_FIELDS:
            data[f] = data[f] + shift
        derived = np.zeros(shape, bool)
        gnodes = list(grid["g_b"])
        for i, C in enumerate(grid["C_b"]):
            if C < SPARSE_C_MIN - 1e-9:
                continue
            for k, g in enumerate(gnodes):
                if not any(abs(g - s_) < 1e-9 for s_ in SPARSE_G):
                    continue
                for j in range(shape[1]):
                    for l in range(shape[3]):
                        if status[i, j, k, l] != "":
                            continue
                        lo = max((kk for kk in range(k) if status[i, j, kk, l] != "" and not derived[i, j, kk, l]), default=None)
                        hi = min((kk for kk in range(k + 1, len(gnodes)) if status[i, j, kk, l] != "" and not derived[i, j, kk, l]), default=None)
                        if lo is None or hi is None:
                            continue
                        w = (g - gnodes[lo]) / (gnodes[hi] - gnodes[lo])
                        for f in FIELDS:
                            data[f][i, j, k, l] = (1 - w) * data[f][i, j, lo, l] + w * data[f][i, j, hi, l]
                        sl, sh = status[i, j, lo, l], status[i, j, hi, l]
                        status[i, j, k, l] = "OK" if sl == sh == "OK" else (sl if sl != "OK" else sh)
                        derived[i, j, k, l] = True
        # extra a/b nodes on deep slices: linear in log a between the solved neighbours (identical to the
        # piecewise-linear interpolant on the coarse a nodes, so the deep table is unchanged)
        anodes = list(grid["a_b"]); la = np.log(anodes)
        for i, C in enumerate(grid["C_b"]):
            if C <= A_FINE_C_MAX + 1e-9:
                continue
            for j, a in enumerate(anodes):
                if not any(abs(a - f_) < 1e-3 for f_ in A_FINE):
                    continue
                for k in range(shape[2]):
                    for l in range(shape[3]):
                        if status[i, j, k, l] != "":
                            continue
                        lo = max((jj for jj in range(j) if status[i, jj, k, l] != "" and not any(abs(anodes[jj] - f_) < 1e-3 for f_ in A_FINE)), default=None)
                        hi = min((jj for jj in range(j + 1, len(anodes)) if status[i, jj, k, l] != "" and not any(abs(anodes[jj] - f_) < 1e-3 for f_ in A_FINE)), default=None)
                        if lo is None or hi is None:
                            continue
                        w = (la[j] - la[lo]) / (la[hi] - la[lo])
                        for f in FIELDS:
                            data[f][i, j, k, l] = (1 - w) * data[f][i, lo, k, l] + w * data[f][i, hi, k, l]
                        sl, sh = status[i, lo, k, l], status[i, hi, k, l]
                        status[i, j, k, l] = "OK" if sl == sh == "OK" else (sl if sl != "OK" else sh)
                        derived[i, j, k, l] = True
        meta["derived"] = derived
        missing = int((status == "").sum())
        if missing:
            raise ValueError(f"table {path} is incomplete: {missing} grid points missing")
        meta["status"] = status
        return cls(grid, data, float(meta.get("gw_ref", "nan")), meta)

    # ------------------------------------------------------------------ queries
    def _weights(self, q: dict):
        cell, w = [], []
        for a in AXES:
            nodes = self.grid[a]
            v = q[a]
            if not (nodes[0] - 1e-12 <= v <= nodes[-1] + 1e-12):
                raise TableRangeError(f"{a} = {v:g} outside the table range [{nodes[0]:g}, {nodes[-1]:g}]")
            if len(nodes) == 1:
                cell.append((0, 0)); w.append(0.0); continue
            t = _t(a, nodes); tv = float(_t(a, min(max(v, nodes[0]), nodes[-1])))
            i = int(np.clip(np.searchsorted(t, tv) - 1, 0, len(t) - 2))
            f = (tv - t[i]) / (t[i + 1] - t[i])
            cell.append((i, i + 1)); w.append(float(np.clip(f, 0.0, 1.0)))
        return cell, w

    def _corners(self, q: dict):
        cell, w = self._weights(q)
        for corner in range(16):
            idx, wt = [], 1.0
            for k in range(4):
                bit = (corner >> k) & 1
                idx.append(cell[k][bit])
                wt *= w[k] if bit else (1.0 - w[k])
            if wt:
                yield tuple(idx), wt

    def _check_stable(self, q: dict):
        st = self.meta.get("status")
        if st is None:
            return
        bad = {st[idx] for idx, wt in self._corners(q) if st[idx] != "OK"}
        if bad:
            raise UnstableOpening(f"{', '.join(sorted(bad))} at a neighbouring grid point of "
                                  + ", ".join(f"{a} = {q[a]:g}" for a in AXES))

    def _interp(self, field: str, q: dict) -> float:
        arr = self.data[field]
        return float(sum(wt * arr[idx] for idx, wt in self._corners(q)))

    def query(self, C_b, a_b, g_b, rho_b, gw_b=0.0, full=False, mechanism="collapse"):
        """Return dict(lo, hi, mid) of the stability number (sigma_s - p_cr)/c_u0.
        full=True adds the hydrostatic support of a full pipe, beta * gw_b * a_b (5.16a)."""
        key = {"collapse": "c", "blowout": "b"}[mechanism]
        if full:
            # Exact full-pipe identity (5.16b): the water column adds gamma_w (z - z_crown) to the wall
            # pressure; after the overburden shift only the net gradient (gamma - gamma_w) acts on the
            # opening, so N_full(g, gw) = N_0(g - gw) - gw C/b_p. No support factor, no fifth dimension.
            if gw_b < 0.0 or gw_b > g_b + 1e-12:
                raise TableRangeError(f"gw_b = {gw_b:g} outside [0, g_b = {g_b:g}] (the identity needs "
                                      f"gamma >= gamma_w)")
            r = self.query(C_b, a_b, g_b - gw_b, rho_b, mechanism=mechanism)
            return dict(lo=r["lo"] - gw_b * C_b, hi=r["hi"] - gw_b * C_b, mid=r["mid"] - gw_b * C_b)
        q = dict(C_b=C_b, a_b=a_b, g_b=g_b, rho_b=rho_b)
        self._check_stable(q)
        shift = g_b * (C_b + a_b)                    # exact overburden term (5.15b)
        lo = self._interp(f"N_{key}0_lo", q) - shift
        hi = self._interp(f"N_{key}0_hi", q) - shift
        return dict(lo=lo, hi=hi, mid=0.5 * (lo + hi))
