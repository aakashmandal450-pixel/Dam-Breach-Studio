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
from . import piping as pp
from . import roof
from .geometry import Dam
from .hydraulics import crest_overflow
from .stability_table import StabilityTable

GAMMA_W = roof.GAMMA_W
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
    cum_eroded: float = 0.0    # bulk soil eroded from the pipe walls (exported)
    V_end_up: float = 0.0      # bulk roof exported at inlet retreats
    V_end_dn: float = 0.0      # bulk roof exported at outlet retreats
    V_uplift: float = 0.0      # bulk cover removed by mechanism C
    released_out: float = 0.0  # pore water of fallen soil (enters W_c; tracked for the budget)


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
        self.V0 = V0
        self.events, self.series = [], []
        self.record_every, self._next_rec = record_every, 0.0
        self.stopped = None
        self.max_water_err = 0.0
        self.max_solids_err = 0.0
        self.passes_max = 0
        # A margin counts as failed below -M_tol. Without it, a retreat to the interpolated zero crossing
        # leaves M ~ 0 (+-round-off) at the new end and the cascade repeats zero-length retreats.
        self.M_tol = 1e-6 * case.soil.c_u0
        # Failure kinds whose onset has been event-located. Once an end or a crater edge has started to move,
        # its further motion is continuous (the margin at the new boundary is ~0 and keeps falling as the pipe
        # grows), so it is applied at the end of each step; the onset of every kind is located in the step.
        self.onset = set()

    # ------------------------------------------------------------------ hydraulics on a state
    def hyd(self, s: State) -> dict:
        c = self.c
        p = s.pipe
        HW = s.z_s - p.z_inv
        h = dict(z_c=math.nan, Q_out_cr=0.0, Q_spill=0.0, fl_dn=None)
        if s.crater is None:
            fl = pp.pipe_flow(HW, p.b, p.D, p.L, c.n_p)
            h.update(fl_up=fl, Q_res=fl.Q, Q_final=fl.Q)
        else:
            cr = s.crater
            z_c = cr.level()
            fl = pp.pipe_flow(HW, p.b, p.D, max(p.L, 0.0), c.n_p, h_t=max(z_c - p.z_inv, 0.0))
            ao = cr.a_open()
            z_o = max(cr.z_d, cr.z_inv)
            fl_dn = pp.pipe_flow(z_c - z_o, cr.b_p, ao, cr.L_down, c.n_p) if ao > 0 and cr.L_down > 0 else None
            Qo, Qs = cr.Q_out(z_c), cr.Q_spill(z_c)
            h.update(fl_up=fl, Q_res=fl.Q, z_c=z_c, Q_out_cr=Qo, Q_spill=Qs, fl_dn=fl_dn, Q_final=Qo + Qs)
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
        if n.pipe.L > 0:
            new_pipe, dV = pp.erode(n.pipe, eps, fl.w, fl.y, dt)
            n.pipe, n.cum_eroded = new_pipe, n.cum_eroded + dV
        p0 = s.pipe
        if n.crater is None:
            q_res = h["Q_res"]
        else:
            # crater water (5.22) by RK4, with the inflow from the upstream reach recomputed from the crater
            # level (tailwater coupling); the same averaged inflow leaves the reservoir, so the budget is exact
            cr = n.crater
            HW = s.z_s - p0.z_inv

            def rate(W):
                old = cr.W_c; cr.W_c = max(W, 0.0)
                zc = cr.level()
                qi = pp.pipe_flow(HW, p0.b, p0.D, max(p0.L, 0.0), c.n_p, h_t=max(zc - p0.z_inv, 0.0)).Q
                q = cr.Q_out(zc) + cr.Q_spill(zc)
                cr.W_c = old
                return qi - q, qi, q
            W0 = cr.W_c
            k1, i1, o1 = rate(W0); k2, i2, o2 = rate(W0 + 0.5 * dt * k1)
            k3, i3, o3 = rate(W0 + 0.5 * dt * k2); k4, i4, o4 = rate(W0 + dt * k3)
            vin = dt * (i1 + 2 * i2 + 2 * i3 + i4) / 6
            vout = dt * (o1 + 2 * o2 + 2 * o3 + o4) / 6
            W1 = W0 + vin - vout
            if W1 < 0.0:                                   # cannot drain more than it holds
                vout += W1; W1 = 0.0
            cr.W_c = W1
            n.cum_out += vout + h["Q_crest"] * dt
            q_res = vin / dt + h["Q_crest"]
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
        n.t = s.t + dt
        return n

    # ------------------------------------------------------------------ checks on one state
    def checks(self, s: State) -> dict:
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
                return s
            s = self.apply(s, chk)
            if self.stopped:
                return s
        raise RunStop("cascade_cap", f"no convergence in {self.max_passes} passes")

    def apply(self, s: State, chk: dict) -> State:
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
                self._event(s, f"wall_{k}", dist=d, H_w=walls[k][1])
        if walls["side"][0] <= 0.0:
            d = cr.retreat_wall("sides", S_r=self._sat(walls["side"][1], cr.z_d, s.z_s))
            self._event(s, "wall_sides", dist=d, H_w=walls["side"][1])
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

    # ------------------------------------------------------------------ helpers for apply
    def _sat(self, H, z_bot, z_ph):
        """Saturated fraction of a soil column of height H above z_bot (phreatic level z_ph), for S_r."""
        if H <= 0:
            return 0.0
        return min(max(z_ph - z_bot, 0.0), H) / H

    def _roof_fall(self, s: State, xa: float, xb: float):
        dam, z_cr, b = self.c.dam, s.pipe.z_cr, s.pipe.b
        A = ends.roof_area(dam, z_cr, xa, xb)
        A_dry = ends.roof_area(dam, max(s.z_s, z_cr), xa, xb)
        return b * A, (A - A_dry) / A if A > 0 else 0.0

    def _start_crater(self, s: State, xa: float, xb: float) -> State:
        c = self.c
        p = s.pipe
        cr = cm.Crater(c.dam, xa, xb, p.b, p.z_inv, p.D, p.b, s.x_o - xb, n=c.porosity, n_d=self.n_d,
                       n_p=c.n_p, pore_storage=c.pore_storage)
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
        Vr, Sr = self._roof_fall(s, xa, xb)
        cr.x1, cr.x2 = x1, x2
        cr.fall(Vr, S_r=Sr, new_pipe=cr.b_p * cr.a_p * (xb - xa))
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
        if cr is not None:
            e.update(cr_x1=cr.x1, cr_x2=cr.x2, cr_W=cr.W, z_d=cr.z_d, z_c=cr.level(), W_c=cr.W_c,
                     solids_err=self.solids_error(s))
        self.events.append(e)

    # ------------------------------------------------------------------ budgets
    def water_error(self, s: State) -> float:
        Wc = s.crater.W_c if s.crater else 0.0
        rel = s.crater.released if s.crater else 0.0
        return (s.V + Wc + s.cum_out) - (self.V0 + s.cum_supply + rel)

    def solids_error(self, s: State) -> float:
        cr = s.crater
        if cr is None:
            return 0.0
        return (1 - cr.n) * cr.V_fall - (1 - cr.n_d) * (cr.V_db + cr.V_spoil + cr.V_exp)

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
        rc = chk.get("rc") or chk.get("rc_up")
        if rc is not None:
            r.update(min_M_c=rc.min_M_c, x_star=rc.x_star, FS_A=rc.FS_A, lip_up=rc.lips[0], lip_dn=rc.lips[1])
        if s.crater is not None:
            cr = s.crater
            r.update(cr_x1=cr.x1, cr_x2=cr.x2, cr_W=cr.W, z_d=cr.z_d, z_c=h["z_c"], Q_out_cr=h["Q_out_cr"],
                     Q_spill=h["Q_spill"])
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
                s = n
                self._record(s, chk)
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
                          "outlet_uplift_C")
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

