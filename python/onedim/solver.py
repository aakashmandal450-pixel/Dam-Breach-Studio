"""Explicit first-order finite-volume solver for the 1-D shallow-water equations in channels of
arbitrary piecewise-linear section, with hydrostatic reconstruction on intersection sections,
HLL mass/momentum fluxes, an HLLC contact for a passive concentration, step-face forces and
point-implicit Manning friction.

Theory: Part 6, draft 3.1 (python/onedim/docs/theory/06_distributed_1d.md)
    reconstruction        (6.13)-(6.14), (6.14a) at width changes (decision 6-19)
    integral balance      (6.15), step faces (6.16), loading closure (6.16b)
    wave speeds           (6.17) and the dry-side speeds of 6.5.4
    HLL flux              (6.18), contact speed (6.19), concentration flux (6.20)
    time step             (6.21) incl. interface wave speeds, friction (6.22)
    budgets               (6.33), (6.34)

Phase B scope: fixed geometry. No erosion, no events, no reservoir storage (the reservoir
boundary holds a fixed level).
"""
from __future__ import annotations

import os

import numpy as np
from scipy.optimize import brentq

from .geometry import SectionSet, intersection

G = 9.81


class _BoundarySection:
    """Fast scalar section functions for a boundary cell: A, T exact (segment loop), Phi from a
    table on a quadratic grid (interpolation error ~1e-8 relative at 4000 nodes)."""

    def __init__(self, sset, hmax, n=4000):
        sec = sset.sections[0]
        self.y0 = list(sset.y0[0]); self.y1 = list(sset.y1[0])
        self.w0 = list(sset.w0[0]); self.s = list(sset.slope[0])
        self.hg = hmax * (np.arange(n + 1) / n) ** 2
        self.pg = sset.phi_h(self.hg, rows=np.zeros(n + 1, dtype=int))
        self.hmax = hmax

    def A(self, h):
        a = 0.0
        for y0, y1, w0, s in zip(self.y0, self.y1, self.w0, self.s):
            if h <= y0:
                break
            d = min(h, y1) - y0
            a += d * (w0 + 0.5 * s * d)
        return a

    def T(self, h):
        for y0, y1, w0, s in zip(self.y0, self.y1, self.w0, self.s):
            if y0 <= h < y1:
                return w0 + s * (h - y0)
        return self.w0[-1]

    def phi(self, h):
        if h > self.hmax:
            return float(self.pg[-1] + (h - self.hmax) * np.sqrt(G * self.T(self.hmax) / self.A(self.hmax)))
        return float(np.interp(h, self.hg, self.pg))


class Model:
    def __init__(self, cells, ds, manning_n=0.0, bc_left=None, bc_right=None, cfl=0.9,
                 h_dry=1e-6, face_rule="upwind_capped", recon="discharge_width", interface_coupling=None, c2_mode=None):
        self.N = len(cells)
        self.C = SectionSet(cells)
        self.ds = np.broadcast_to(np.asarray(ds, dtype=float), (self.N,)).copy()
        self.n = np.broadcast_to(np.asarray(manning_n, dtype=float), (self.N,)).copy()
        ifaces = [cells[0]] + [intersection(a, b) for a, b in zip(cells[:-1], cells[1:])] + [cells[-1]]
        self.I = SectionSet(ifaces)
        self.bc_left = bc_left or {"type": "wall"}
        self.bc_right = bc_right or {"type": "wall"}
        self.cfl, self.h_dry = cfl, h_dry
        # interface coupling at expansions: "none" (explicit, default) or "c2" (note 06, draft 2.1, §9;
        # experimental). The environment variables allow whole test suites to be run with C2.
        self.coupling = interface_coupling or os.environ.get("ONEDIM_COUPLING", "none")
        self.c2_mode = c2_mode or os.environ.get("ONEDIM_C2_MODE", "independent")   # or "chain"
        self.c2_blocks = 0; self.c2_fallback = 0; self.c2_skipped_ad = 0; self.c2_max_rel = 0.0
        self.recon = recon                      # "discharge_width" (6.14a, decision 6-19) or "velocity" ((6.14), comparison only)
        self.face_rule = face_rule              # "upwind_capped" (6.16b) or "own" (draft-1 rule)
        self.A = np.zeros(self.N); self.Q = np.zeros(self.N); self.AC = np.zeros(self.N)
        self.M = np.zeros(self.N)               # solids deposited by drying cells (store)
        self.A_dry = self.C.area_h(np.full(self.N, h_dry))
        self.t = 0.0
        self.nsteps = 0
        # budgets (cumulative)
        self.vol_in = 0.0; self.vol_out = 0.0; self.sol_in = 0.0; self.sol_out = 0.0
        self.min_area_seen = np.inf; self.clipped_volume = 0.0; self.min_ac_seen = np.inf
        self.max_step_imbalance = 0.0
        self.dt_limited_by_interface = 0
        self._C0 = self.C.subset([0]); self._CN = self.C.subset([self.N - 1])

    # ------------------------------------------------------------------ state helpers
    def set_stage(self, eta, U=0.0, C=0.0):
        eta = np.broadcast_to(np.asarray(eta, dtype=float), (self.N,))
        self.A = self.C.area(eta)
        self.Q = self.A * np.broadcast_to(U, (self.N,))
        self.AC = self.A * np.broadcast_to(C, (self.N,))

    def stage(self):
        return self.C.eta_from_area(self.A)

    def depth(self):
        return self.C.depth_from_area(self.A)

    def velocity(self):
        h = self.depth()
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(h > self.h_dry, self.Q / np.where(self.A > 0, self.A, 1.0), 0.0)

    def concentration(self):
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(self.A > self.A_dry, self.AC / np.where(self.A > 0, self.A, 1.0), 0.0)

    def water_volume(self):
        return float(np.sum(self.A * self.ds))

    def solids(self):
        return float(np.sum(self.AC * self.ds) + np.sum(self.M))

    # ------------------------------------------------------------------ boundaries
    def _ghost(self, side, eta_b, U_b, C_b, A_b):
        bc = self.bc_left if side == "L" else self.bc_right
        kind = bc["type"]
        sec = self._C0 if side == "L" else self._CN
        z = sec.z[0]
        if kind == "wall":
            return eta_b, -U_b, C_b
        if kind == "transmissive":
            return eta_b, U_b, C_b
        if kind == "discharge":                       # given Q (positive downstream)
            Uq = bc["Q"] / A_b if A_b > 0 else 0.0
            return eta_b, Uq, bc.get("C", 0.0)
        if kind == "stage":                           # given water level, velocity extrapolated
            return bc["eta"], U_b, C_b
        if kind == "reservoir":                       # still water at z_s, energy + characteristic
            return self._reservoir_ghost(sec, z, bc, eta_b, U_b, side)
        if kind == "critical":                        # free outfall (6.6.2)
            return self._outfall_ghost(sec, z, eta_b, U_b, C_b, A_b, side)
        raise ValueError(f"unknown boundary {kind}")

    def _bsec(self, side, hmax):
        key = (side, hmax)
        cache = self.__dict__.setdefault("_btab", {})
        if key not in cache:
            cache[key] = _BoundarySection(self._C0 if side == "L" else self._CN, hmax)
        return cache[key]

    def _reservoir_ghost(self, sec, z, bc, eta_b, U_b, side):
        zs, K = bc["z_s"], bc.get("K_u", 0.0)
        sgn = 1.0 if side == "L" else -1.0           # inflow direction
        hmax = zs - z
        if hmax <= 0:
            return z, 0.0, 0.0
        B = self._bsec(side, max(hmax, 1e-9) * 2.0)
        hb = max(eta_b - z, 0.0)
        Rout = sgn * U_b - B.phi(hb)                  # outgoing invariant, inflow-positive frame

        def f(h):
            u = Rout + B.phi(h)
            return zs - (z + h) - (1.0 + K) * u * u / (2 * G)

        def crit(h):
            return zs - (z + h) - (1.0 + K) * (G * B.A(h) / B.T(h)) / (2 * G)

        hc = brentq(crit, 1e-12 * hmax, hmax, xtol=1e-14)
        try:
            h = brentq(f, 1e-12 * hmax, hmax, xtol=1e-14)
        except ValueError:
            h = hc
        u = Rout + B.phi(h)
        if u * u > G * B.A(h) / B.T(h):              # choked: critical inflow (Part 1 (1.4)-(1.5))
            h = hc
            u = np.sqrt(G * B.A(h) / B.T(h))
        return z + h, sgn * u, 0.0

    def _outfall_ghost(self, sec, z, eta_b, U_b, C_b, A_b, side):
        sgn = 1.0 if side == "R" else -1.0
        hb = max(eta_b - z, 0.0)
        if hb <= self.h_dry:
            return eta_b, U_b, C_b
        B = self._bsec(side, self.bc_right.get("h_table", 20.0) if side == "R" else self.bc_left.get("h_table", 20.0))
        cb = np.sqrt(G * B.A(hb) / B.T(hb))
        if sgn * U_b >= cb:
            return eta_b, U_b, C_b                    # supercritical outflow: transmissive
        Rin = sgn * U_b + B.phi(hb)

        def f(h):
            return np.sqrt(G * B.A(h) / B.T(h)) + B.phi(h) - Rin

        h = brentq(f, 1e-12, max(hb * 4.0, 1e-6), xtol=1e-14)
        return z + h, sgn * np.sqrt(G * B.A(h) / B.T(h)), C_b

    # ------------------------------------------------------------------ one step
    def time_step(self):
        h = self.depth()
        wet = h > self.h_dry
        if not np.any(wet):
            return np.inf
        U = self.velocity()
        T = self.C.width_h(h)
        c = np.where(wet, np.sqrt(G * self.A / np.where(T > 0, T, 1.0)), 0.0)
        lam = np.where(wet, np.abs(U) + c, 0.0)
        return self.cfl * float(np.min(np.where(lam > 0, self.ds / np.where(lam > 0, lam, 1.0), np.inf)))

    def step(self, dt=None):
        N, I, C = self.N, self.I, self.C
        h = C.depth_from_area(self.A)
        eta = C.z + h
        wet = h > self.h_dry
        with np.errstate(divide="ignore", invalid="ignore"):
            U = np.where(wet, self.Q / np.where(self.A > 0, self.A, 1.0), 0.0)
            Cc = np.where(self.A > self.A_dry, self.AC / np.where(self.A > 0, self.A, 1.0), 0.0)
        if dt is None:
            dt = self.time_step()
        # ghost cells -------------------------------------------------------------------
        eL, uL, cL = self._ghost("L", eta[0], U[0], Cc[0], self.A[0])
        eR, uR, cR = self._ghost("R", eta[-1], U[-1], Cc[-1], self.A[-1])
        eta_x = np.concatenate([[eL], eta, [eR]])
        U_x = np.concatenate([[uL], U, [uR]])
        C_x = np.concatenate([[cL], Cc, [cR]])
        # reconstruction on the interface sections (6.14) --------------------------------
        etaL, etaR = eta_x[:-1], eta_x[1:]
        hL = np.maximum(etaL - I.z, 0.0); hR = np.maximum(etaR - I.z, 0.0)
        AL, AR = I.area_h(hL), I.area_h(hR)
        wl = hL > self.h_dry; wr = hR > self.h_dry
        AL = np.where(wl, AL, 0.0); AR = np.where(wr, AR, 0.0)
        UL = np.where(wl, U_x[:-1], 0.0); UR = np.where(wr, U_x[1:], 0.0)
        if self.recon == "discharge_width":
            # (6.14a), decision 6-19: carry the cell's discharge through a width change, scaled only by
            # the part of the cell's flow area above the interface bottom (blocked by a bed step)
            Cx = np.r_[0, np.arange(N), N - 1]
            Acell = np.r_[self.A[0], self.A, self.A[-1]]
            Qcell = Acell * U_x
            secL = Cx[:-1]; secR = Cx[1:]
            AbL = Acell[:-1] - C.area(I.z, rows=secL); AbR = Acell[1:] - C.area(I.z, rows=secR)
            with np.errstate(divide="ignore", invalid="ignore"):
                fL = np.where(Acell[:-1] > 0, np.clip(AbL, 0, None) / np.where(Acell[:-1] > 0, Acell[:-1], 1.0), 0.0)
                fR = np.where(Acell[1:] > 0, np.clip(AbR, 0, None) / np.where(Acell[1:] > 0, Acell[1:], 1.0), 0.0)
                QL = np.where(wl, Qcell[:-1] * fL, 0.0); QR = np.where(wr, Qcell[1:] * fR, 0.0)
                UL = np.where(wl, QL / np.where(AL > 0, AL, 1.0), 0.0); UR = np.where(wr, QR / np.where(AR > 0, AR, 1.0), 0.0)
            sQL, sQR = np.where(wl, fL, 0.0), np.where(wr, fR, 0.0)
        else:
            QL, QR = AL * UL, AR * UR
            Acx = np.r_[self.A[0], self.A, self.A[-1]]
            with np.errstate(divide="ignore", invalid="ignore"):
                sQL = np.where(wl & (Acx[:-1] > 0), AL / np.where(Acx[:-1] > 0, Acx[:-1], 1.0), 0.0)
                sQR = np.where(wr & (Acx[1:] > 0), AR / np.where(Acx[1:] > 0, Acx[1:], 1.0), 0.0)
        pL = G * I.i1_h(np.where(wl, hL, 0.0)); pR = G * I.i1_h(np.where(wr, hR, 0.0))
        TL, TR = I.width_h(hL), I.width_h(hR)
        cL_ = np.where(wl, np.sqrt(G * AL / np.where(TL > 0, TL, 1.0)), 0.0)
        cR_ = np.where(wr, np.sqrt(G * AR / np.where(TR > 0, TR, 1.0)), 0.0)
        # wave speeds (6.17) and dry sides ----------------------------------------------
        both = wl & wr
        sAL, sAR = np.sqrt(AL), np.sqrt(AR)
        with np.errstate(divide="ignore", invalid="ignore"):
            Ut = np.where(both, (sAL * UL + sAR * UR) / np.where(both, sAL + sAR, 1.0), 0.0)
        Am = 0.5 * (AL + AR)
        hm = I.depth_from_area(Am)
        Tm = I.width_h(hm)
        ct = np.where(both, np.sqrt(G * Am / np.where(Tm > 0, Tm, 1.0)), 0.0)
        SL = np.minimum(UL - cL_, Ut - ct)
        SR = np.maximum(UR + cR_, Ut + ct)
        rdry = wl & ~wr; ldry = wr & ~wl
        if np.any(rdry):
            idx = np.where(rdry)[0]
            ph = I.phi_h(hL[idx], rows=idx)
            SL[idx] = UL[idx] - cL_[idx]; SR[idx] = UL[idx] + ph
        if np.any(ldry):
            idx = np.where(ldry)[0]
            ph = I.phi_h(hR[idx], rows=idx)
            SL[idx] = UR[idx] - ph; SR[idx] = UR[idx] + cR_[idx]
        # positivity: the step must also respect the interface wave speeds, which exceed the cell
        # speeds |U| + c at dry fronts (S = U + Phi) -- the Audusse et al. (2004) condition
        smax = np.maximum(np.abs(SL), np.abs(SR))
        ds_if = np.minimum(np.r_[self.ds[0], self.ds], np.r_[self.ds, self.ds[-1]])
        with np.errstate(divide="ignore"):
            dt_if = self.cfl * float(np.min(np.where(smax > 0, ds_if / np.where(smax > 0, smax, 1.0), np.inf)))
        if dt > dt_if:
            dt = dt_if
            self.dt_limited_by_interface += 1
        # physical fluxes on the interface section
        FA_L, FA_R = QL, QR
        FQ_L = QL * UL + pL; FQ_R = QR * UR + pR
        FC_L = QL * C_x[:-1]; FC_R = QR * C_x[1:]
        # HLL (6.18), written so that identical states give exactly the physical flux
        span = SR - SL
        safe = np.where(span > 0, span, 1.0)
        a1 = (SR + SL) / safe; a2 = SL * SR / safe
        FA = 0.5 * (FA_L + FA_R) - 0.5 * a1 * (FA_R - FA_L) + a2 * (AR - AL)
        FQ = 0.5 * (FQ_L + FQ_R) - 0.5 * a1 * (FQ_R - FQ_L) + a2 * (QR - QL)
        sup_r = SL >= 0; sup_l = SR <= 0
        FA = np.where(sup_r, FA_L, np.where(sup_l, FA_R, FA))
        FQ = np.where(sup_r, FQ_L, np.where(sup_l, FQ_R, FQ))
        dry2 = ~wl & ~wr
        FA = np.where(dry2, 0.0, FA)
        FQ = np.where(dry2, pL * 0.0, FQ)            # both dry: zero flux, zero pressure
        # contact speed (6.19) and concentration flux (6.20)
        den = AR * (UR - SR) - AL * (UL - SL)
        with np.errstate(divide="ignore", invalid="ignore"):
            Sst = np.where(np.abs(den) > 0, (SL * AR * (UR - SR) - SR * AL * (UL - SL)) / np.where(np.abs(den) > 0, den, 1.0), 0.0)
        Cup = np.where(Sst >= 0, C_x[:-1], C_x[1:])
        Cup = np.where(sup_r, C_x[:-1], np.where(sup_l, C_x[1:], Cup))
        FC = np.where(dry2, 0.0, FA * Cup)
        # step-face loading (6.15)-(6.16b) ----------------------------------------------
        # cell i (0..N-1): right interface j = i+1, left interface j = i
        mR = FA[1:]; mL = FA[:-1]
        eta_nbR = eta_x[2:]; eta_nbL = eta_x[:-2]
        if self.face_rule == "upwind_capped":
            efR = np.where(mR < 0, np.minimum(eta, eta_nbR), eta)
            efL = np.where(mL > 0, np.minimum(eta, eta_nbL), eta)
        else:                                          # draft-1 rule: always the cell's own stage
            efR = eta.copy(); efL = eta.copy()
        jR = np.arange(1, N + 1); jL = np.arange(0, N)
        hfR_c = np.maximum(efR - C.z, 0.0); hfL_c = np.maximum(efL - C.z, 0.0)
        hfR_i = np.maximum(efR - I.z[jR], 0.0); hfL_i = np.maximum(efL - I.z[jL], 0.0)
        I1c_R = C.i1_h(hfR_c); I1c_L = C.i1_h(hfL_c)
        I1i_R = I.i1_h(np.where(hfR_i > self.h_dry, hfR_i, 0.0), rows=jR)
        I1i_L = I.i1_h(np.where(hfL_i > self.h_dry, hfL_i, 0.0), rows=jL)
        # corrected momentum fluxes seen by cell i; at rest (Phi - g I1_int) is exactly 0
        FQ_right = (FQ[1:] - G * I1i_R) + G * I1c_R
        FQ_left = (FQ[:-1] - G * I1i_L) + G * I1c_L
        # locally implicit coupling at expansion interfaces (C2, note 06 §9) --------------
        if self.coupling == "c2" and N > 1:
            FA, FC, FQ_right, FQ_left = self._c2(dt, FA, FC, Cup, FQ_right, FQ_left, SL, SR, a2,
                                                 sQL, sQR, UL, UR, eta, h, U, efL, efR)
        # update (6.12) ------------------------------------------------------------------
        r = dt / self.ds
        A_new = self.A - r * (FA[1:] - FA[:-1])
        Q_new = self.Q - r * (FQ_right - FQ_left)
        AC_new = self.AC - r * (FC[1:] - FC[:-1])
        # per-step water imbalance (6.33 per-step diagnostic)
        dW = np.sum((A_new - self.A) * self.ds) - dt * (FA[0] - FA[-1])
        turn = np.sum(np.abs(A_new - self.A) * self.ds) + dt * (abs(FA[0]) + abs(FA[-1]))
        if turn > 0:
            self.max_step_imbalance = max(self.max_step_imbalance, abs(dW) / max(turn, 1e-9))
        self.min_area_seen = min(self.min_area_seen, float(A_new.min()))
        self.min_ac_seen = min(self.min_ac_seen, float(AC_new.min()))
        neg = A_new < 0
        if np.any(neg):
            self.clipped_volume += float(-np.sum(A_new[neg] * self.ds[neg]))
            A_new[neg] = 0.0
        # friction, point-implicit (6.22)
        h_new = C.depth_from_area(A_new)
        wet_new = h_new > self.h_dry
        if np.any(self.n > 0):
            P = C.perimeter_h(h_new)
            with np.errstate(divide="ignore", invalid="ignore"):
                R = np.where(wet_new, A_new / np.where(P > 0, P, 1.0), 1.0)
                k = np.where(wet_new, dt * G * self.n ** 2 * np.abs(Q_new) /
                             (np.where(A_new > 0, A_new, 1.0) * R ** (4.0 / 3.0)), 0.0)
            Q_new = Q_new / (1.0 + k)
        Q_new = np.where(wet_new, Q_new, 0.0)
        # drying: suspended solids go to the store (6.7.4)
        dry_now = A_new <= self.A_dry
        if np.any(dry_now & (AC_new != 0)):
            self.M[dry_now] += AC_new[dry_now] * self.ds[dry_now]
            AC_new[dry_now] = 0.0
        # budgets
        self.vol_in += dt * FA[0]; self.vol_out += dt * FA[-1]
        self.sol_in += dt * FC[0]; self.sol_out += dt * FC[-1]
        self.A, self.Q, self.AC = A_new, Q_new, AC_new
        self.t += dt; self.nsteps += 1
        self.last = dict(FA=FA, FQ=FQ, FC=FC, SL=SL, SR=SR, dt=dt,
                         WR=G * (I1c_R - I1i_R), WL=G * (I1c_L - I1i_L), etaf_R=efR, etaf_L=efL)
        return dt

    def _c2(self, dt, FA, FC, Cup, FQ_right, FQ_left, SL, SR, a2, sQL, sQR, UL, UR, eta, h, U, efL, efR):
        """C2 (note 06, draft 2.1, §§9-9.5): at each interior interface where (6.16b) loads the receiving
        (wide) cell's face at the narrow neighbour's stage, solve the two coupling links implicitly.
        Corrections are made to the shared interface fluxes before any cell is updated (§9.3a)."""
        N, C, I = self.N, self.C, self.I
        r = dt / self.ds
        span = SR - SL
        safe = np.where(span > 0, span, 1.0)
        al = SR / safe; be = -SL / safe; aa2 = np.abs(a2)
        T = C.width_h(h)
        hmin = 10.0 * self.h_dry
        blocks = []
        for k in range(1, N):
            if not (SL[k] < 0.0 < SR[k]) or FA[k] == 0.0 or self.face_rule != "upwind_capped":
                continue
            if FA[k] > 0:
                n, w = k - 1, k
            else:
                n, w = k, k - 1
            if not (eta[n] < eta[w]) or h[n] <= hmin or h[w] <= hmin or T[n] <= 0:
                continue
            ef = efL[w] if w == k else efR[w]
            if ef != eta[n]:
                continue
            An = float(I.area(np.array([eta[n]]), rows=[k])[0])
            Awf = float(C.area(np.array([eta[n]]), rows=[w])[0])
            if not (Awf > An * (1.0 + 1e-9)) or An <= 0:
                continue                                     # no width change: no A_w term, no loop
            if w == k:                                       # flow to the right, wide cell on the right
                c_a = be[k] * sQR[k]; omega = al[k]; tau = 1.0; sig_n = -r[n]; sig_w = r[w]
                D1 = aa2[k] + aa2[k - 1]
                D2 = (2 * al[k + 1] * U[w] + aa2[k + 1]) - sQR[k] * (2 * be[k] * UR[k] - aa2[k])
            else:                                            # flow to the left, wide cell on the left
                c_a = al[k] * sQL[k]; omega = be[k]; tau = -1.0; sig_n = r[n]; sig_w = -r[w]
                D1 = aa2[k] + aa2[k + 1]
                D2 = sQL[k] * (2 * al[k] * UL[k] + aa2[k]) + aa2[k - 1] - 2 * be[k - 1] * U[w]
            a_ = 1.0 - r[n] * D1; d_ = 1.0 - r[w] * D2
            if abs(a_) > 1.0 or abs(d_) > 1.0:
                self.c2_skipped_ad += 1
                continue
            Phat = G * (omega * An + (Awf - An))
            blocks.append(dict(k=k, n=n, w=w, c_a=c_a, sig_n=sig_n, sig_w=sig_w, kappa=tau * r[w] * Phat,
                               Tn=float(T[n]), An=An, Awf=Awf, omega=omega))
        if not blocks:
            return FA, FC, FQ_right, FQ_left
        dA_E = -r * (FA[1:] - FA[:-1])
        dQ_E = -r * (FQ_right - FQ_left)
        nb = len(blocks)

        def touch(bp, cell):
            if cell == bp["n"]:
                return bp["sig_n"] * bp["c_a"]
            if cell == bp["w"]:
                return bp["sig_w"] * bp["c_a"]
            return 0.0

        M = np.eye(nb); rhs = np.zeros(nb)
        for i, b in enumerate(blocks):
            rhs[i] = dQ_E[b["w"]] + b["kappa"] * dA_E[b["n"]] / b["Tn"]
            others = range(nb) if self.c2_mode == "chain" else [i]
            for j in others:
                M[i, j] -= b["kappa"] / b["Tn"] * touch(blocks[j], b["n"])
        x = np.linalg.solve(M, rhs)
        FA = FA.copy(); FC = FC.copy(); FQ_right = FQ_right.copy(); FQ_left = FQ_left.copy()
        corr = []
        for i, b in enumerate(blocks):
            others = range(nb) if self.c2_mode == "chain" else [i]
            dAn = dA_E[b["n"]] + sum(touch(blocks[j], b["n"]) * x[j] for j in others)
            deta = dAn / b["Tn"]
            dFA = b["c_a"] * x[i]
            dFs = b["omega"] * G * b["An"] * deta            # shared interface-pressure correction
            dW = G * (b["Awf"] - b["An"]) * deta             # step-face correction, wide cell only
            corr.append((dFA, dFs, dW))
        def apply(i, sgn):
            b = blocks[i]; k, w = b["k"], b["w"]
            dFA, dFs, dW = corr[i]
            FA[k] += sgn * dFA; FC[k] += sgn * dFA * Cup[k]
            FQ_right[k - 1] += sgn * dFs; FQ_left[k] += sgn * dFs
            if w == k:
                FQ_left[w] += sgn * dW
            else:
                FQ_right[w] += sgn * dW
        for i in range(nb):
            apply(i, +1.0)
        # positivity of both cells sharing each corrected flux; revert whole blocks (§9.5)
        A_try = self.A - r * (FA[1:] - FA[:-1])
        for i, b in enumerate(blocks):
            if A_try[b["n"]] < self.A_dry or A_try[b["w"]] < self.A_dry:
                apply(i, -1.0); self.c2_fallback += 1
        self.c2_blocks += nb
        fmax = max(float(np.max(np.abs(FA))), 1e-30)
        self.c2_max_rel = max(self.c2_max_rel, max(abs(c[0]) for c in corr) / fmax)
        self.last_c2 = dict(blocks=blocks, x=x, corr=corr)
        return FA, FC, FQ_right, FQ_left

    def run(self, t_end, max_steps=10 ** 8, callback=None, every=0):
        while self.t < t_end - 1e-12 and self.nsteps < max_steps:
            dt = min(self.time_step(), t_end - self.t)
            self.step(dt)                       # may take a shorter step (interface speeds)
            if callback and every and self.nsteps % every == 0:
                callback(self)
        return self

    def run_to_steady(self, tol=1e-10, check_every=200, t_max=1e5, max_steps=5 * 10 ** 6):
        """Advance until the relative change of A and Q over `check_every` steps is below tol."""
        prevA, prevQ = self.A.copy(), self.Q.copy()
        while self.t < t_max and self.nsteps < max_steps:
            for _ in range(check_every):
                self.step()
            dA = np.max(np.abs(self.A - prevA)) / max(np.max(np.abs(self.A)), 1e-12)
            dQ = np.max(np.abs(self.Q - prevQ)) / max(np.max(np.abs(self.Q)), 1e-12)
            self.steady_residual = (float(dA), float(dQ))
            if dA < tol and dQ < tol:
                return True
            prevA, prevQ = self.A.copy(), self.Q.copy()
        return False

    def water_error(self, V0):
        """Cumulative relative water error (6.33), with the flux budget."""
        E = self.water_volume() - V0 - (self.vol_in - self.vol_out)
        scale = max(V0 + max(self.vol_in, 0.0), 1e-9)
        return abs(E) / scale

    def solids_error(self, S0):
        E = self.solids() - S0 - (self.sol_in - self.sol_out)
        return abs(E) / max(S0 + max(self.sol_in, 0.0), 1e-12)
