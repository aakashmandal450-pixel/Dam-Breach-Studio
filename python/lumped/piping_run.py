"""Piping stage 3c: the piping driver (Theory Part 5, sections 5.2-5.7a; docs/theory/05_piping.md).

One run from pipe initiation to the hand-over to the open breach. Each step follows a fixed sequence:

    hydraulics -> pipe erosion and water balance over dt -> checks on the new state
    -> if any check fails inside the step: locate the failure instant by bisection, redo the step to that
       instant, then run the synchronous cascade (5.7a.6) on that state -> finish the rest of the step
    -> water and solids budget checks on every completed step

Checks on one state (all read the same state):
  roof sections (5.15) on the pipe, or on the upstream and downstream reaches once a crater exists;
  failing reaches classified as upstream-end, downstream-end or interior (ends.py);
  blow-out at the outlet (mechanism C via N_b, 5.6) as its own outlet rule;
  push-out of the whole roof (mechanism B, 5.10) before a crater, of the remnants (5.23) after;
  crater walls (5.17) with the validity-domain guard.

Outcomes kept separate: inlet retreat, outlet retreat (roof end), outlet uplift (mechanism C), crater
start, crater extension, wall failures, hand-over, and stops (numerical error, domain error, multiple
craters, crater opening downstream, cascade cap). Stage 4 (the hand-over itself) is not implemented: the
run stops at the hand-over with the full state recorded.

Water budget (every step):  V_res + W_c + cum_out - V_res0 - cum_supply - released = 0 (round-off)
Solids (every step): crater identity (1 - n) V_fall = (1 - n_d)(V_db + V_spoil + V_exp); pipe erosion
volume equal to the void added (exact by construction in piping.erode, re-checked here).
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import numpy as np

from . import crater as cm
from . import ends
from . import exit_headcut as xh
from . import exit_widening as xw
from . import piping as pp
from . import roof
from .geometry import Dam
from .hydraulics import crest_overflow
from .stability_table import StabilityTable, TableRangeError

GAMMA_W = roof.GAMMA_W
Z_BASE = 0.0          # dam base elevation: hard lower bound of every floor (5.7a.11)
CONTINUOUS = {"inlet", "outlet", "crater_up", "crater_down", "uplift"}   # moving boundaries (after onset)


class RunStop(RuntimeError):
    """A stop the theory does not cover or a numerical failure; carries an event type."""

    def __init__(self, kind: str, msg: str):
        super().__init__(f"{kind}: {msg}")
        self.kind = kind


@dataclass
class PipingCase:
    dam: Dam
    soil: roof.Soil
    kd: float                  # m3/(N s)
    tau_c: float               # Pa
    b0: float
    D0: float
    z_inv0: float
    z_s0: float
    porosity: float = 0.35
    n_d: float | None = None   # debris porosity (default = porosity)
    n_p: float = 0.016
    constant_level: bool = True
    reservoir: object = None   # model.Reservoir when constant_level is False
    inflow: object = None      # callable t -> m3/s when constant_level is False
    bound: str = "mid"
    tension: bool = True       # wall criterion 3.776 (True) or 2 (tension cut-off)
    pore_storage: bool = True
    exit_headcut: bool = False   # 5.6 exit headcut at the outlet (optional, off by default)
    exit_widening: bool = False  # note H-1, H1-a: widening of the exit notch (optional, off by default)
    debris: str = "level"        # 5.7 debris treatment: 'level' (default) | 'instant' | 'tank' (comparison modes)
    C_h: float = 1.0             # Part 4 headcut advance factor (not adjusted)
    plugs: bool = False          # 5.7b: D5 (both mouths obstructed by the deposit) + D1-a plug breakthrough
    c_d: float = 0.0             # 5.7b: debris cohesion in (5.26) [Pa]; 0 = non-plastic remoulded debris


@dataclass
class State:
    t: float
    V: float                   # reservoir volume (constant-level runs: unused)
    z_s: float
    pipe: pp.Pipe              # upstream pipe (whole pipe before a crater); L = its length
    x_in: float
    x_o: float
    crater: cm.Crater | None = None
    pipe_dn: pp.Pipe | None = None     # downstream reach (frozen at crater start, 5.7a.7)
    cum_supply: float = 0.0
    cum_out: float = 0.0
    cum_spill: float = 0.0     # part of cum_out that left over the crater rim (crater_spilling, 5.7a.11)
    cum_eroded: float = 0.0    # bulk soil eroded from the pipe walls (exported)
    V_end_up: float = 0.0      # bulk roof exported at inlet retreats
    V_end_dn: float = 0.0      # bulk roof exported at outlet retreats
    V_uplift: float = 0.0      # bulk cover removed by mechanism C
    released_out: float = 0.0  # pore water of fallen soil (enters W_c; tracked for the budget)
    hc: xh.ExitHeadcut | None = None   # exit headcut (5.6), when switched on
    hc_moved: float = 0.0      # outlet retreat by the exit headcut in the last step (for the event log)
    B_e: float | None = None   # H-1: exit (notch) width, when exit widening is on
    V_exit: float = 0.0        # H-1: bulk soil removed by widening beyond the pipe width (exported)


def upstream_flow(p: pp.Pipe, z_s: float, z_c: float, n_p: float, mouth=None):
    """Signed discharge of the upstream reach between the reservoir (z_s) and the crater (z_c), and the
    PipeFlow that sets the wall shear and soffit pressure. Forward (z_s >= z_c): reservoir -> crater with
    tailwater z_c. Reverse (z_c > z_s): the same pipe relations with the ends exchanged, crater -> reservoir
    (draft 5.8; a hydraulic correction that keeps z_c from rising above the reservoir).

    mouth = (a_open, z_o) when the deposit covers the upstream mouth (5.7b.1, D5): a partly covered mouth
    uses the pipe relations with height a_open and heads from z_o (as the downstream reach, 5.25); a fully
    covered mouth (a plug) passes no flow and leaves the reach full and stagnant at the reservoir head."""
    L = max(p.L, 0.0)
    if mouth is not None and mouth[0] < p.D:
        a, z_o = mouth
        if a <= 0.0:
            fl = pp.pipe_flow(z_s - p.z_inv, p.b, p.D, L, n_p, h_t=z_s - p.z_inv)
            return 0.0, fl, False
        if z_c <= z_s:
            fl = pp.pipe_flow(z_s - z_o, p.b, a, L, n_p, h_t=max(z_c - z_o, 0.0))
            return fl.Q, fl, False
        fl = pp.pipe_flow(z_c - z_o, p.b, a, L, n_p, h_t=max(z_s - z_o, 0.0))
        return -fl.Q, fl, True
    if z_c <= z_s:
        fl = pp.pipe_flow(z_s - p.z_inv, p.b, p.D, L, n_p, h_t=max(z_c - p.z_inv, 0.0))
        return fl.Q, fl, False
    fl = pp.pipe_flow(z_c - p.z_inv, p.b, p.D, L, n_p, h_t=max(z_s - p.z_inv, 0.0))
    return -fl.Q, fl, True


class PipingRun:
    def __init__(self, case: PipingCase, table: StabilityTable, dt: float = 1.0, record_every: float = 10.0,
                 t_tol: float = 1e-3, max_passes: int = 200):
        self.c, self.T = case, table
        self.dt, self.t_tol, self.max_passes = dt, t_tol, max_passes
        self.n_d = case.n_d if case.n_d is not None else case.porosity
        dam = case.dam
        z_bp = case.z_inv0 + case.D0 / 2
        x_in, x_o = dam.x_up(z_bp), dam.x_down(z_bp)
        V0 = case.reservoir.volume(case.z_s0) if not case.constant_level else 0.0
        self.s = State(0.0, V0, case.z_s0, pp.Pipe(case.b0, case.D0, case.z_inv0, x_o - x_in), x_in, x_o)
        if case.exit_headcut and case.exit_widening:
            raise ValueError("exit_headcut and exit_widening are separate experiments (note H-1, decision 5)")
        if case.exit_widening:
            self.s.B_e = case.b0
        if case.exit_headcut:
            self.s.hc = xh.ExitHeadcut(x_h=x_o, z_h=case.z_inv0)
        self.V0 = V0
        self.events, self.series = [], []
        self.record_every, self._next_rec = record_every, 0.0
        self.stopped = None
        self.max_water_err = 0.0
        self.max_solids_err = 0.0
        self.passes_max = 0
        self.stall = None
        # A margin counts as failed below -M_tol. Without it, a retreat to the interpolated zero crossing
        # leaves M ~ 0 (+-round-off) at the new end and the cascade repeats zero-length retreats.
        self.M_tol = 1e-6 * case.soil.c_u0
        # Failure kinds whose onset has been event-located. Once an end or a crater edge has started to move,
        # its further motion is continuous (the margin at the new boundary is ~0 and keeps falling as the pipe
        # grows), so it is applied at the end of each step; the onset of every kind is located in the step.
        self.onset = set()
        # Sealed state: downstream entrance blocked, no failure, geometry and water stationary for T_seal
        self.T_seal = 600.0
        self.seal_tol = dict(length=1e-6, volume=1e-6, flow=1e-6)
        self._seal_ref = None
        self._spill_ref, self._spilling = None, False
        self._plugs_formed = set()

    # ------------------------------------------------------------------ hydraulics on a state
    def hyd(self, s: State) -> dict:
        c = self.c
        p = s.pipe
        HW = s.z_s - p.z_inv
        h = dict(z_c=math.nan, Q_out_cr=0.0, Q_spill=0.0, fl_dn=None, reverse=False)
        if s.crater is None:
            fl = pp.pipe_flow(HW, p.b, p.D, p.L, c.n_p)
            h.update(fl_up=fl, Q_res=fl.Q, Q_final=fl.Q)
        else:
            cr = s.crater
            z_c = cr.level()
            q_up, fl, rev = upstream_flow(p, s.z_s, z_c, c.n_p, self._mouth_up(s))
            h["reverse"] = rev
            ao = cr.a_open()
            z_o = cr.z_open()
            fl_dn = pp.pipe_flow(z_c - z_o, cr.b_p, ao, cr.L_down, c.n_p) if ao > 0 and cr.L_down > 0 else None
            Qo, Qs = cr.Q_out(z_c), cr.Q_spill(z_c)
            h.update(fl_up=fl, Q_res=q_up, z_c=z_c, Q_out_cr=Qo, Q_spill=Qs, fl_dn=fl_dn, Q_final=Qo + Qs)
        crest = crest_overflow(c.dam.L_cr, s.z_s - c.dam.H)
        h["Q_crest"] = crest
        h["Q_res"] += crest
        h["Q_final"] += crest
        return h

    # ------------------------------------------------------------------ one smooth step (no events)
    def advance(self, s: State, dt: float) -> State:
        c = self.c
        n = copy.deepcopy(s)
        h = self.hyd(s)
        fl = h["fl_up"]
        eps = pp.erosion_rate(pp.wall_shear(fl), c.kd, c.tau_c)
        bmax = n.crater.W if n.crater is not None else math.inf      # 5.7a.11: connected pipe <= crater width
        if n.pipe.L > 0:
            new_pipe, dV = pp.erode(n.pipe, eps, fl.w, fl.y, dt, b_max=bmax)
            n.pipe, n.cum_eroded = new_pipe, n.cum_eroded + dV
        p0 = s.pipe
        if n.crater is None:
            q_res = h["Q_res"]
        else:
            # crater water (5.22) by backward Euler: W1 = W0 + dt (q_up(W1) - q_out(W1) - q_spill(W1)).
            # Implicit, because the exchange with the reservoir follows a square root of the level difference:
            # an explicit scheme limit-cycles around z_c = z_s (found in the first P1 runs, draft 5.8).
            # The residual is a monotone function of W1, solved by bisection; the same inflow leaves the
            # reservoir, so the water budget closes exactly.
            cr = n.crater
            W0 = cr.W_c
            mouth = self._mouth_up(s)

            def fluxes(W):
                old = cr.W_c; cr.W_c = max(W, 0.0)
                zc = cr.level()
                qi, fl_i, rev = upstream_flow(p0, s.z_s, zc, c.n_p, mouth)
                qo = cr.Q_out(zc) + cr.Q_spill(zc)
                cr.W_c = old
                return qi, qo, fl_i

            def resid(W):
                qi, qo, _ = fluxes(W)
                return W - W0 - dt * (qi - qo)
            lo, hi = 0.0, max(W0, 1e-6)
            while resid(hi) < 0.0:
                hi *= 2.0
            if resid(lo) >= 0.0:
                hi = lo
            for _ in range(200):
                if hi - lo <= 1e-13 * max(hi, 1e-9):
                    break
                mid = 0.5 * (lo + hi)
                if resid(mid) < 0.0:
                    lo = mid
                else:
                    hi = mid
            W1 = hi
            qi, qo, fl_end = fluxes(W1)
            vin = dt * qi
            vout = W0 + vin - W1                              # closes the crater balance exactly
            cr.W_c = W1
            q_sp = cr.Q_spill(cr.level())                     # split of the outflow (5.22): rim spill / pipe
            n.cum_spill += min(dt * q_sp, vout) if vout > 0.0 else 0.0
            n.cum_out += vout + h["Q_crest"] * dt
            q_res = vin / dt + h["Q_crest"]
            # erosion of the upstream reach with the implicit (end-of-step) exchange flow
            eps1 = pp.erosion_rate(pp.wall_shear(fl_end), c.kd, c.tau_c)
            if n.pipe.L > 0:
                n.pipe, n.cum_eroded = s.pipe, s.cum_eroded
                if cr.debris == "tank" and cr.V_tank > 0.0:
                    # DL Breach virtual tank (Wu 2016, 4.7): the flow's erosion capacity removes stored debris
                    # instead of eroding the walls; the geometry is frozen until the tank is empty
                    _, dV_pot = pp.erode(s.pipe, eps1, fl_end.w, fl_end.y, dt, b_max=bmax)
                    take = min(dV_pot, cr.V_tank)
                    cr.V_tank -= take
                    cr.V_exp_out += take
                    if dV_pot > take and dV_pot > 0.0:       # tank emptied inside the step: erode for the rest
                        new_pipe, dV = pp.erode(s.pipe, eps1, fl_end.w, fl_end.y, dt * (1.0 - take / dV_pot), b_max=bmax)
                        n.pipe, n.cum_eroded = new_pipe, s.cum_eroded + dV
                else:
                    new_pipe, dV = pp.erode(s.pipe, eps1, fl_end.w, fl_end.y, dt, b_max=bmax)
                    n.pipe, n.cum_eroded = new_pipe, s.cum_eroded + dV
        if n.crater is None:
            n.cum_out += h["Q_final"] * dt
        # reservoir
        if c.constant_level:
            n.cum_supply += q_res * dt
        else:
            qin = c.inflow(s.t)
            n.cum_supply += qin * dt
            n.V += (qin - q_res) * dt
            n.z_s = c.reservoir.level(n.V)
        # exit widening (H-1, H1-a): the same outlet discharge as the exit headcut would see
        if n.B_e is not None:
            if n.crater is None:
                q_w, pw = h["fl_up"].Q, n.pipe
            else:
                q_w, pw = h["Q_out_cr"], n.pipe_dn
            n.B_e, dVw = xw.step(n.B_e, pw.b, pw.D, q_w, c.dam.zd, c.n_p, c.kd, c.tau_c, dt)
            n.V_exit += dVw
        # exit headcut (5.6): driven by the discharge leaving the outlet at the start of the step
        n.hc_moved = 0.0
        if n.hc is not None:
            if n.crater is None:
                q_o, po = h["fl_up"].Q, n.pipe
            else:
                q_o, po = h["Q_out_cr"], n.pipe_dn
            gam = c.soil.gamma_sat
            new_hc, x_o_new = xh.step(n.hc, c.dam, q_o, po.b, po.z_inv, po.z_cr, n.x_o, dt, c.kd, c.tau_c,
                                      c.soil.c_u0, gam, c.n_p, c.C_h)
            n.hc_moved = n.x_o - x_o_new
            n.hc = new_hc
            if x_o_new < n.x_o:
                n.x_o = x_o_new
                if n.crater is None:
                    n.pipe = pp.Pipe(n.pipe.b, n.pipe.D, n.pipe.z_inv, n.x_o - n.x_in)
                else:
                    n.crater.L_down = n.x_o - n.crater.x2
                    n.pipe_dn = pp.Pipe(n.pipe_dn.b, n.pipe_dn.D, n.pipe_dn.z_inv, n.crater.L_down)
        n.t = s.t + dt
        return n

    # ------------------------------------------------------------------ checks on one state
    def checks(self, s: State) -> dict:
        """Everything that can fail, evaluated on one state. A geometry outside the stability table stops
        the run as 'table_range' (never extrapolated, 5.5b)."""
        try:
            return self._checks(s)
        except TableRangeError as e:
            raise RunStop("table_range", str(e))

    def _checks(self, s: State) -> dict:
        """Everything that can fail, evaluated on one state. Returns a dict of findings."""
        c, dam = self.c, self.c.dam
        h = self.hyd(s)
        out = dict(h=h, fail=False)
        if s.crater is None:
            rc = roof.check(dam, s.pipe, s.x_in, s.x_o, s.z_s, h["fl_up"], c.soil, self.T, c.bound)
            out["rc"] = rc
            out["F"] = ends.classify(rc, self.M_tol)
            out["blow"] = _blowout_at_outlet(rc)
            out["M_B"] = rc.M_B
            out["min_M"] = min(v for v in (rc.min_M_c, rc.M_B, out["blow"][1]) if not math.isnan(v))
        else:
            cr = s.crater
            p = s.pipe
            mins = []
            if cr.x1 - s.x_in > 0:
                if h["reverse"]:                         # crater -> reservoir: energy from the crater end
                    rcu = roof.check(dam, p, s.x_in, cr.x1, s.z_s, h["fl_up"], c.soil, self.T, c.bound, ab=False,
                                     z_head=h["z_c"], x_entry=cr.x1)
                else:
                    rcu = roof.check(dam, p, s.x_in, cr.x1, s.z_s, h["fl_up"], c.soil, self.T, c.bound, ab=False)
                out["rc_up"], out["F_up"] = rcu, ends.classify(rcu, self.M_tol)
                mins.append(rcu.min_M_c)
            if s.x_o - cr.x2 > 0:
                fl_dn = h["fl_dn"] or pp.pipe_flow(0.0, cr.b_p, cr.a_p, cr.L_down, c.n_p)
                rcd = roof.check(dam, s.pipe_dn, cr.x2, s.x_o, s.z_s, fl_dn, c.soil, self.T, c.bound,
                                 z_head=h["z_c"], ab=False)
                out["rc_dn"], out["F_dn"] = rcd, ends.classify(rcd, self.M_tol)
                out["blow"] = _blowout_at_outlet(rcd)
                mins += [rcd.min_M_c, out["blow"][1]]
            walls = self.wall_margins(s, h["z_c"])
            out["walls"] = walls
            mins += [m for m, _ in walls.values()]
            mu, md = cm.pushout_margins(dam, cr.z_cr, cr.b_p, s.z_s, h["z_c"], s.x_in, cr.x1, cr.x2, s.x_o,
                                        c.soil.c_u0, c.soil.rho)
            out["push"] = (mu, md)
            mins += [mu, md]
            if c.plugs:
                out["plugs"] = self.plug_margins(s, h["z_c"])
                mins += [d["M"] for d in out["plugs"].values()]
            mins = [v for v in mins if not math.isnan(v)]
            out["min_M"] = min(mins) if mins else math.inf
        out["fail"] = out["min_M"] < -self.M_tol
        return out

    def wall_margins(self, s: State, z_c: float) -> dict:
        """H_c - H_w for the up, down and side walls (5.17); DomainError stops the run."""
        c, cr = self.c, s.crater
        res = {}
        for k, (Hw, hw) in cr.wall_heights().items():
            if Hw <= 0:
                res[k] = (math.inf, 0.0); continue
            gam = roof.gamma_bar(Hw, cr.z_d, s.z_s, c.soil)
            try:
                Hc = cm.wall_critical_height(c.soil.c_u0, gam, GAMMA_W, c.soil.rho, hw, Hw, c.tension)
            except cm.DomainError as e:
                raise RunStop("domain_error", f"wall {k}: {e}")
            res[k] = (Hc - Hw, Hw)
        return res

    # ------------------------------------------------------------------ the cascade (5.7a.6)
    def cascade(self, s: State) -> State:
        c, dam = self.c, self.c.dam
        for npass in range(1, self.max_passes + 1):
            chk = self.checks(s)
            if not chk["fail"]:
                self.passes_max = max(self.passes_max, npass - 1)
                self._log_plugs_formed(s)
                return s
            s = self.apply(s, chk)
            if self.stopped:
                return s
        self.stall = self._stall_info(s, self.checks(s))
        raise RunStop("cascade_cap", f"no convergence in {self.max_passes} passes")

    def _stall_info(self, s: State, chk: dict) -> dict:
        """Diagnostic only: what is still failing when the cascade cap is reached (state after the last pass)."""
        info = dict(t=s.t, min_M=chk["min_M"], x_in=s.x_in, x_o=s.x_o, b=s.pipe.b)
        cr = s.crater
        if cr is not None:
            info.update(x1=cr.x1, x2=cr.x2, W=cr.W, z_d=cr.z_d, z_c=cr.level(),
                        walls={k: (m + hw, hw) for k, (m, hw) in chk["walls"].items()}, push=chk["push"])
            for key in ("rc_up", "rc_dn"):
                if key in chk:
                    rc = chk[key]
                    k = min(range(len(rc.M_c)), key=lambda j: rc.M_c[j]) if rc.M_c else None
                    if k is not None:
                        info[key] = dict(x=rc.x[k], M_c=rc.M_c[k], n=len(rc.x),
                                         neighbours=[(rc.x[j], rc.M_c[j]) for j in range(max(k - 1, 0), min(k + 2, len(rc.x)))])
        return info

    def apply(self, s: State, chk: dict) -> State:
        """Apply every failure found on one state together, then check the geometry invariants (5.7a.11)."""
        s = self._apply(s, chk)
        cr = s.crater
        if cr is not None and cr.z_d < Z_BASE - 1e-9:
            raise RunStop("geometry_error", f"crater floor {cr.z_d:.4f} m below the dam base {Z_BASE:.3f} m")
        if cr is not None and s.x_in < cr.x1 and s.pipe.b > cr.W * (1 + 1e-9):
            raise RunStop("geometry_error", f"connected pipe b {s.pipe.b:.4f} m wider than the crater W {cr.W:.4f} m")
        return s

    def _apply(self, s: State, chk: dict) -> State:
        """Apply every failure found on one state together, then update the derived quantities."""
        c, dam = self.c, self.c.dam
        s = copy.deepcopy(s)
        b, z_cr = s.pipe.b, s.pipe.z_cr
        if s.crater is None:
            F = chk["F"]
            if F.whole or chk["M_B"] <= 0.0:
                return self._handover(s, "whole roof failed" if F.whole else "roof pushed out (mechanism B)")
            if len(F.interior) > 1:
                return self._stop(s, "multiple_craters", f"interior reaches {F.interior}")
            new_in, new_o = s.x_in, s.x_o
            r = ends.retreat(dam, b, z_cr, s.x_in, s.x_o, F)
            if F.x_up is not None:
                self._event(s, "inlet_retreat", x_from=s.x_in, x_to=r.x_in, dist=r.x_in - s.x_in, V=r.V_up)
                s.V_end_up += r.V_up; new_in = r.x_in
            if F.x_dn is not None:
                self._event(s, "outlet_retreat", x_from=s.x_o, x_to=r.x_o, dist=s.x_o - r.x_o, V=r.V_dn)
                s.V_end_dn += r.V_dn; new_o = r.x_o
            xb_blow, mb = chk["blow"]
            if xb_blow is not None and F.x_dn is None:
                new_o = self._uplift(s, xb_blow, new_o)
            s.x_in, s.x_o = new_in, new_o
            s.pipe = pp.Pipe(s.pipe.b, s.pipe.D, s.pipe.z_inv, s.x_o - s.x_in)
            if F.interior:
                xa, xb = _reach_extent(chk["rc"], F.interior[0])
                dx = 0.5 * s.pipe.b                     # section spacing: the resolution of the failed reach
                if xb - xa < dx:
                    xm = 0.5 * (xa + xb); xa, xb = xm - 0.5 * dx, xm + 0.5 * dx
                xa, xb = max(xa, s.x_in), min(xb, s.x_o)
                s = self._start_crater(s, xa, xb)
            return s
        # crater exists
        cr = s.crater
        new_x1, new_x2 = cr.x1, cr.x2
        if "F_up" in chk:
            F = chk["F_up"]
            if F.whole:
                return self._handover(s, "cascade reached the inlet")
            if F.interior:
                return self._stop(s, "multiple_craters", f"second failure upstream {F.interior}")
            if F.x_up is not None:
                r = ends.retreat(dam, b, z_cr, s.x_in, cr.x1, ends.Failures(F.x_up, None, [], False))
                self._event(s, "inlet_retreat", x_from=s.x_in, x_to=r.x_in, dist=r.x_in - s.x_in, V=r.V_up)
                s.V_end_up += r.V_up; s.x_in = r.x_in
            if F.x_dn is not None:
                new_x1 = max(F.x_dn, s.x_in)
        if "F_dn" in chk:
            F = chk["F_dn"]
            if F.whole:
                return self._stop(s, "crater_open_downstream", "the downstream reach failed end to end")
            if F.interior:
                return self._stop(s, "multiple_craters", f"second failure downstream {F.interior}")
            if F.x_up is not None:
                new_x2 = min(F.x_up, s.x_o)
            if F.x_dn is not None:
                zc_dn = s.pipe_dn.z_cr
                r = ends.retreat(dam, s.pipe_dn.b, zc_dn, cr.x2, s.x_o, ends.Failures(None, F.x_dn, [], False))
                self._event(s, "outlet_retreat", x_from=s.x_o, x_to=r.x_o, dist=s.x_o - r.x_o, V=r.V_dn)
                s.V_end_dn += r.V_dn; s.x_o = r.x_o
            elif chk.get("blow", (None, 0))[0] is not None:
                s.x_o = self._uplift(s, chk["blow"][0], s.x_o, pipe=s.pipe_dn)
        mu, md = chk["push"]
        if mu <= 0.0:
            return self._handover(s, "upstream remnant pushed out (5.23)")
        if md <= 0.0:
            return self._stop(s, "crater_open_downstream", "downstream remnant pushed out (5.23)")
        # plug breakthrough (5.7b.3, D1-a), on the same state as the checks
        for k, d in chk.get("plugs", {}).items():
            if d["M"] < -self.M_tol:
                self._plug_fail(s, k, d)
        # roof extension of the crater
        if new_x1 < cr.x1:
            self._extend(s, new_x1, cr.x2, "up")
        if new_x2 > cr.x2:
            self._extend(s, cr.x1, new_x2, "down")
        # walls (on the same state as the checks)
        walls = chk["walls"]
        for k in ("up", "down"):
            if walls[k][0] <= 0.0:
                d = cr.retreat_wall(k, S_r=self._sat(walls[k][1], cr.z_d, s.z_s))
                self._event(s, f"wall_{k}", dist=d, H_w=walls[k][1], H_c=walls[k][0] + walls[k][1])
        if walls["side"][0] <= 0.0:
            d = cr.retreat_wall("sides", S_r=self._sat(walls["side"][1], cr.z_d, s.z_s))
            self._event(s, "wall_sides", dist=d, H_w=walls["side"][1], H_c=walls["side"][0] + walls["side"][1])
        if cr.x1 <= s.x_in + 1e-12:
            return self._handover(s, "crater reached the inlet")
        if cr.x2 >= s.x_o - 1e-12:
            return self._stop(s, "crater_open_downstream", "crater reached the outlet")
        if s.z_s > dam.z_dam(cr.x1):
            return self._handover(s, "reservoir above the ground at the crater's upstream end")
        s.pipe = pp.Pipe(s.pipe.b, s.pipe.D, s.pipe.z_inv, cr.x1 - s.x_in)
        cr.L_down = s.x_o - cr.x2
        s.pipe_dn = pp.Pipe(s.pipe_dn.b, s.pipe_dn.D, s.pipe_dn.z_inv, cr.L_down)
        return s

    # ------------------------------------------------------------------ plugs (5.7b, D5 + D1-a)
    def _mouth_up(self, s: State):
        """(a_open, z_o) of the upstream mouth when the deposit can cover it (5.27); None when unrestricted."""
        cr = s.crater
        if cr is None or not self.c.plugs or cr.open_up:
            return None
        p = s.pipe
        a = min(max(p.z_cr - max(cr.z_d, p.z_inv), 0.0), p.D)
        return (a, max(cr.z_d, p.z_inv))

    def i_cr(self, b: float) -> float:
        """(5.26): critical gradient of a debris plug of width b."""
        c, n, nd = self.c, self.c.porosity, self.n_d
        gs = (c.soil.gamma_sat - n * GAMMA_W) / (1.0 - n)          # solid unit weight of the intact soil
        gsd = (1.0 - nd) * gs + nd * GAMMA_W
        return (gsd - GAMMA_W) / GAMMA_W + 2.0 * c.c_d / (GAMMA_W * b)

    def plug_margins(self, s: State, z_c: float) -> dict:
        """M_plug = gamma_w l (i_cr - i) of every fully covered, unfailed mouth (5.28), each with its own
        boundary conditions: downstream, crater water over an empty pipe; upstream, reservoir against crater."""
        cr, out = s.crater, {}
        zd = cr.z_d
        if not cr.open_dn and cr.L_down > 0 and cr.a_open() <= 0.0:
            ell = zd - cr.z_cr
            if ell > 0:
                dh = max(z_c - cr.z_cr, 0.0)
                ic = self.i_cr(cr.b_p)
                out["dn"] = dict(M=GAMMA_W * (ell * ic - dh), i=dh / ell, i_cr=ic, dh=dh, ell=ell,
                                 b=cr.b_p, a=cr.a_p, z_cr=cr.z_cr)
        mouth = self._mouth_up(s)
        if mouth is not None and mouth[0] <= 0.0 and s.x_in < cr.x1:
            p = s.pipe
            ell = zd - p.z_cr
            if ell > 0:
                if s.z_s >= z_c:
                    dh = max(s.z_s - max(z_c, p.z_cr), 0.0)
                else:
                    dh = max(z_c - max(s.z_s, p.z_cr), 0.0)
                ic = self.i_cr(p.b)
                out["up"] = dict(M=GAMMA_W * (ell * ic - dh), i=dh / ell, i_cr=ic, dh=dh, ell=ell,
                                 b=p.b, a=p.D, z_cr=p.z_cr)
        return out

    def _plug_fail(self, s: State, k: str, d: dict) -> None:
        """D1-a: a pipe-sized channel reopens the mouth. Downstream: the plug b a l is carried out of the
        outlet (crater and system export) with its pore water; upstream: it rejoins the deposit (no export)."""
        cr = s.crater
        if k not in self._plugs_formed:                  # covered and failed in the same cascade
            self._plugs_formed.add(k)
            self._event(s, f"plug_{k}_formed", z_d=cr.z_d)
        V = d["b"] * d["a"] * d["ell"]
        w = 0.0
        if k == "dn":
            S = min(max((cr.level() - d["z_cr"]) / d["ell"], 0.0), 1.0)
            w = min(self.n_d * V * S, cr.W_c)
            cr.V_exp += V
            cr.V_exp_out += V
            cr.W_c -= w
            s.cum_out += w
            cr.open_dn = True
        else:
            cr.open_up = True
        self._event(s, f"plug_{k}_fail", i=d["i"], i_cr=d["i_cr"], dh=d["dh"], ell=d["ell"],
                    V_plug=V if k == "dn" else 0.0, V_plug_geom=V, w_out=w)
        self._event(s, f"mouth_{k}_open")

    def _log_plugs_formed(self, s: State) -> None:
        if not self.c.plugs or s.crater is None:
            return
        cr = s.crater
        cov = {"dn": (not cr.open_dn and cr.a_open() <= 0.0)}
        m = self._mouth_up(s)
        cov["up"] = m is not None and m[0] <= 0.0 and s.x_in < cr.x1
        for k, on in cov.items():
            if on and k not in self._plugs_formed:
                self._plugs_formed.add(k)
                self._event(s, f"plug_{k}_formed", z_d=cr.z_d)

    # ------------------------------------------------------------------ helpers for apply
    def _sat(self, H, z_bot, z_ph):
        """Saturated fraction of a soil column of height H above z_bot (phreatic level z_ph), for S_r."""
        if H <= 0:
            return 0.0
        return min(max(z_ph - z_bot, 0.0), H) / H

    def _roof_fall(self, s: State, xa: float, xb: float, pipe=None):
        pipe = pipe or s.pipe
        dam, z_cr, b = self.c.dam, pipe.z_cr, pipe.b
        A = ends.roof_area(dam, z_cr, xa, xb)
        A_dry = ends.roof_area(dam, max(s.z_s, z_cr), xa, xb)
        return b * A, (A - A_dry) / A if A > 0 else 0.0

    def _start_crater(self, s: State, xa: float, xb: float) -> State:
        c = self.c
        p = s.pipe
        cr = cm.Crater(c.dam, xa, xb, p.b, p.z_inv, p.D, p.b, s.x_o - xb, n=c.porosity, n_d=self.n_d,
                       n_p=c.n_p, pore_storage=c.pore_storage, debris=c.debris)
        cr.V_pipe = p.b * p.D * (xb - xa)
        Vr, Sr = self._roof_fall(s, xa, xb)
        cr.fall(Vr, S_r=Sr)
        s.crater = cr
        s.pipe_dn = pp.Pipe(p.b, p.D, p.z_inv, s.x_o - xb)
        s.pipe = pp.Pipe(p.b, p.D, p.z_inv, xa - s.x_in)
        self._event(s, "crater_start", x1=xa, x2=xb, V_roof=Vr, z_d=cr.z_d, z_c=cr.level())
        return s

    def _extend(self, s: State, x1: float, x2: float, side: str) -> None:
        cr = s.crater
        xa, xb = (x1, cr.x1) if side == "up" else (cr.x2, x2)
        if xb - xa <= 1e-9:
            return
        p = s.pipe if side == "up" else s.pipe_dn          # the reach being opened, with its own section
        Vr, Sr = self._roof_fall(s, xa, xb, pipe=p)
        cr.x1, cr.x2 = x1, x2
        cr.fall(Vr, S_r=Sr, new_pipe=p.b * p.D * (xb - xa))
        self._event(s, f"crater_extend_{side}", x_from=(xb if side == "up" else xa), x_to=(xa if side == "up" else xb),
                    dist=xb - xa, V_roof=Vr)

    def _uplift(self, s: State, x_cut: float, x_o: float, pipe=None) -> float:
        pipe = pipe or s.pipe
        if x_cut >= x_o:
            return x_o
        V = pipe.b * ends.roof_area(self.c.dam, pipe.z_cr, x_cut, x_o)
        s.V_uplift += V
        self._event(s, "outlet_uplift_C", x_from=x_o, x_to=x_cut, dist=x_o - x_cut, V=V)
        return x_cut

    def _handover(self, s: State, why: str) -> State:
        self._event(s, "handover", why=why)
        self.stopped = ("handover", why)
        return s

    def _stop(self, s: State, kind: str, why: str) -> State:
        self._event(s, "stop_" + kind, why=why)
        self.stopped = (kind, why)
        return s

    def _event(self, s: State, kind: str, **kw) -> None:
        cr = s.crater
        e = dict(t=s.t, type=kind, z_s=s.z_s, b=s.pipe.b, D=s.pipe.D, z_inv=s.pipe.z_inv, x_in=s.x_in, x_o=s.x_o,
                 L=s.pipe.L, water_err=self.water_error(s), **kw)
        if s.hc is not None:
            e.update(hc_stage=s.hc.stage, hc_x_h=s.hc.x_h, hc_z_h=s.hc.z_h, V_hc=s.hc.vol, V_hc_roof=s.hc.V_roof)
        if s.B_e is not None:
            e.update(B_e=s.B_e, V_exit=s.V_exit)
        if cr is not None:
            e.update(cr_x1=cr.x1, cr_x2=cr.x2, cr_W=cr.W, z_d=cr.z_d, z_c=cr.level(), W_c=cr.W_c,
                     a_open=cr.a_open(), V_fall=cr.V_fall, V_tank=cr.V_tank, V_exp_out=cr.V_exp_out,
                     debris=cr.debris, solids_err=self.solids_error(s))
        self.events.append(e)

    # ------------------------------------------------------------------ exit headcut log and limits
    def _headcut_log(self, s: State, stage0) -> None:
        if s.hc is None:
            return
        if stage0 == 1 and s.hc.stage == 2:
            self._event(s, "headcut_plunging", x_h=s.hc.x_h, z_h=s.hc.z_h)
        if s.hc_moved > 0.0:
            self._event(s, "headcut_outlet_retreat", dist=s.hc_moved, x_h=s.hc.x_h, z_h=s.hc.z_h)
        if s.crater is None and s.x_o <= s.x_in + 1e-9:
            self._handover(s, "exit headcut reached the inlet")
        elif s.crater is not None and s.x_o <= s.crater.x2 + 1e-9:
            self._stop(s, "headcut_reached_crater", "the exit headcut reached the crater (not covered by the theory)")

    # ------------------------------------------------------------------ sealed state
    def _seal_snapshot(self, s: State, h: dict):
        cr, p = s.crater, s.pipe
        hcg = (s.hc.x_h, s.hc.z_h) if s.hc is not None else ()
        return dict(t=s.t, geom=(p.b, p.D, p.z_inv, s.x_in, s.x_o, cr.x1, cr.x2, cr.W) + hcg,
                    vol=(cr.V_fall, cr.V_pipe, cr.V_exp, cr.V_spoil, cr.W_c, s.V, cr.V_tank), z_s=s.z_s)

    def _spill_check(self, s: State, chk: dict) -> None:
        """crater_spilling (5.7a.11): the downstream entrance is blocked (a_open = 0, no pipe outflow), no
        check fails, and crater water leaves over the rim (Q_spill > 0). Logged on entry and exit; a run in
        this state with the geometry and water stationary for T_seal stops as 'crater_spilling'. Not
        sealed and not a hand-over: erosion of the rim belongs to the overtopping engine, not to piping."""
        h, cr, tol = chk["h"], s.crater, self.seal_tol
        spilling = (cr is not None and not chk["fail"] and cr.a_open() <= 0.0 and h["Q_out_cr"] == 0.0
                    and h["Q_spill"] > 0.0)
        if spilling != self._spilling:
            self._event(s, "spill_start" if spilling else "spill_end", Q_spill=h["Q_spill"],
                        z_rim=cr.z_rim if cr is not None else math.nan)
            self._spilling = spilling
        if not spilling:
            self._spill_ref = None
            return
        snap = self._seal_snapshot(s, h)
        ref = self._spill_ref
        if ref is None or any(abs(a - b) > tol["length"] for a, b in zip(snap["geom"], ref["geom"])) \
                or any(abs(a - b) > tol["volume"] for a, b in zip(snap["vol"], ref["vol"])) \
                or abs(snap["z_s"] - ref["z_s"]) > tol["length"]:
            self._spill_ref = snap
            return
        if s.t - ref["t"] >= self.T_seal:
            self._event(s, "crater_spilling", why=f"steady rim spill since t = {ref['t']:.1f} s", Q_spill=h["Q_spill"],
                        Q_up=h["Q_res"], z_rim=cr.z_rim, z_c=h["z_c"], spill_since=ref["t"])
            self.stopped = ("crater_spilling", f"blocked pipe, steady spill {h['Q_spill'] * 1e3:.3f} L/s over the "
                            f"rim (z {cr.z_rim:.3f} m) from t = {ref['t']:.1f} s")

    def _seal_check(self, s: State, chk: dict) -> None:
        """Stop with 'sealed' when, continuously for T_seal: the downstream entrance is blocked (a_open = 0,
        no outflow, no spill), no check fails, the pipe, ends and crater geometry do not change, and the
        water state (crater water, reservoir) is stationary with |Q| through the upstream reach below
        tolerance. Any change restarts the clock, so a temporary pause is never classified as sealed."""
        h, cr, tol = chk["h"], s.crater, self.seal_tol
        candidate = (cr is not None and not chk["fail"] and cr.a_open() <= 0.0 and h["Q_out_cr"] == 0.0
                     and h["Q_spill"] == 0.0 and h["Q_crest"] == 0.0 and abs(h["Q_res"]) < tol["flow"])
        if not candidate:
            self._seal_ref = None
            return
        snap = self._seal_snapshot(s, h)
        ref = self._seal_ref
        if ref is None or any(abs(a - b) > tol["length"] for a, b in zip(snap["geom"], ref["geom"])) \
                or any(abs(a - b) > tol["volume"] for a, b in zip(snap["vol"], ref["vol"])) \
                or abs(snap["z_s"] - ref["z_s"]) > tol["length"]:
            self._seal_ref = snap
            return
        if s.t - ref["t"] >= self.T_seal:
            self._event(s, "sealed", why=f"stationary since t = {ref['t']:.1f} s", Q_up=h["Q_res"],
                        Q_out=h["Q_out_cr"], a_open=cr.a_open(), seal_since=ref["t"])
            self.stopped = ("sealed", f"blocked and stationary from t = {ref['t']:.1f} s")

    # ------------------------------------------------------------------ budgets
    def water_error(self, s: State) -> float:
        Wc = s.crater.W_c if s.crater else 0.0
        rel = s.crater.released if s.crater else 0.0
        return (s.V + Wc + s.cum_out) - (self.V0 + s.cum_supply + rel)

    def solids_error(self, s: State) -> float:
        """Crater identity (5.18) plus the split of the crater export: V_exp = tank + left the domain
        (instant / tank modes; zero in the level mode, which exports nothing)."""
        cr = s.crater
        if cr is None:
            return 0.0
        e1 = (1 - cr.n) * cr.V_fall - (1 - cr.n_d) * (cr.V_db + cr.V_spoil + cr.V_exp)
        e2 = cr.V_exp - (cr.V_tank + cr.V_exp_out)     # system split, every treatment (5.7b.3)
        return e1 if abs(e1) >= abs(e2) else e2

    def _budget(self, s: State) -> None:
        scale = max(abs(self.V0), s.cum_supply, s.cum_out, 1.0)
        we = abs(self.water_error(s)) / scale
        se = abs(self.solids_error(s)) / max(s.crater.V_fall if s.crater else 1.0, 1e-12)
        self.max_water_err = max(self.max_water_err, we)
        self.max_solids_err = max(self.max_solids_err, se)
        if we > 1e-9 or se > 1e-9:
            raise RunStop("budget", f"t = {s.t:.3f} s: water {we:.2e}, solids {se:.2e} (relative)")

    # ------------------------------------------------------------------ time loop with event location
    def _record(self, s: State, chk: dict) -> None:
        if s.t + 1e-9 < self._next_rec:
            return
        self._next_rec = s.t + self.record_every
        h = chk["h"]
        r = dict(t=s.t, z_s=s.z_s, Q=h["Q_res"], Q_final=h["Q_final"], b=s.pipe.b, D=s.pipe.D, z_inv=s.pipe.z_inv,
                 x_in=s.x_in, x_o=s.x_o, min_M=chk["min_M"], water_err=self.water_error(s))
        if s.hc is not None:
            r.update(hc_stage=s.hc.stage, hc_x_h=s.hc.x_h, hc_z_h=s.hc.z_h, V_hc=s.hc.vol, V_hc_roof=s.hc.V_roof)
        if s.B_e is not None:
            po, qo = (s.pipe, h["fl_up"].Q) if s.crater is None else (s.pipe_dn, h["Q_out_cr"])
            y_n, tau_n = xw.notch_flow(qo, s.B_e, self.c.dam.zd, self.c.n_p)
            r.update(B_e=s.B_e, V_exit=s.V_exit, notch_depth=y_n, notch_tau=tau_n, b_out=po.b, D_out=po.D)
        rc = chk.get("rc") or chk.get("rc_up")
        if rc is not None:
            r.update(min_M_c=rc.min_M_c, x_star=rc.x_star, FS_A=rc.FS_A, lip_up=rc.lips[0], lip_dn=rc.lips[1])
        if s.crater is not None:
            cr = s.crater
            r.update(cr_x1=cr.x1, cr_x2=cr.x2, cr_W=cr.W, z_d=cr.z_d, z_c=h["z_c"], Q_out_cr=h["Q_out_cr"],
                     Q_spill=h["Q_spill"], a_open=cr.a_open(), V_tank=cr.V_tank, V_exp_out=cr.V_exp_out,
                     cum_spill=s.cum_spill, cum_out=s.cum_out)
        self.series.append(r)

    def run(self, t_end: float) -> "PipingRun":
        s = self.s
        try:
            chk = self.checks(s)
            if chk["fail"]:
                s = self.cascade(s)
                chk = self.checks(s)
            self._record(s, chk)
            while s.t < t_end - 1e-9 and not self.stopped:
                dt = min(self.dt, t_end - s.t)
                n = self.advance(s, dt)
                chk = self.checks(n)
                if chk["fail"] and _kinds(chk) <= self.onset:
                    # only boundaries that are already moving: continuous retreat, applied at the step end
                    n = self.cascade(n)
                    chk = self.checks(n) if not self.stopped else chk
                elif chk["fail"]:
                    self.onset |= _kinds(chk) & CONTINUOUS
                    lo, hi = 0.0, dt                       # failure-free at lo, failing at hi
                    while hi - lo > max(self.t_tol, 1e-9 * dt):
                        mid = 0.5 * (lo + hi)
                        if self.checks(self.advance(s, mid))["fail"]:
                            hi = mid
                        else:
                            lo = mid
                    n = self.advance(s, hi)
                    self._budget(n)
                    n = self.cascade(n)
                    chk = self.checks(n) if not self.stopped else chk
                self._budget(n)
                stage0 = s.hc.stage if s.hc is not None else None
                s = n
                self._headcut_log(s, stage0)
                self._record(s, chk)
                if not self.stopped:
                    self._seal_check(s, chk)
                if not self.stopped:
                    self._spill_check(s, chk)
        except RunStop as e:
            self._event(s, "stop_" + e.kind, why=str(e))
            self.stopped = (e.kind, str(e))
        self.s = s
        return self


def _blowout_at_outlet(rc: roof.RoofCheck):
    """Blow-out (M_b <= 0) on a reach joined to the outlet: (cut position, smallest M_b). Elsewhere a
    blow-out is not handled by the theory and stops the run (raised by the caller through min_M)."""
    xs, mb = rc.x, rc.M_b
    if not xs:
        return None, math.inf
    m = min((v for v in mb if not math.isnan(v)), default=math.inf)
    if m > 0:
        return None, m
    n = len(xs)
    if not (mb[-1] <= 0):
        raise RunStop("blowout_interior", f"blow-out away from the outlet (min M_b {m:.1f} Pa)")
    k = n - 1
    while k > 0 and mb[k - 1] <= 0:
        k -= 1
    if k == 0:
        return xs[0], m
    x0, m0, x1, m1 = xs[k], mb[k], xs[k - 1], mb[k - 1]
    return x0 + (x1 - x0) * (-m0) / (m1 - m0), m


def _reach_extent(rc: roof.RoofCheck, reach):
    """Zero crossings of M_c bracketing an interior failing reach (x_first, x_last)."""
    xa, xb = reach
    i, j = rc.x.index(xa), rc.x.index(xb)
    def zero(k_fail, k_ok):
        m0, m1 = rc.M_c[k_fail], rc.M_c[k_ok]
        if math.isinf(m0):
            return rc.x[k_fail]
        return rc.x[k_fail] + (rc.x[k_ok] - rc.x[k_fail]) * (-m0) / (m1 - m0)
    return zero(i, i - 1), zero(j, j + 1)


def _kinds(chk: dict) -> set:
    """Kinds of failure present in one check: continuous boundary motions and discrete events."""
    k = set()
    tol = 0.0
    if "F" in chk:
        F = chk["F"]
        if F.x_up is not None: k.add("inlet")
        if F.x_dn is not None: k.add("outlet")
        if F.interior or F.whole: k.add("crater_start")
        if chk["blow"][0] is not None: k.add("uplift")
        if chk["M_B"] <= 0: k.add("pushout_B")
    if "F_up" in chk:
        F = chk["F_up"]
        if F.x_up is not None: k.add("inlet")
        if F.x_dn is not None: k.add("crater_up")
        if F.interior or F.whole: k.add("discrete_up")
    if "F_dn" in chk:
        F = chk["F_dn"]
        if F.x_up is not None: k.add("crater_down")
        if F.x_dn is not None: k.add("outlet")
        if F.interior or F.whole: k.add("discrete_dn")
        if chk.get("blow", (None,))[0] is not None: k.add("uplift")
    if "walls" in chk:
        for w, (m, _) in chk["walls"].items():
            if m <= 0: k.add("wall_" + w)
    if "push" in chk:
        if chk["push"][0] <= 0 or chk["push"][1] <= 0: k.add("pushout_remnant")
    if not k:
        k.add("unclassified")
    return k


def timeline(run: "PipingRun") -> list:
    """Compact diagnostic timeline: every discrete event, and each run of the same continuous motion
    (inlet/outlet retreat, crater extension, uplift) merged into one line with its start, end, count and
    total distance."""
    out, cur = [], None
    for e in run.events:
        kind = e["type"]
        moving = kind in ("inlet_retreat", "outlet_retreat", "crater_extend_up", "crater_extend_down",
                          "outlet_uplift_C", "headcut_outlet_retreat")
        if moving and cur is not None and cur["type"] == kind:
            cur["t_end"] = e["t"]; cur["n"] += 1; cur["dist"] += e.get("dist", 0.0); cur["last"] = e
            continue
        if cur is not None:
            out.append(cur); cur = None
        if moving:
            cur = dict(type=kind, t=e["t"], t_end=e["t"], n=1, dist=e.get("dist", 0.0), first=e, last=e)
        else:
            out.append(dict(type=kind, t=e["t"], t_end=e["t"], n=1, dist=e.get("dist", 0.0), first=e, last=e))
    if cur is not None:
        out.append(cur)
    return out

