"""Pipe-roof stability table (Theory Part 5, §5.5b, (5.15)-(5.16a)).

Stores, on a 4-D grid of (C/b_p, a_p/b_p, gamma b_p/c_u0, rho b_p/c_u0):
  N_c0_lo, N_c0_hi   collapse (fall-in) stability number, single (crown) pressure: lower / upper bound
  N_b0_lo, N_b0_hi   blow-out stability number, single pressure: lower / upper end of the bracket
  beta_c_lo/hi, beta_b_lo/hi   support factors of the hydrostatic increase below the crown (full pipe),
                     from solves at one reference gamma_w b_p / c_u0 (stored as gw_ref)
Full pipe (5.16a):  N_full = N_0 + beta * gamma_w a_p / c_u0, applied to each bound separately.
Central estimate = midpoint of the two bounds (a central estimate, not a statistical expectation).

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
GW_MAX = 2.0      # gamma_w b_p / c_u0 range covered by the acceptance test of (5.16a)
FIELDS = ("N_c0_lo", "N_c0_hi", "N_b0_lo", "N_b0_hi", "beta_c_lo", "beta_c_hi", "beta_b_lo", "beta_b_hi")


class TableRangeError(ValueError):
    """A query lies outside the tabulated range (no extrapolation)."""


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
                rows.append({k: float(v) for k, v in r.items() if k in AXES + FIELDS})
        grid = {a: np.array(sorted({r[a] for r in rows})) for a in AXES}
        shape = tuple(len(grid[a]) for a in AXES)
        data = {f: np.full(shape, np.nan) for f in FIELDS}
        for r in rows:
            idx = tuple(int(np.searchsorted(grid[a], r[a])) for a in AXES)
            for f in FIELDS:
                data[f][idx] = r[f]
        missing = int(np.isnan(data["N_c0_lo"]).sum())
        if missing:
            raise ValueError(f"table {path} is incomplete: {missing} grid points missing")
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

    def _interp(self, field: str, q: dict) -> float:
        cell, w = self._weights(q)
        arr = self.data[field]
        tot = 0.0
        for corner in range(16):
            idx, wt = [], 1.0
            for k in range(4):
                bit = (corner >> k) & 1
                idx.append(cell[k][bit])
                wt *= w[k] if bit else (1.0 - w[k])
            if wt:
                tot += wt * arr[tuple(idx)]
        return float(tot)

    def query(self, C_b, a_b, g_b, rho_b, gw_b=0.0, full=False, mechanism="collapse"):
        """Return dict(lo, hi, mid) of the stability number (sigma_s - p_cr)/c_u0.
        full=True adds the hydrostatic support of a full pipe, beta * gw_b * a_b (5.16a)."""
        q = dict(C_b=C_b, a_b=a_b, g_b=g_b, rho_b=rho_b)
        key = {"collapse": "c", "blowout": "b"}[mechanism]
        lo = self._interp(f"N_{key}0_lo", q)
        hi = self._interp(f"N_{key}0_hi", q)
        if full:
            if not (0.0 <= gw_b <= GW_MAX):
                raise TableRangeError(f"gw_b = {gw_b:g} outside the acceptance-tested range [0, {GW_MAX:g}]")
            lo += self._interp(f"beta_{key}_lo", q) * gw_b * a_b
            hi += self._interp(f"beta_{key}_hi", q) * gw_b * a_b
        return dict(lo=lo, hi=hi, mid=0.5 * (lo + hi))
