"""Lumped 1-D morphodynamic breach model — overtopping core (Theory Parts 1-3).

State: reservoir volume V; breach-top elevation z_b; flat-top bottom width b; downstream edge of the flat
top x_e; downstream-slope bottom width b_down; side slope beta (from bank stability, recomputed each step).

Not yet included (later theory parts): headcut migration (Part 4), piping (Part 5), impulse waves
(Part 6), moraine specifics (Part 7). Time integration is explicit Euler at a fixed step until Part 8.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import hydraulics as hy
from . import sediment as sd
from .geometry import (Dam, bulk_unit_weight, side_area_slope, side_area_top, side_slope_angle)

RHO_S = 2650.0
EPS = 1e-9


@dataclass
class Params:
    dam: Dam
    material_class: str            # "cohesive" | "noncohesive"
    d50: float                     # m
    porosity: float
    phi: float                     # rad
    cohesion: float                # Pa
    n: float                       # Manning n (total)
    kd: float = 0.0                # m3/(N s), already multiplied by f_kd where applicable
    tau_c_coh: float = 0.0         # Pa
    f_t: float = 1.0
    lam: float = 6.0               # adaptation-length factor (6 field, 3 lab)
    n_loc: int = 2
    weir: str = "exact"            # "exact" | "dlbreach"
    rho_s: float = RHO_S


@dataclass
class State:
    t: float
    V: float
    z_b: float
    b: float
    x_e: float
    b_down: float
    beta: float


class Reservoir:
    """Stage-volume table built from the case file (same curve builder as the 2-D engine's cases.py)."""

    def __init__(self, curve: Dict[float, float]):
        lv = np.array(sorted(curve), dtype=float)
        self.levels = lv
        self.vols = np.array([curve[k] for k in lv], dtype=float)

    def level(self, V: float) -> float:
        return float(np.interp(V, self.vols, self.levels))

    def volume(self, z: float) -> float:
        return float(np.interp(z, self.levels, self.vols))


def inflow_fn(spec):
    if isinstance(spec, dict):
        if spec.get("type") != "table":
            raise ValueError(f"unknown inflow type {spec.get('type')!r}")
        pts = np.asarray(spec["points"], dtype=float)
        return lambda t: float(np.interp(t, pts[:, 0], pts[:, 1]))
    q = float(spec or 0.0)
    return lambda t: q


class LumpedBreach:
    def __init__(self, p: Params, res: Reservoir, z_s0: float, notch: Dict, qin, H_dam: float):
        self.p, self.res, self.qin = p, res, qin
        dam = p.dam
        z_b0 = H_dam - notch["depth"]
        b0 = notch.get("bottom_width", 0.0) if notch["shape"] == "trapezoid" else 0.0
        self.gamma_b = bulk_unit_weight(p.porosity, p.rho_s)
        beta0 = side_slope_angle(p.cohesion, self.gamma_b, H_dam - z_b0, p.phi)
        if notch["shape"] == "v" and beta0 >= 0.5 * math.pi - 1e-9:
            b0 = 0.5 * notch["top_width"]     # vertical walls: rectangle of the V-notch's area
        self.s = State(t=0.0, V=res.volume(z_s0), z_b=z_b0, b=max(b0, 0.0), x_e=dam.x_down(z_b0),
                       b_down=max(b0, 0.0), beta=beta0)
        self.z_b0 = z_b0
        self.ws = sd.settling_velocity(p.d50, p.rho_s) if p.material_class == "noncohesive" else 0.0
        self.tau_c_nc = sd.critical_shear_wu(p.d50, p.rho_s)
        # balances
        self.V0 = self.s.V
        self.cum_in = 0.0
        self.cum_out = 0.0
        self.cum_eroded_bulk = 0.0       # sum of eroded bulk volumes (incl. bank-failure wedges)
        self.cum_failure_bulk = 0.0

    # ---- helpers -------------------------------------------------------------------------------------
    @property
    def m(self) -> float:
        return 1.0 / math.tan(self.s.beta)

    def flat_top_length(self) -> float:
        return max(self.s.x_e - self.p.dam.x_up(self.s.z_b), 0.0)

    def top_width_at_crest(self) -> float:
        return self.s.b + 2.0 * self.m * max(self.p.dam.H - self.s.z_b, 0.0)

    def average_width(self) -> float:
        """B = b + m d (1.1)."""
        return self.s.b + self.m * max(self.p.dam.H - self.s.z_b, 0.0)

    # ---- one explicit step ---------------------------------------------------------------------------
    def step(self, dt: float) -> Dict[str, float]:
        p, dam, s = self.p, self.p.dam, self.s
        m = self.m
        z_s = self.res.level(s.V)
        head = z_s - s.z_b
        weir = hy.weir_exact if p.weir == "exact" else hy.weir_dlbreach
        Qb = weir(s.b, m, head) if head > 0.0 else 0.0
        Qov = hy.crest_overflow(max(dam.L_cr - self.top_width_at_crest(), 0.0), z_s - dam.H)
        Qin = self.qin(s.t)
        avail = s.V + Qin * dt                  # positivity: never release more water than is stored
        if (Qb + Qov) * dt > avail > 0.0:
            k = avail / ((Qb + Qov) * dt)
            Qb, Qov = Qb * k, Qov * k
        elif avail <= 0.0:
            Qb = Qov = 0.0

        on_base = s.z_b <= EPS
        L_top = self.flat_top_length()
        out = {"t": s.t, "Q": Qb + Qov, "Qb": Qb, "z_s": z_s, "z_b": s.z_b, "b": s.b, "beta": s.beta,
               "B": self.average_width(), "B_top": self.top_width_at_crest(), "x_e": s.x_e, "L_top": L_top}

        dV_top = dV_slope = 0.0
        if Qb > 0.0:
            # breach top: critical depth (1.10)
            y = hy.critical_depth(s.b, m, head)
            A, R = hy.area(s.b, m, y), hy.hydraulic_radius(s.b, m, y)
            P, Bw = hy.wetted_perimeter(s.b, m, y), hy.top_width(s.b, m, y)
            U = Qb / A
            tau = hy.manning_shear(Qb, A, R, p.n)
            # downstream slope: normal depth (1.11), capped at critical
            slope_len = 0.0
            if not on_base and dam.x_T - s.x_e > EPS:
                S0 = s.z_b / (dam.x_T - s.x_e)
                beta_s = math.atan(S0)
                slope_len = math.hypot(dam.x_T - s.x_e, s.z_b)
                hc = hy.critical_depth(s.b_down, m, head) if s.b_down > 0 or m > 0 else y
                hn = hy.normal_depth(Qb, s.b_down, m, p.n, S0)
                hs = min(hn, hc) if hc > 0 else hn
                As, Rs = hy.area(s.b_down, m, hs), hy.hydraulic_radius(s.b_down, m, hs)
                Ps, Bs = hy.wetted_perimeter(s.b_down, m, hs), hy.top_width(s.b_down, m, hs)
                Us = Qb / As
                taus = hy.manning_shear(Qb, As, Rs, p.n)
            if p.material_class == "noncohesive":
                tp = sd.grain_shear_wu(tau, p.n, p.d50)
                c_star = sd.capacity_dlbreach(Qb, U, R, s.b, tp, self.tau_c_nc, p.d50, p.rho_s, self.ws, p.f_t)
                c1 = sd.relax(0.0, c_star, L_top, p.lam * Bw)
                dV_top = Qb * c1 * dt / (1.0 - p.porosity)
                c2 = c1
                if slope_len > 0.0:
                    tps = sd.grain_shear_wu(taus, p.n, p.d50)
                    te = sd.slope_effective_shear(tps, self.tau_c_nc, beta_s, p.phi)
                    cs_star = sd.capacity_dlbreach(Qb, Us, Rs, s.b_down, te, self.tau_c_nc, p.d50, p.rho_s,
                                                   self.ws, p.f_t)
                    c2 = sd.relax(c1, cs_star, slope_len, p.lam * Bs)
                    dV_slope = Qb * (c2 - c1) * dt / (1.0 - p.porosity)
            else:
                eps = sd.cohesive_rate(tau, p.tau_c_coh, p.kd)
                dV_top = eps * P * L_top * dt
                if slope_len > 0.0:
                    dV_slope = sd.cohesive_rate(taus, p.tau_c_coh, p.kd) * Ps * slope_len * dt
            out.update(tau_top=tau, tau_slope=(taus if slope_len > 0 else 0.0))

        # ---- water (1.2), explicit ----
        Qout = Qb + Qov
        s.V = max(s.V + (Qin - Qout) * dt, 0.0)
        self.cum_in += Qin * dt
        self.cum_out += Qout * dt

        # ---- geometry (Part 3) ----
        self._allocate_top(dV_top)
        self._allocate_slope(dV_slope)
        self._update_side_slope()
        self.cum_eroded_bulk += dV_top + dV_slope
        s.t += dt
        return out

    def _allocate_top(self, dV: float) -> None:
        """(3.1)-(3.5): spread dV over bed + side walls of the flat top."""
        if dV <= 0.0:
            return
        p, dam, s = self.p, self.p.dam, self.s
        sb = math.sin(s.beta)
        L_top = self.flat_top_length()
        x_u = dam.x_up(s.z_b)
        A_side = side_area_top(dam, x_u, s.x_e, s.z_b) if L_top > 0.0 else 0.0
        n_loc = self._active_sides()
        bed_erodible = s.z_b > EPS
        A_bed = s.b * L_top if bed_erodible else 0.0
        A_tot = A_bed + n_loc * A_side / sb
        if A_tot <= 0.0:
            return
        dz = dV / A_tot
        if bed_erodible:
            dz_bed = min(dz, s.z_b)
            s.z_b -= dz_bed
            s.b += n_loc * dz * (1.0 / sb - 1.0 / math.tan(s.beta))
            # the flat top's downstream edge follows the (unrotated) slope line to the new level
            if s.x_e < dam.x_T and s.z_b + dz_bed > EPS:
                z_old = s.z_b + dz_bed
                s.x_e = dam.x_T - (dam.x_T - s.x_e) * s.z_b / z_old
        else:
            s.b += n_loc * dz / sb             # walls retreat on a fixed bed (3.5, base reached)
        self._abutment_limit()

    def _allocate_slope(self, dV: float) -> None:
        """Downstream-slope reach (3.6)-(3.8) and rotation about the toe (Appendix 3A)."""
        p, dam, s = self.p, self.p.dam, self.s
        if dV <= 0.0 or s.z_b <= EPS or dam.x_T - s.x_e <= EPS:
            return
        sb = math.sin(s.beta)
        n_loc = self._active_sides()
        slope_len = math.hypot(dam.x_T - s.x_e, s.z_b)
        A_side = side_area_slope(dam, s.x_e, s.z_b)
        A_tot = s.b_down * slope_len + n_loc * A_side / sb
        if A_tot <= 0.0:
            return
        delta = dV / A_tot                                   # mean normal thickness on the slope reach
        # widening on the slope (3.6)-(3.8)
        cb = min(1.0, max(0.0, 1.8 * s.b / max(s.b_down, EPS) - 0.8))
        s.b_down += n_loc * delta * (max(cb / sb, 1.0 / math.tan(s.beta)) - 1.0 / math.tan(s.beta))
        # rotation about the toe: thickness linear from 0 at the toe, longitudinal area removed = delta * slope_len
        area = delta * slope_len
        x_new = s.x_e - 2.0 * area / s.z_b
        x_u = dam.x_up(s.z_b)
        if x_new >= x_u:
            s.x_e = x_new
        else:
            # flat top consumed: the leftover area lowers the edge along the upstream face
            used = 0.5 * (s.x_e - x_u) * s.z_b
            left = area - used
            z0, xT = s.z_b, dam.x_T

            def removed(z):            # area between line toe->(x_u(z0),z0) and toe->(x_up(z),z)
                return 0.5 * abs((dam.x_up(z0) - xT) * z - (dam.x_up(z) - xT) * z0)

            if removed(0.0) <= left:
                s.z_b, s.x_e = 0.0, dam.x_T
            else:
                from .hydraulics import bisect
                z = bisect(lambda zz: removed(zz) - left, 0.0, z0)
                s.z_b, s.x_e = z, dam.x_up(z)
        if s.z_b <= EPS:
            s.z_b, s.x_e = 0.0, dam.x_T
            s.b = max(s.b, s.b_down)
            s.b_down = s.b

    def _update_side_slope(self) -> None:
        """beta from bank stability (3.14); a flattening releases the failure wedge (counted as eroded)."""
        p, dam, s = self.p, self.p.dam, self.s
        h = max(dam.H - s.z_b, 1e-6)
        beta_new = side_slope_angle(p.cohesion, self.gamma_b, h, p.phi)
        room = dam.L_cr - s.b
        if room > 0.0:                       # walls cannot flatten past the valley sides (3.5-3)
            beta_new = max(beta_new, math.atan2(2.0 * h, room))
        if beta_new < s.beta - 1e-12:
            dcot = 1.0 / math.tan(beta_new) - 1.0 / math.tan(s.beta)
            length = self.flat_top_length() + math.hypot(dam.x_T - s.x_e, s.z_b)
            wedge = self._active_sides() * 0.5 * h * h * dcot * length
            self.cum_failure_bulk += wedge
            self.cum_eroded_bulk += wedge
        s.beta = beta_new
        self._abutment_limit()

    def _active_sides(self) -> int:
        return self.p.n_loc if self.top_width_at_crest() < self.p.dam.L_cr - EPS else 0

    def _abutment_limit(self) -> None:
        """Breach no wider than the valley at crest level (3.5-3)."""
        dam, s = self.p.dam, self.s
        excess = self.top_width_at_crest() - dam.L_cr
        if excess > 0.0:
            s.b = max(s.b - excess, 0.0)
            s.b_down = min(s.b_down, max(s.b, s.b_down - excess))
        d = dam.H - s.z_b
        if d > 0.0 and s.b + 2.0 * d / math.tan(s.beta) > dam.L_cr:
            # the breach already spans the valley: the walls cannot flatten further
            s.beta = math.atan2(2.0 * d, max(dam.L_cr - s.b, 1e-9))

    # ---- diagnostics ---------------------------------------------------------------------------------
    def water_balance_error(self) -> float:
        return (self.s.V - self.V0) - (self.cum_in - self.cum_out)


# ---- case adapter -----------------------------------------------------------------------------------

def params_from_case(case: Dict, factors: Optional[Dict] = None, weir: str = "exact") -> tuple:
    import sys
    from pathlib import Path
    cal = Path(__file__).resolve().parent.parent / "calibration"
    if str(cal) not in sys.path:
        sys.path.insert(0, str(cal))
    from cases import _stage_volume   # same reservoir curves as the 2-D engine

    f = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0, **(factors or {})}
    H = float(case["H"])
    dam = Dam(H=H, Wc=float(case["crest_w"]), zu=float(case["zu"]), zd=float(case["zd"]),
              L_cr=float(case["section_width"]))
    mat = case["material"]
    d50 = mat.get("d50_mm", 0.1) / 1000.0
    phi = math.atan(mat.get("tan_phi", 0.7))
    if mat["class"] == "cohesive" and "qu_kPa" in mat:
        cohesion = mat["qu_kPa"] * 1000.0 / (2.0 * math.tan(math.pi / 4 + phi / 2))
    else:
        cohesion = mat.get("cohesion_kPa", 0.0) * 1000.0
    lab = case.get("kind") == "lab"
    n = case.get("manning_n") or max(0.016, d50 ** (1.0 / 6.0) / (16.0 if lab else 12.0))
    kd = 0.0
    if mat["class"] == "cohesive":
        kd = mat["kd_cm3Ns"] * 1e-6 * (f["f_kd"] if str(mat.get("kd_status", "")).startswith("measured") else 1.0)
    p = Params(dam=dam, material_class=mat["class"], d50=d50, porosity=mat.get("porosity", 0.35), phi=phi,
               cohesion=cohesion, n=n, kd=kd, tau_c_coh=mat.get("tauc_Pa", 0.0), f_t=f["f_t"],
               lam=3.0 if lab else 6.0, n_loc=int(case.get("n_loc", 2)), weir=weir)
    res = Reservoir(_stage_volume(case["reservoir"], H))
    notch = case["notch"]
    z_s0 = case.get("initial_level", (H - notch["depth"]) + (case.get("initial_head") or 0.0))
    return p, res, z_s0, notch, inflow_fn(case.get("inflow", 0.0))


def run_case(case: Dict, factors: Optional[Dict] = None, dt: Optional[float] = None, t_end: Optional[float] = None,
             weir: str = "exact", record_every: Optional[float] = None) -> Dict:
    p, res, z_s0, notch, qin = params_from_case(case, factors, weir)
    t_end = float(t_end or case.get("t_end", 43200.0))
    dt = float(dt or t_end / 20000.0)
    eng = LumpedBreach(p, res, z_s0, notch, qin, p.dam.H)
    nsteps = int(round(t_end / dt))
    rec_every = max(int(round((record_every or t_end / 2000.0) / dt)), 1)
    ts, qs, hist = [], [], []
    for i in range(nsteps):
        o = eng.step(dt)
        ts.append(o["t"]); qs.append(o["Qb"] if case.get("q_measure") == "reservoir" else o["Q"])
        if i % rec_every == 0:
            hist.append(o)
    ts, qs = np.asarray(ts), np.asarray(qs)
    k = int(np.argmax(qs))
    datum = 0.0
    if case.get("tp_datum") == "q_frac":
        frac = float(case.get("tp_datum_frac", 0.05))
        datum = float(ts[int(np.argmax(qs >= frac * qs[k]))])
    lowered = max(eng.z_b0 - eng.s.z_b, 0.0)
    return {"id": case["id"], "Qp": float(qs[k]), "Tp_h": (float(ts[k]) - datum) / 3600.0,
            "B": eng.average_width(), "B_top": eng.top_width_at_crest(), "breached": lowered > 0.5 * notch["depth"],
            "z_b_end": eng.s.z_b, "beta_end_deg": math.degrees(eng.s.beta),
            "water_balance_rel": eng.water_balance_error() / max(eng.V0, 1.0),
            "eroded_bulk_m3": eng.cum_eroded_bulk, "failure_bulk_m3": eng.cum_failure_bulk,
            "dt": dt, "t_end": t_end, "steps": nsteps, "history": hist}
