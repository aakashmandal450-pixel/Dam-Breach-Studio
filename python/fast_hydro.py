"""Numba backend for the 2-D shallow-water step of breach_engine_2d_v3_2 (Hydrodynamics.step).

Opt-in, engine file unchanged:

    import fast_hydro
    fast_hydro.enable()          # patches breach_engine_2d_v3_2.Hydrodynamics.step in this process
    fast_hydro.disable()         # restores the NumPy step

What is compiled: ghost-cell fill and boundary states, CFL wave speeds, first- or second-order (minmod MUSCL)
reconstruction, hydrostatic reconstruction (Audusse et al. 2004) + HLL fluxes on all x and y faces, the conservative
update, wet/dry velocities and semi-implicit Chezy or Manning friction. Each expression follows the NumPy code term by
term and in the same order, so results agree to round-off (exact in most steps).

Also compiled: bed_shear. Cached (exact): UltimateBreachEngine.breach_development and channelization_index, which
depend only on the bed and were recomputed every hydraulic step for the history record.

Left in NumPy, unchanged: the reservoir-face positivity limit, Q_left / Q_right sums and the speed-clip bookkeeping.
Steps with an incident lake-wave boundary (wave_boundary given) fall back to the NumPy step.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np

import breach_engine_2d_v3_2 as E

try:
    import numba as _nb
    from numba import njit
    HAVE_NUMBA = True
except Exception:          # pragma: no cover - reported by enable()
    HAVE_NUMBA = False

    def njit(*a, **k):     # type: ignore
        def deco(f):
            return f
        return deco if not (a and callable(a[0])) else a[0]

_ORIG_STEP = E.Hydrodynamics.step
_ORIG_SHEAR = E.Hydrodynamics.bed_shear
_ORIG_BD = E.UltimateBreachEngine.breach_development
_ORIG_CI = E.UltimateBreachEngine.channelization_index
_ENABLED = False

DS_TRANSMISSIVE, DS_WALL, DS_OUTFALL = 0, 1, 2
FR_CHEZY, FR_MANNING = 0, 1


# ----------------------------------------------------------------------------------------------------------------
# kernels
# ----------------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _fill_ghosts(h, u, v, z, res_level, ds_mode, hP, uP, vP, zP):
    nx, ny = h.shape
    # np.pad(mode="edge")
    for i in range(nx + 2):
        ii = min(max(i - 1, 0), nx - 1)
        for j in range(ny + 2):
            jj = min(max(j - 1, 0), ny - 1)
            hP[i, j] = h[ii, jj]
            uP[i, j] = u[ii, jj]
            vP[i, j] = v[ii, jj]
            zP[i, j] = z[ii, jj]
    # left: reservoir stage
    for j in range(ny + 2):
        zP[0, j] = zP[1, j]
        hP[0, j] = max(res_level - zP[0, j], 0.0)
        uP[0, j] = 0.0
        vP[0, j] = 0.0
    # y walls reflective
    for i in range(nx + 2):
        vP[i, 0] = -vP[i, 1]
        vP[i, ny + 1] = -vP[i, ny]
    if ds_mode == DS_WALL:
        for j in range(ny + 2):
            uP[nx + 1, j] = -uP[nx, j]
    elif ds_mode == DS_OUTFALL:
        for j in range(ny + 2):
            hP[nx + 1, j] = 0.0


@njit(cache=True)
def _max_speeds(h, u, v, hP, uP, vP, g, interior_only):
    smx = -np.inf
    smy = -np.inf
    if interior_only:
        nx, ny = h.shape
        for i in range(nx):
            for j in range(ny):
                c = math.sqrt(g * h[i, j])
                a = abs(u[i, j]) + c
                b = abs(v[i, j]) + c
                if a > smx:
                    smx = a
                if b > smy:
                    smy = b
    else:
        nx2, ny2 = hP.shape
        for i in range(nx2):
            for j in range(ny2):
                c = math.sqrt(g * hP[i, j])
                a = abs(uP[i, j]) + c
                b = abs(vP[i, j]) + c
                if a > smx:
                    smx = a
                if b > smy:
                    smy = b
    return smx, smy


@njit(cache=True)
def _sign(x):
    if x > 0.0:
        return 1.0
    if x < 0.0:
        return -1.0
    return 0.0


@njit(cache=True)
def _minmod3(a, b, c):
    sa, sb, sc = _sign(a), _sign(b), _sign(c)
    if sa == sb and sb == sc:
        return sa * min(abs(a), min(abs(b), abs(c)))
    return 0.0


@njit(cache=True)
def _slopes(aP, axis, out):
    """_limited_slope for a padded field (out preset to 0)."""
    n0, n1 = aP.shape
    if axis == 0:
        for i in range(1, n0 - 1):
            for j in range(n1):
                out[i, j] = _minmod3(aP[i, j] - aP[i - 1, j], 0.5 * (aP[i + 1, j] - aP[i - 1, j]),
                                     aP[i + 1, j] - aP[i, j])
        for j in range(n1):
            out[1, j] = 0.0
            out[n0 - 2, j] = 0.0
    else:
        for i in range(n0):
            for j in range(1, n1 - 1):
                out[i, j] = _minmod3(aP[i, j] - aP[i, j - 1], 0.5 * (aP[i, j + 1] - aP[i, j - 1]),
                                     aP[i, j + 1] - aP[i, j])
        for i in range(n0):
            out[i, 1] = 0.0
            out[i, n1 - 2] = 0.0


@njit(cache=True)
def _face(hL, unL, utL, zL, hR, unR, utR, zR, hcL, hcR, g):
    """Hydrostatic reconstruction + HLL at one face. Returns (Fh, FnL, FnR, Ft) as in Hydrodynamics._face_flux."""
    zf = max(zL, zR)
    hLs = max(hL + zL - zf, 0.0)
    hRs = max(hR + zR - zf, 0.0)
    # _hll_normal
    cL = math.sqrt(g * hLs)
    cR = math.sqrt(g * hRs)
    sL = min(unL - cL, unR - cR)
    sR = max(unL + cL, unR + cR)
    dryL = hLs <= 1e-12
    dryR = hRs <= 1e-12
    if dryL:
        sL = unR - 2 * cR
        sR = unR + cR
    if dryR:
        sL = unL - cL
        sR = unL + 2 * cL
    FLh = hLs * unL
    FRh = hRs * unR
    FLn = hLs * unL ** 2 + 0.5 * g * hLs ** 2
    FRn = hRs * unR ** 2 + 0.5 * g * hRs ** 2
    FLt = hLs * unL * utL
    FRt = hRs * unR * utR
    den = sR - sL
    if abs(den) < 1e-12:
        den = 1.0
    if sL >= 0:
        Fh, Fn, Ft = FLh, FLn, FLt
    elif sR <= 0:
        Fh, Fn, Ft = FRh, FRn, FRt
    else:
        Fh = (sR * FLh - sL * FRh + sL * sR * (hRs - hLs)) / den
        Fn = (sR * FLn - sL * FRn + sL * sR * (hRs * unR - hLs * unL)) / den
        Ft = (sR * FLt - sL * FRt + sL * sR * (hRs * utR - hLs * utL)) / den
    FnL = Fn + 0.5 * g * (hcL ** 2 - hLs ** 2)
    FnR = Fn + 0.5 * g * (hcR ** 2 - hRs ** 2)
    return Fh, FnL, FnR, Ft


@njit(cache=True)
def _fluxes(hP, uP, vP, zP, g, order, Fh_x, FnL_x, FnR_x, Ft_x, Gh_y, GnL_y, GnR_y, Gt_y,
            s_eta, s_z, s_u, s_v, etaP):
    nx2, ny2 = hP.shape
    nx, ny = nx2 - 2, ny2 - 2
    for i in range(nx2):
        for j in range(ny2):
            etaP[i, j] = zP[i, j] + hP[i, j]
    # ---- x faces (nx+1, ny): left cell i, right cell i+1 (padded rows), columns 1..ny
    if order == 2:
        s_eta[:] = 0.0; s_z[:] = 0.0; s_u[:] = 0.0; s_v[:] = 0.0
        _slopes(etaP, 0, s_eta); _slopes(zP, 0, s_z); _slopes(uP, 0, s_u); _slopes(vP, 0, s_v)
    for f in range(nx + 1):
        for j in range(ny):
            a, b, jj = f, f + 1, j + 1
            if order == 2:
                etaL = etaP[a, jj] + 0.5 * s_eta[a, jj]
                etaR = etaP[b, jj] - 0.5 * s_eta[b, jj]
                zL = zP[a, jj] + 0.5 * s_z[a, jj]
                zR = zP[b, jj] - 0.5 * s_z[b, jj]
                hL = max(etaL - zL, 0.0)
                hR = max(etaR - zR, 0.0)
                uL = uP[a, jj] + 0.5 * s_u[a, jj]
                uR = uP[b, jj] - 0.5 * s_u[b, jj]
                vL = vP[a, jj] + 0.5 * s_v[a, jj]
                vR = vP[b, jj] - 0.5 * s_v[b, jj]
            else:
                hL, hR = hP[a, jj], hP[b, jj]
                zL, zR = zP[a, jj], zP[b, jj]
                uL, uR = uP[a, jj], uP[b, jj]
                vL, vR = vP[a, jj], vP[b, jj]
            r = _face(hL, uL, vL, zL, hR, uR, vR, zR, hP[a, jj], hP[b, jj], g)
            Fh_x[f, j] = r[0]; FnL_x[f, j] = r[1]; FnR_x[f, j] = r[2]; Ft_x[f, j] = r[3]
    # ---- y faces (nx, ny+1): normal = v, tangential = u
    if order == 2:
        s_eta[:] = 0.0; s_z[:] = 0.0; s_u[:] = 0.0; s_v[:] = 0.0
        _slopes(etaP, 1, s_eta); _slopes(zP, 1, s_z); _slopes(uP, 1, s_u); _slopes(vP, 1, s_v)
    for i in range(nx):
        for f in range(ny + 1):
            ii, a, b = i + 1, f, f + 1
            if order == 2:
                etaL = etaP[ii, a] + 0.5 * s_eta[ii, a]
                etaR = etaP[ii, b] - 0.5 * s_eta[ii, b]
                zL = zP[ii, a] + 0.5 * s_z[ii, a]
                zR = zP[ii, b] - 0.5 * s_z[ii, b]
                hL = max(etaL - zL, 0.0)
                hR = max(etaR - zR, 0.0)
                vL = vP[ii, a] + 0.5 * s_v[ii, a]
                vR = vP[ii, b] - 0.5 * s_v[ii, b]
                uL = uP[ii, a] + 0.5 * s_u[ii, a]
                uR = uP[ii, b] - 0.5 * s_u[ii, b]
            else:
                hL, hR = hP[ii, a], hP[ii, b]
                zL, zR = zP[ii, a], zP[ii, b]
                vL, vR = vP[ii, a], vP[ii, b]
                uL, uR = uP[ii, a], uP[ii, b]
            r = _face(hL, vL, uL, zL, hR, vR, uR, zR, hP[ii, a], hP[ii, b], g)
            Gh_y[i, f] = r[0]; GnL_y[i, f] = r[1]; GnR_y[i, f] = r[2]; Gt_y[i, f] = r[3]


@njit(cache=True)
def _update(h, u, v, dt, dx, dy, Fh_x, FnL_x, FnR_x, Ft_x, Gh_y, GnL_y, GnR_y, Gt_y,
            h_dry, fr_mode, chezy_C, manning_n, g, h_new, un, vn, sp):
    nx, ny = h.shape
    cx = dt / dx
    cy = dt / dy
    if fr_mode == FR_CHEZY:
        Cf = g / max(chezy_C, 1e-6) ** 2
        n = 0.0
    else:
        Cf = 0.0
        n = max(manning_n, 0.0)
    for i in range(nx):
        for j in range(ny):
            hu = h[i, j] * u[i, j]
            hv = h[i, j] * v[i, j]
            hn = h[i, j] - cx * (Fh_x[i + 1, j] - Fh_x[i, j]) - cy * (Gh_y[i, j + 1] - Gh_y[i, j])
            hun = hu - cx * (FnL_x[i + 1, j] - FnR_x[i, j]) - cy * (Gt_y[i, j + 1] - Gt_y[i, j])
            hvn = hv - cx * (Ft_x[i + 1, j] - Ft_x[i, j]) - cy * (GnL_y[i, j + 1] - GnR_y[i, j])
            hn = max(hn, 0.0)
            wet = hn > h_dry
            hs = max(hn, h_dry)
            if wet:
                a = hun / hs
                b = hvn / hs
            else:
                a = 0.0
                b = 0.0
            s = math.sqrt(a ** 2 + b ** 2)
            if fr_mode == FR_CHEZY:
                fac = 1.0 / (1.0 + dt * Cf * s / hs)
            else:
                coeff = g * n * n / max(hs, h_dry) ** (4.0 / 3.0)
                fac = 1.0 / (1.0 + dt * coeff * s)
            a = a * fac
            b = b * fac
            h_new[i, j] = hn
            un[i, j] = a
            vn[i, j] = b
            sp[i, j] = math.sqrt(a ** 2 + b ** 2)


@njit(cache=True)
def _bed_shear(h, u, v, h_dry, rho_g, manning, coef, grain, coef_g, tau_out):
    """Hydrodynamics.bed_shear: total shear (Manning: rho g n^2 U^2 / h^(1/3); Chezy: rho g U^2 / C^2),
    optionally capped by grain shear; zero on dry cells. Returns the wet maximum of the TOTAL shear."""
    nx, ny = h.shape
    tmax = 0.0
    first = True
    for i in range(nx):
        for j in range(ny):
            s2 = u[i, j] ** 2 + v[i, j] ** 2
            hs = max(h[i, j], h_dry)
            if manning:
                t = rho_g * coef * s2 / hs ** (1.0 / 3.0)
            else:
                t = rho_g * s2 / coef
            wet = h[i, j] > h_dry
            tw = t if wet else 0.0
            if first or tw > tmax:
                tmax = tw
                first = False
            if grain:
                tg = rho_g * coef_g * s2 / hs ** (1.0 / 3.0)
                t = min(t, tg)
            tau_out[i, j] = t if wet else 0.0
    return tmax


# ----------------------------------------------------------------------------------------------------------------
# patched Hydrodynamics.step
# ----------------------------------------------------------------------------------------------------------------

def _buffers(self, nx, ny):
    key = (nx, ny)
    b = getattr(self, "_fast_buf", None)
    if b is None or b["key"] != key:
        P = lambda: np.zeros((nx + 2, ny + 2))
        b = {"key": key, "hP": P(), "uP": P(), "vP": P(), "zP": P(), "etaP": P(),
             "s_eta": P(), "s_z": P(), "s_u": P(), "s_v": P(),
             "Fx": tuple(np.zeros((nx + 1, ny)) for _ in range(4)),
             "Gy": tuple(np.zeros((nx, ny + 1)) for _ in range(4))}
        self._fast_buf = b
    return b


def _fast_step(self, mesh, res_level: float, dt_limit: float, *, wave_boundary=None, time_s: float = 0.0,
               inflow_available: Optional[Tuple[float, float]] = None):
    if wave_boundary is not None:
        return _ORIG_STEP(self, mesh, res_level, dt_limit, wave_boundary=wave_boundary, time_s=time_s,
                          inflow_available=inflow_available)
    cfg, g = self.cfg, self.cfg.g
    if cfg.spatial_order not in (1, 2):
        raise ValueError("spatial_order must be 1 or 2")
    if cfg.friction_model not in ("chezy", "manning"):
        raise ValueError("friction_model must be 'chezy' or 'manning'")
    nx, ny, dx, dy = mesh.nx, mesh.ny, mesh.dx, mesh.dy
    h = np.ascontiguousarray(mesh.h, dtype=np.float64)
    u = np.ascontiguousarray(mesh.u, dtype=np.float64)
    v = np.ascontiguousarray(mesh.v, dtype=np.float64)
    z = np.ascontiguousarray(mesh.z_b, dtype=np.float64)
    b = _buffers(self, nx, ny)
    hP, uP, vP, zP = b["hP"], b["uP"], b["vP"], b["zP"]
    ds = {"transmissive": DS_TRANSMISSIVE, "wall": DS_WALL, "outfall": DS_OUTFALL}.get(cfg.downstream_boundary,
                                                                                      DS_TRANSMISSIVE)
    _fill_ghosts(h, u, v, z, float(res_level), ds, hP, uP, vP, zP)
    smx, smy = _max_speeds(h, u, v, hP, uP, vP, g, bool(cfg.cfl_interior_only))
    dt = cfg.CFL / (smx / dx + smy / dy + 1e-12)
    dt = min(dt, cfg.dt_max_hydro, dt_limit)

    Fh_x, FnL_x, FnR_x, Ft_x = b["Fx"]
    Gh_y, GnL_y, GnR_y, Gt_y = b["Gy"]
    _fluxes(hP, uP, vP, zP, g, int(cfg.spatial_order), Fh_x, FnL_x, FnR_x, Ft_x, Gh_y, GnL_y, GnR_y, Gt_y,
            b["s_eta"], b["s_z"], b["s_u"], b["s_v"], b["etaP"])

    if inflow_available is not None:     # same code as the NumPy step
        V_avail = max(inflow_available[0] + inflow_available[1] * dt, 0.0)
        into = np.maximum(Fh_x[0, :], 0.0)
        demand = float(np.sum(into) * dy * dt)
        if demand > V_avail:
            f = V_avail / demand
            pos = Fh_x[0, :] > 0.0
            wall_p = 0.5 * g * hP[1, 1:-1] ** 2
            Fh_x[0, :] = np.where(pos, f * Fh_x[0, :], Fh_x[0, :])
            FnR_x[0, :] = np.where(pos, f * FnR_x[0, :] + (1.0 - f) * wall_p, FnR_x[0, :])
            Ft_x[0, :] = np.where(pos, f * Ft_x[0, :], Ft_x[0, :])
            self.inflow_limit_events += 1
    Q_left = float(np.sum(Fh_x[0, :]) * dy)
    Q_right = float(np.sum(Fh_x[-1, :]) * dy)

    h_new, un, vn, sp = (np.empty((nx, ny)) for _ in range(4))
    _update(h, u, v, dt, dx, dy, Fh_x, FnL_x, FnR_x, Ft_x, Gh_y, GnL_y, GnR_y, Gt_y,
            float(cfg.h_dry), FR_CHEZY if cfg.friction_model == "chezy" else FR_MANNING,
            float(cfg.chezy_C), float(cfg.manning_n), g, h_new, un, vn, sp)

    wet = h_new > cfg.h_dry
    clip = (sp > cfg.max_speed) & wet
    if np.any(clip):                     # same bookkeeping as the NumPy step
        self.speed_clip_events += 1
        self.speed_clip_cells += int(np.count_nonzero(clip))
        self.speed_clip_max_uncapped = max(self.speed_clip_max_uncapped, float(np.max(sp[clip])))
        for i, j in np.argwhere(clip):
            key = (int(i), int(j))
            self.speed_clip_locations[key] = self.speed_clip_locations.get(key, 0) + 1
        sc = np.where(clip, cfg.max_speed / (sp + 1e-12), 1.0)
        un, vn = un * sc, vn * sc
    mesh.h, mesh.u, mesh.v = h_new, un, vn
    self.bed_shear(mesh)
    return dt, Q_left, Q_right


def _fast_bed_shear(self, mesh):
    cfg = self.cfg
    manning = cfg.friction_model == "manning"
    if not manning and cfg.friction_model != "chezy":
        return _ORIG_SHEAR(self, mesh)
    grain = cfg.erosion_shear == "grain"
    if grain and (self.grain_n is None or self.grain_n <= 0):
        raise ValueError("erosion_shear='grain' needs a positive grain Manning n")
    # same scalar grouping as the NumPy code: (rho*g)*n**2 and (rho*g)/C**2
    rho_g = self.rho_w * cfg.g
    coef = cfg.manning_n ** 2 if manning else cfg.chezy_C ** 2
    coef_g = self.grain_n ** 2 if grain else 0.0
    h = np.ascontiguousarray(mesh.h, dtype=np.float64)
    tau = np.empty_like(h)
    self.last_tau_total_max = float(_bed_shear(h, np.ascontiguousarray(mesh.u, dtype=np.float64),
                                               np.ascontiguousarray(mesh.v, dtype=np.float64),
                                               float(cfg.h_dry), rho_g, manning, coef, grain, coef_g, tau))
    mesh.tau_b = tau
    return mesh.tau_b


def _cached(self, name, fn):
    """The breach diagnostics depend only on the bed, which changes only at morphology steps: cache them by
    the bed's content (exact; recomputed whenever any bed value differs)."""
    c = self.__dict__.setdefault("_fast_diag_cache", {})
    zb = self.mesh.z_b
    # everything else the two functions read: the settings and reference geometry
    key = (id(self.mesh), float(self.cfg.breach_width_fraction), float(self._dam_height),
           id(self._initial_bed), id(self._crest_rows))
    hit = c.get(name)
    if hit is not None and hit[0] == key and hit[1].shape == zb.shape and np.array_equal(hit[1], zb):
        return hit[2]
    val = fn(self)
    c[name] = (key, zb.copy(), val)
    return val


def _fast_breach_development(self):
    return dict(_cached(self, "bd", _ORIG_BD))


def _fast_channelization_index(self):
    return _cached(self, "ci", _ORIG_CI)


def enable() -> bool:
    """Use the Numba step in this process. Returns False (and keeps NumPy) if numba is not installed."""
    global _ENABLED
    if not HAVE_NUMBA:
        print("fast_hydro: numba is not installed (pip install numba); using the NumPy step", flush=True)
        return False
    E.Hydrodynamics.step = _fast_step
    E.Hydrodynamics.bed_shear = _fast_bed_shear
    E.UltimateBreachEngine.breach_development = _fast_breach_development
    E.UltimateBreachEngine.channelization_index = _fast_channelization_index
    _ENABLED = True
    return True


def disable() -> None:
    global _ENABLED
    E.Hydrodynamics.step = _ORIG_STEP
    E.Hydrodynamics.bed_shear = _ORIG_SHEAR
    E.UltimateBreachEngine.breach_development = _ORIG_BD
    E.UltimateBreachEngine.channelization_index = _ORIG_CI
    _ENABLED = False


def enabled() -> bool:
    return _ENABLED
