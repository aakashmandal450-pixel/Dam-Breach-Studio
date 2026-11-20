"""Numba kernels for the morphology of breach_engine_2d_v3_2 (V3.4).

Switched on together with the hydraulics by fast_hydro.enable(); the engine file is unchanged and stays the reference.

Compiled (each kernel follows the NumPy code term by term, in the same order):
  BankStability.check_and_collapse   both collapse modes ('unsupported' V3.2.2 and C2 'all_pairs'), all passes
  Headcut._migrate_scarp             C1 scarp headcut in x and y (all three rate laws)
  Headcut._migrate_scarp_volume      F7 volume-based scarp retreat with local face detection
  LateralErosion._apply_axis         lateral bank retreat, lateral_model 'critical_shear' (force_balance -> NumPy)
  Morphology._advect                 conservative upwind sediment advection with the outflow limiter

Agreement with NumPy:
  _advect is arithmetic only and is bit-identical.
  The other three use arctan / sin / cos / tan / cbrt. Numba calls the C maths library, NumPy may use its own SIMD
  versions, and the two differ in the last bit for part of the inputs. Results therefore agree to round-off
  (about 1e-16 relative per step), not bit for bit; in a full run the difference then grows like any round-off
  perturbation of this chaotic second-order scheme (see RUNS.md, 'fast backend'). A given backend is deterministic.
  The returned diagnostic volumes are summed in a different order from np.sum (round-off only).
"""
from __future__ import annotations

import numpy as np

import breach_engine_2d_v3_2 as E

try:
    from numba import njit
    HAVE_NUMBA = True
except Exception:          # pragma: no cover
    HAVE_NUMBA = False

    def njit(*a, **k):     # type: ignore
        def deco(f):
            return f
        return deco if not (a and callable(a[0])) else a[0]

_ORIG = {
    "collapse": E.BankStability.check_and_collapse,
    "scarp": E.Headcut._migrate_scarp,
    "scarp_volume": E.Headcut._migrate_scarp_volume,
    "lateral": E.LateralErosion._apply_axis,
    "advect": E.Morphology._advect,
}
_ENABLED = False

HC_ENERGY, HC_TEMPLE, HC_SITES_KH, HC_SITES_A0 = 0, 1, 2, 3


# ----------------------------------------------------------------------------------------------------------------
# bank collapse (BankStability._collapse_pairs / _collapse_pairs_all + check_and_collapse loop)
# ----------------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _collapse_pair(z, S, h, ia, ja, ib, jb, ds, all_pairs, c, gamma, phi_mat, phi_dry, phi_wet, hsw, h_dry, p,
                   fs_trig, fs_target, minfs):
    zA = z[ia, ja]
    zB = z[ib, jb]
    hA = h[ia, ja]
    hB = h[ib, jb]
    dz = zA - zB
    ad = abs(dz)
    beta = np.arctan(ad / ds)
    if all_pairs:
        phi = phi_wet if (hA > hsw and hB > hsw) else phi_dry
    else:
        phi = phi_mat
    if beta > phi:
        num = 4.0 * c * np.sin(beta) * np.cos(phi)
        den = gamma * (1.0 - np.cos(beta - phi)) + 1e-12
        Zc = num / den
    else:
        Zc = np.inf
    FS = Zc / max(ad, 1e-12)
    if ad > 1e-9 and FS < minfs[0]:
        minfs[0] = FS
    target = min(max(Zc / fs_target, ds * np.tan(phi)), ad)
    d = ad - target if FS < fs_trig else 0.0
    wetA = hA > h_dry
    wetB = hB > h_dry
    if all_pairs:
        d = 0.5 * d if d > 1e-6 else 0.0
    else:
        unsupported = (dz > 0.0 and (not wetA) and wetB) or (dz < 0.0 and wetA and (not wetB))
        d = d if (d > 1e-6 and unsupported) else 0.0
    fromA = d if dz > 0 else 0.0
    fromB = d if dz < 0 else 0.0
    zA -= fromA
    zB -= fromB
    toA = fromB
    toB = fromA
    if wetA:
        S[ia, ja] += (1.0 - p) * toA
    else:
        zA += toA
    if wetB:
        S[ib, jb] += (1.0 - p) * toB
    else:
        zB += toB
    z[ia, ja] = zA
    z[ib, jb] = zB
    return d


@njit(cache=True)
def _collapse(z, S, h, dx, dy, all_pairs, c, gamma, phi_mat, phi_dry, phi_wet, hsw, h_dry, p, fs_trig, fs_target,
              iters):
    nx, ny = z.shape
    minfs = np.full(1, np.inf)
    total = 0.0
    passes = 0
    moved = 0.0
    for _ in range(max(iters, 1)):
        passes += 1
        moved = 0.0
        # axis 1 (pairs along y, ds = dy), then axis 0 (pairs along x, ds = dx); even then odd pairs
        for start in range(2):
            for i in range(nx):
                for j in range(start, ny - 1, 2):
                    moved += _collapse_pair(z, S, h, i, j, i, j + 1, dy, all_pairs, c, gamma, phi_mat, phi_dry,
                                            phi_wet, hsw, h_dry, p, fs_trig, fs_target, minfs)
        for start in range(2):
            for i in range(start, nx - 1, 2):
                for j in range(ny):
                    moved += _collapse_pair(z, S, h, i, j, i + 1, j, dx, all_pairs, c, gamma, phi_mat, phi_dry,
                                            phi_wet, hsw, h_dry, p, fs_trig, fs_target, minfs)
        total += moved
        if moved < 1e-9:
            break
    return total, minfs[0], passes, moved >= 1e-9


def _fast_check_and_collapse(self, mesh):
    cfg, m = self.cfg, self.mat
    mode = cfg.collapse_mode
    if mode == "bank_wedge":                    # V3.4 F5: whole-bank Culmann is NumPy only (failures are rare events)
        if m.cohesion > 0.0:
            return _ORIG["collapse"](self, mesh)
        mode = "all_pairs"
    if mode not in ("unsupported", "all_pairs"):
        raise ValueError("collapse_mode must be 'unsupported', 'all_pairs' or 'bank_wedge'")
    self.last_min_fs = float("inf")
    phi_dry = np.deg2rad(m.phi if cfg.collapse_phi_dry is None else cfg.collapse_phi_dry)
    phi_wet = np.deg2rad(m.phi if cfg.collapse_phi_wet is None else cfg.collapse_phi_wet)
    hsw = cfg.h_dry if cfg.collapse_hswitch is None else cfg.collapse_hswitch
    if not (mesh.z_b.flags.c_contiguous and mesh.S.flags.c_contiguous):
        mesh.z_b = np.ascontiguousarray(mesh.z_b)
        mesh.S = np.ascontiguousarray(mesh.S)
    limit = self.pass_limit()
    total, minfs, passes, moving = _collapse(mesh.z_b, mesh.S, np.ascontiguousarray(mesh.h, dtype=np.float64),
                             float(mesh.dx), float(mesh.dy), mode == "all_pairs", float(m.cohesion),
                             float(self.gamma), float(np.deg2rad(m.phi)), float(phi_dry), float(phi_wet), float(hsw),
                             float(cfg.h_dry), float(m.porosity), float(max(cfg.bank_fs_trigger, 1e-6)),
                             float(max(cfg.bank_fs_target, 1e-6)), int(limit))
    self.last_min_fs = min(self.last_min_fs, float(minfs))
    self.record_passes(int(passes), bool(moving), limit)
    return total * mesh.dx * mesh.dy


# ----------------------------------------------------------------------------------------------------------------
# C1 scarp headcut (Headcut._migrate_scarp)
# ----------------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _hc_rate(q, H, method, C, A0, has_max, max_rate, retard, sites_thr, sites_coef):
    if method == HC_ENERGY:
        r = C * np.cbrt(q * H)
    elif method == HC_TEMPLE:
        r = C * np.cbrt(q) * np.sqrt(H)
    elif method == HC_SITES_KH:
        attack = np.cbrt(max(q, 0.0) * 10.7639104167 * max(H, 0.0) * 3.280839895)
        r = sites_coef * max(attack - sites_thr, 0.0) * 0.3048 / 3600.0
    else:
        r = C * max(np.cbrt(q * H) - A0, 0.0)
    if has_max:
        r = min(r, max(max_rate, 0.0))
    return r * max(retard, 0.0)


@njit(cache=True)
def _scarp(z, h, qx, qy, S, zfl, dx, dy, dt, seg_slope, min_slope, min_height, h_dry, p, floor_on,
           method, C, A0, has_max, max_rate, retard, sites_thr, sites_coef, free_only):
    nx, ny = z.shape
    nmax = 4 * nx * ny
    rti = np.empty(nmax, np.int64)
    rtj = np.empty(nmax, np.int64)
    rri = np.empty(nmax, np.int64)
    rrj = np.empty(nmax, np.int64)
    ramt = np.empty(nmax)
    nrec = 0
    req = np.zeros((nx, ny))
    for dirn in range(4):
        axis = 0 if dirn < 2 else 1
        sign = 1 if dirn % 2 == 0 else -1
        ds = dx if axis == 0 else dy
        n_line = nx if axis == 0 else ny
        n_col = ny if axis == 0 else nx
        dsafe = max(ds, 1e-12)
        csum = np.empty(n_line)
        dline = np.empty(n_line)
        segl = np.zeros(n_line, np.bool_)
        for col in range(n_col):
            # oriented line k = 0..n_line-1 -> mesh cell
            csum[0] = 0.0
            for k in range(n_line - 1):
                k0 = k if sign > 0 else n_line - 1 - k
                k1 = k + 1 if sign > 0 else n_line - 2 - k
                if axis == 0:
                    dk = z[k0, col] - z[k1, col]
                else:
                    dk = z[col, k0] - z[col, k1]
                dline[k] = dk
                sg = dk / dsafe >= seg_slope
                segl[k] = sg
                csum[k + 1] = csum[k] + (dk if sg else 0.0)
            k = 0
            while k < n_line - 1:
                if not segl[k]:
                    k += 1
                    continue
                s = k
                while k < n_line - 1 and segl[k]:
                    k += 1
                e = k - 1
                Hs = csum[e + 1] - csum[s]
                Ls = (e - s + 1) * ds
                top = s
                foot = e + 1
                t0 = top if sign > 0 else n_line - 1 - top
                f0 = foot if sign > 0 else n_line - 1 - foot
                if axis == 0:
                    q = qx[t0, col] * sign
                    hfoot = h[f0, col]
                    zfoot = z[f0, col]
                    ztop = z[t0, col]
                else:
                    q = qy[col, t0] * sign
                    hfoot = h[col, f0]
                    zfoot = z[col, f0]
                    ztop = z[col, t0]
                if not ((Hs / Ls >= min_slope) and (Hs >= min_height) and (hfoot > h_dry) and (q > 1e-6)):
                    continue
                if free_only and not (zfoot + hfoot < ztop):     # V3.4 F2: free overfall only
                    continue
                R = _hc_rate(q, Hs, method, C, A0, has_max, max_rate, retard, sites_thr, sites_coef)
                f = min(R * dt / dsafe, 1.0)
                for cell in range(top, e + 1):
                    amt = f * dline[cell]
                    t_o = cell if sign > 0 else n_line - 1 - cell
                    r_o = cell + 1 if sign > 0 else n_line - 1 - (cell + 1)
                    if axis == 0:
                        ti, tj, ri, rj = t_o, col, r_o, col
                    else:
                        ti, tj, ri, rj = col, t_o, col, r_o
                    rti[nrec] = ti
                    rtj[nrec] = tj
                    rri[nrec] = ri
                    rrj[nrec] = rj
                    ramt[nrec] = amt
                    nrec += 1
                    req[ti, tj] += amt
    if nrec == 0:
        return 0.0, -1
    total = 0.0
    hi = nx + ny
    for r in range(nrec):
        ti = rti[r]
        tj = rtj[r]
        if floor_on:
            avail = max(z[ti, tj] - zfl[ti, tj], 0.0)
            # scale uses the bed before any of this step's headcut lowering (as in NumPy)
            sc = min(1.0, avail / max(req[ti, tj], 1e-12))
        else:
            sc = 1.0
        ramt[r] = ramt[r] * sc
        if ti < hi:
            hi = ti
    for r in range(nrec):
        a = ramt[r]
        z[rti[r], rtj[r]] += -a
        S[rri[r], rrj[r]] += (1.0 - p) * a
        total += a
    return total, hi


def _fast_migrate_scarp(self, mesh, qx, qy, dt):
    cfg, mat = self.cfg, self.mat
    method = cfg.headcut_method.lower()
    sites_thr = sites_coef = 0.0
    if method == "energy":
        code = HC_ENERGY
    elif method == "temple":
        code = HC_TEMPLE
    elif method == "sites":
        if mat.headcut_Kh is not None:
            code = HC_SITES_KH
            kh = max(float(mat.headcut_Kh), 1e-9)
            sites_thr = 0.0 if kh < 0.01 else (1.0 / 3.0) * np.exp(-((np.log(kh) - 3.23) ** 2) / 189.0)
            sites_coef = -0.79 * np.log(kh) + 3.04 if kh < 18.2 else 0.75
        else:
            code = HC_SITES_A0
    else:
        raise ValueError("headcut_method must be 'energy', 'temple', or 'sites'")
    if not (mesh.z_b.flags.c_contiguous and mesh.S.flags.c_contiguous):
        mesh.z_b = np.ascontiguousarray(mesh.z_b)
        mesh.S = np.ascontiguousarray(mesh.S)
    f64 = np.float64
    zfl = np.ascontiguousarray(mesh.z_floor, dtype=f64) if cfg.z_floor_enabled else np.zeros((1, 1))
    total, hi = _scarp(mesh.z_b, np.ascontiguousarray(mesh.h, dtype=f64), np.ascontiguousarray(qx, dtype=f64),
                       np.ascontiguousarray(qy, dtype=f64), mesh.S, zfl, float(mesh.dx), float(mesh.dy), float(dt),
                       float(cfg.headcut_seg_slope), float(cfg.headcut_min_slope), float(cfg.headcut_min_height),
                       float(cfg.h_dry), float(mat.porosity), bool(cfg.z_floor_enabled), code,
                       float(cfg.headcut_C), float(cfg.headcut_threshold_A0), cfg.headcut_max_rate is not None,
                       float(cfg.headcut_max_rate or 0.0), float(cfg.headcut_retardation), float(sites_thr),
                       float(sites_coef), getattr(cfg, "headcut_overfall", "any") == "free")
    if hi < 0:
        return 0.0
    mesh.headcut_i = int(hi)
    return total * mesh.dx * mesh.dy


# ----------------------------------------------------------------------------------------------------------------
# F7 scarp volume retreat (Headcut._migrate_scarp_volume)
# ----------------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _oz(z, idx, sign, n_line, axis, col):
    """Read z at oriented index — inlined helper for Numba."""
    m = idx if sign > 0 else n_line - 1 - idx
    if axis == 0:
        return z[m, col]
    return z[col, m]


@njit(cache=True)
def _scarp_volume_kernel(z, h, qx, qy, S, dx, dy, dt, seg_slope, face_slope, min_height, h_dry, p,
                         method, C, A0, has_max, max_rate, retard, sites_thr, sites_coef, free_only):
    """F7 volume-based scarp retreat — Numba kernel matching _migrate_scarp_volume."""
    nx, ny = z.shape
    total = 0.0
    min_hi = nx + ny
    for dirn in range(4):
        axis = 0 if dirn < 2 else 1
        sign = 1 if dirn % 2 == 0 else -1
        ds = dx if axis == 0 else dy
        n_line = nx if axis == 0 else ny
        n_col = ny if axis == 0 else nx
        dsafe = max(ds, 1e-12)
        for col in range(n_col):
            # build oriented drop and seg arrays
            dline = np.empty(n_line - 1)
            segl = np.zeros(n_line - 1, np.bool_)
            for kk in range(n_line - 1):
                k0 = kk if sign > 0 else n_line - 1 - kk
                k1 = kk + 1 if sign > 0 else n_line - 2 - kk
                if axis == 0:
                    dk = z[k0, col] - z[k1, col]
                else:
                    dk = z[col, k0] - z[col, k1]
                dline[kk] = dk
                segl[kk] = dk / dsafe >= seg_slope
            # find runs
            kk = 0
            while kk < n_line - 1:
                if not segl[kk]:
                    kk += 1
                    continue
                s = kk
                while kk < n_line - 1 and segl[kk]:
                    kk += 1
                e = kk - 1
                # --- Change A: local scarp detection ---
                hc_top = -1
                ext_foot = -1
                z_crest = 0.0
                H_full = 0.0
                ge = -1
                j = s
                while j <= e:
                    if dline[j] / dsafe >= face_slope:
                        gs = j
                        while j <= e and dline[j] / dsafe >= face_slope:
                            j += 1
                        ge = j - 1
                        hc_top = gs
                        break
                    j += 1
                if hc_top >= 0:
                    zt = _oz(z, hc_top, sign, n_line, axis, col)
                    ztp = _oz(z, hc_top - 1, sign, n_line, axis, col) if hc_top > 0 else zt
                    z_crest = max(zt, ztp)
                    ext_foot = ge + 1
                    # extend via cumulative slope
                    while ext_foot < e + 1 and ext_foot + 1 < n_line:
                        cum_drop = z_crest - _oz(z, ext_foot + 1, sign, n_line, axis, col)
                        cum_len = (ext_foot + 1 - hc_top) * dsafe
                        if cum_drop / cum_len >= face_slope:
                            ext_foot += 1
                        else:
                            break
                    H_full = z_crest - _oz(z, ext_foot, sign, n_line, axis, col)
                    # --- Coarse-grid face extension ---
                    if e + 1 > ext_foot and e + 1 < n_line:
                        H_run_base = z_crest - _oz(z, e + 1, sign, n_line, axis, col)
                        n_span = e + 1 - hc_top
                        if H_run_base > H_full and dsafe > 1e-12 and n_span <= H_run_base / dsafe + 2:
                            H_full = H_run_base
                            ext_foot = e + 1
                else:
                    # fallback: whole run
                    hc_top = s
                    ext_foot = e + 1
                    if ext_foot >= n_line:
                        continue
                    zs = _oz(z, s, sign, n_line, axis, col)
                    zsp = _oz(z, s - 1, sign, n_line, axis, col) if s > 0 else zs
                    z_crest = max(zs, zsp)
                    z_base_fb = _oz(z, ext_foot, sign, n_line, axis, col)
                    H_run = z_crest - z_base_fb
                    n_drops = e - s + 1
                    max_drops = H_run / dsafe + 2
                    if n_drops > max_drops or H_run <= 0:
                        continue
                    H_full = H_run
                # --- Walk to true base ---
                true_foot = ext_foot
                while true_foot + 1 < n_line:
                    z_curr = _oz(z, true_foot, sign, n_line, axis, col)
                    z_next = _oz(z, true_foot + 1, sign, n_line, axis, col)
                    if z_next >= z_curr - 1e-9:
                        break
                    if (z_curr - z_next) / dsafe >= seg_slope:
                        break
                    true_foot += 1
                H_walk = z_crest - _oz(z, true_foot, sign, n_line, axis, col)
                if H_walk > H_full:
                    H_full = H_walk
                    ext_foot = true_foot
                # --- Activation ---
                if H_full < min_height:
                    continue
                ef_m = ext_foot if sign > 0 else n_line - 1 - ext_foot
                ht_m = hc_top if sign > 0 else n_line - 1 - hc_top
                if axis == 0:
                    hfoot = h[ef_m, col]
                    q_val = qx[ht_m, col] * sign
                    zfoot_val = z[ef_m, col]
                    ztop_val = z[ht_m, col]
                else:
                    hfoot = h[col, ef_m]
                    q_val = qy[col, ht_m] * sign
                    zfoot_val = z[col, ef_m]
                    ztop_val = z[col, ht_m]
                if not (hfoot > h_dry and q_val > 1e-6):
                    continue
                if free_only and not (zfoot_val + hfoot < ztop_val):
                    continue
                # --- Change B: volume-based retreat ---
                R = _hc_rate(q_val, H_full, method, C, A0, has_max, max_rate, retard, sites_thr, sites_coef)
                z_base_vol = _oz(z, ext_foot, sign, n_line, axis, col)
                # vol_target is m²/m-width; convert to height for cells of width ds
                vol_target = R * dt * H_full
                h_target = vol_target / dsafe
                brink = ext_foot - 1
                h_remaining = h_target
                while h_remaining > 1e-15 and brink >= hc_top:
                    cell_z = _oz(z, brink, sign, n_line, axis, col)
                    removable = cell_z - z_base_vol
                    if removable <= 0:
                        brink -= 1
                        continue
                    take = min(removable, h_remaining)
                    brink_m = brink if sign > 0 else n_line - 1 - brink
                    if axis == 0:
                        z[brink_m, col] -= take
                    else:
                        z[col, brink_m] -= take
                    h_remaining -= take
                    if cell_z - take <= z_base_vol + 1e-9:
                        brink -= 1
                    else:
                        break
                vol_removed = (h_target - h_remaining) * dsafe  # back to m²
                deposit = vol_removed / dsafe  # height for the foot cell
                # Deposit at foot
                if ext_foot < n_line:
                    if axis == 0:
                        if hfoot > h_dry:
                            S[ef_m, col] += (1.0 - p) * deposit
                        else:
                            z[ef_m, col] += deposit
                    else:
                        if hfoot > h_dry:
                            S[col, ef_m] += (1.0 - p) * deposit
                        else:
                            z[col, ef_m] += deposit
                dw = dy if axis == 0 else dx  # cross-stream cell width
                total += vol_removed * dw  # m² * m = m³
                hi = ht_m if axis == 0 else col
                if hi < min_hi:
                    min_hi = hi
    return total, min_hi


def _fast_migrate_scarp_volume(self, mesh, qx, qy, dt):
    cfg, mat = self.cfg, self.mat
    method = cfg.headcut_method.lower()
    sites_thr = sites_coef = 0.0
    if method == "energy":
        code = HC_ENERGY
    elif method == "temple":
        code = HC_TEMPLE
    elif method == "sites":
        if mat.headcut_Kh is not None:
            code = HC_SITES_KH
            kh = max(float(mat.headcut_Kh), 1e-9)
            sites_thr = 0.0 if kh < 0.01 else (1.0 / 3.0) * np.exp(-((np.log(kh) - 3.23) ** 2) / 189.0)
            sites_coef = -0.79 * np.log(kh) + 3.04 if kh < 18.2 else 0.75
        else:
            code = HC_SITES_A0
    else:
        raise ValueError("headcut_method must be 'energy', 'temple', or 'sites'")
    if not (mesh.z_b.flags.c_contiguous and mesh.S.flags.c_contiguous):
        mesh.z_b = np.ascontiguousarray(mesh.z_b)
        mesh.S = np.ascontiguousarray(mesh.S)
    f64 = np.float64
    total, hi = _scarp_volume_kernel(
        mesh.z_b, np.ascontiguousarray(mesh.h, dtype=f64),
        np.ascontiguousarray(qx, dtype=f64), np.ascontiguousarray(qy, dtype=f64),
        mesh.S, float(mesh.dx), float(mesh.dy), float(dt),
        float(cfg.headcut_seg_slope), float(cfg.headcut_face_slope),
        float(cfg.headcut_min_height), float(cfg.h_dry), float(mat.porosity),
        code, float(cfg.headcut_C), float(cfg.headcut_threshold_A0),
        cfg.headcut_max_rate is not None, float(cfg.headcut_max_rate or 0.0),
        float(cfg.headcut_retardation), float(sites_thr), float(sites_coef),
        getattr(cfg, "headcut_overfall", "any") == "free")
    if hi < 0 or hi >= mesh.z_b.shape[0] + mesh.z_b.shape[1]:
        return 0.0
    mesh.headcut_i = int(hi)
    return total


# ----------------------------------------------------------------------------------------------------------------
# lateral erosion (LateralErosion._apply_axis, lateral_model 'critical_shear')
# ----------------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _lat_pair(z, S, h, tau, zf, ia, ja, ib, jb, ds, dt, h_dry, tan_phi, tau_c_bank, nsf, kd, n_exp, p):
    zA = z[ia, ja]
    zB = z[ib, jb]
    hA = h[ia, ja]
    drop = zB - zA
    if not (hA > h_dry and drop > 1e-6):
        return 0.0
    tan_a = drop / ds
    K = np.cos(np.arctan(tan_a)) * np.sqrt(max(1.0 - (tan_a / tan_phi) ** 2, 0.0))
    tau_cb = tau_c_bank * K
    R = kd * max(tau[ia, ja] * nsf - tau_cb, 0.0) ** n_exp
    hw = min(drop, hA)
    dzB = R * hw * dt / ds
    dzB = min(dzB, max(drop, 0.0))
    dzB = min(dzB, max(zB - zf[ib, jb], 0.0))
    z[ib, jb] = zB - dzB
    S[ia, ja] += (1.0 - p) * dzB
    return dzB


@njit(cache=True)
def _lateral(z, S, h, tau, zf, axis, ds, dt, h_dry, tan_phi, tau_c_bank, nsf, kd, n_exp, p):
    nx, ny = z.shape
    n = ny if axis == 1 else nx
    m = nx if axis == 1 else ny
    tot1 = 0.0
    tot2 = 0.0
    # sweep 1: A = k, B = k+1. NumPy evaluates the sweep on the bed before it; pair k lowers cell k+1, which is
    # the A cell of pair k+1, so pairs are visited in descending k (each pair then reads unmodified cells).
    for c in range(m):
        for k in range(n - 2, -1, -1):
            if axis == 1:
                tot1 += _lat_pair(z, S, h, tau, zf, c, k, c, k + 1, ds, dt, h_dry, tan_phi, tau_c_bank, nsf, kd,
                                  n_exp, p)
            else:
                tot1 += _lat_pair(z, S, h, tau, zf, k, c, k + 1, c, ds, dt, h_dry, tan_phi, tau_c_bank, nsf, kd,
                                  n_exp, p)
    # sweep 2: A = k+1, B = k; pair k lowers cell k, the A cell of pair k-1 -> ascending k
    for c in range(m):
        for k in range(n - 1):
            if axis == 1:
                tot2 += _lat_pair(z, S, h, tau, zf, c, k + 1, c, k, ds, dt, h_dry, tan_phi, tau_c_bank, nsf, kd,
                                  n_exp, p)
            else:
                tot2 += _lat_pair(z, S, h, tau, zf, k + 1, c, k, c, ds, dt, h_dry, tan_phi, tau_c_bank, nsf, kd,
                                  n_exp, p)
    return tot1, tot2


def _fast_apply_axis(self, mesh, tau, dt, axis):
    m, cfg = self.mat, self.cfg
    if cfg.lateral_model == "force_balance":
        return _ORIG["lateral"](self, mesh, tau, dt, axis)
    if not (mesh.z_b.flags.c_contiguous and mesh.S.flags.c_contiguous):
        mesh.z_b = np.ascontiguousarray(mesh.z_b)
        mesh.S = np.ascontiguousarray(mesh.S)
    f64 = np.float64
    tau_c_bank = (m.tau_c if cfg.bank_tau_c is None else cfg.bank_tau_c) * max(cfg.bank_threshold_factor, 0.0)
    n_bank = m.n_exp if cfg.bank_n_exp is None else cfg.bank_n_exp
    kd_bank = m.kd if cfg.bank_kd is None else cfg.bank_kd
    ds = mesh.dy if axis == 1 else mesh.dx
    t1, t2 = _lateral(mesh.z_b, mesh.S, np.ascontiguousarray(mesh.h, dtype=f64), np.ascontiguousarray(tau, dtype=f64),
                      np.ascontiguousarray(mesh.z_floor, dtype=f64), int(axis), float(ds), float(dt),
                      float(cfg.h_dry), float(np.tan(np.deg2rad(m.phi))), float(tau_c_bank),
                      float(max(cfg.near_bank_shear_factor, 0.0)), float(kd_bank), float(n_bank),
                      float(m.porosity))
    return t1 * mesh.dx * mesh.dy + t2 * mesh.dx * mesh.dy


# ----------------------------------------------------------------------------------------------------------------
# sediment advection (Morphology._advect + _limit_outflow) -- arithmetic only, bit-identical
# ----------------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _advect_k(S, h, qx, qy, dt, dx, dy, h_dry, limit, Fx, Fy, Snew, face, qfx, qfy):
    nx, ny = S.shape
    c = np.empty((nx, ny))
    for i in range(nx):
        for j in range(ny):
            c[i, j] = S[i, j] / max(h[i, j], h_dry) if h[i, j] > h_dry else 0.0
    if face:                                    # V3.4 F6: the flow solver's own face discharges
        for j in range(ny):
            q0 = qfx[0, j]
            Fx[0, j] = q0 * (c[0, j] if q0 < 0 else 0.0)
            for i in range(1, nx):
                qf = qfx[i, j]
                Fx[i, j] = qf * (c[i - 1, j] if qf > 0 else c[i, j])
            qn = qfx[nx, j]
            Fx[nx, j] = qn * (c[nx - 1, j] if qn > 0 else 0.0)
        for i in range(nx):
            Fy[i, 0] = qfy[i, 0] * 0.0
            for j in range(1, ny):
                rf = qfy[i, j]
                Fy[i, j] = rf * (c[i, j - 1] if rf > 0 else c[i, j])
            Fy[i, ny] = qfy[i, ny] * 0.0
    else:
        for j in range(ny):
            q0 = qx[0, j]
            Fx[0, j] = q0 * (c[0, j] if q0 < 0 else 0.0)
            for i in range(1, nx):
                qf = 0.5 * (qx[i - 1, j] + qx[i, j])
                Fx[i, j] = qf * (c[i - 1, j] if qf > 0 else c[i, j])
            qn = qx[nx - 1, j]
            Fx[nx, j] = qn * (c[nx - 1, j] if qn > 0 else 0.0)
        for i in range(nx):
            Fy[i, 0] = 0.0 * 0.0
            for j in range(1, ny):
                rf = 0.5 * (qy[i, j - 1] + qy[i, j])
                Fy[i, j] = rf * (c[i, j - 1] if rf > 0 else c[i, j])
            Fy[i, ny] = 0.0 * 0.0
    if limit:
        a = dt / dx
        b = dt / dy
        f = np.empty((nx, ny))
        for i in range(nx):
            for j in range(ny):
                Sp = max(S[i, j], 0.0)
                out = (a * (max(Fx[i + 1, j], 0.0) + max(-Fx[i, j], 0.0))
                       + b * (max(Fy[i, j + 1], 0.0) + max(-Fy[i, j], 0.0)))
                f[i, j] = Sp / max(out, 1e-300) if out > Sp else 1.0
        for j in range(ny):
            Fx[0, j] = Fx[0, j] * f[0, j]
            for i in range(1, nx):
                Fx[i, j] = Fx[i, j] * (f[i - 1, j] if Fx[i, j] > 0 else f[i, j])
            Fx[nx, j] = Fx[nx, j] * f[nx - 1, j]
        for i in range(nx):
            Fy[i, 0] = Fy[i, 0] * 1.0
            for j in range(1, ny):
                Fy[i, j] = Fy[i, j] * (f[i, j - 1] if Fy[i, j] > 0 else f[i, j])
            Fy[i, ny] = Fy[i, ny] * 1.0
    a = dt / dx
    b = dt / dy
    for i in range(nx):
        for j in range(ny):
            Snew[i, j] = S[i, j] - a * (Fx[i + 1, j] - Fx[i, j]) - b * (Fy[i, j + 1] - Fy[i, j])


_NOFACE = np.zeros((1, 1))


def _fast_advect(self, mesh, h, qx, qy, dt):
    cfg = self.cfg
    nx, ny = mesh.nx, mesh.ny
    f64 = np.float64
    Fx = np.empty((nx + 1, ny))
    Fy = np.empty((nx, ny + 1))
    Snew = np.empty((nx, ny))
    mode = cfg.sediment_face_flux
    if mode == "hydro":
        qfx, qfy = self._face_discharge(mesh)
        qfx, qfy = np.ascontiguousarray(qfx, dtype=f64), np.ascontiguousarray(qfy, dtype=f64)
    elif mode == "centred":
        qfx, qfy = _NOFACE, _NOFACE
    else:
        raise ValueError("sediment_face_flux must be 'centred' or 'hydro'")
    _advect_k(np.ascontiguousarray(mesh.S, dtype=f64), np.ascontiguousarray(h, dtype=f64),
              np.ascontiguousarray(qx, dtype=f64), np.ascontiguousarray(qy, dtype=f64), float(dt), float(mesh.dx),
              float(mesh.dy), float(cfg.h_dry), bool(cfg.positivity_fix and not cfg.legacy_negative_S), Fx, Fy, Snew,
              mode == "hydro", qfx, qfy)
    mesh.S = Snew
    return float((Fx[-1].sum() - Fx[0].sum()) * mesh.dy * dt)


# ----------------------------------------------------------------------------------------------------------------

def enable() -> bool:
    global _ENABLED
    if not HAVE_NUMBA:
        return False
    E.BankStability.check_and_collapse = _fast_check_and_collapse
    E.Headcut._migrate_scarp = _fast_migrate_scarp
    E.Headcut._migrate_scarp_volume = _fast_migrate_scarp_volume
    E.LateralErosion._apply_axis = _fast_apply_axis
    E.Morphology._advect = _fast_advect
    _ENABLED = True
    return True


def disable() -> None:
    global _ENABLED
    E.BankStability.check_and_collapse = _ORIG["collapse"]
    E.Headcut._migrate_scarp = _ORIG["scarp"]
    E.Headcut._migrate_scarp_volume = _ORIG["scarp_volume"]
    E.LateralErosion._apply_axis = _ORIG["lateral"]
    E.Morphology._advect = _ORIG["advect"]
    _ENABLED = False
