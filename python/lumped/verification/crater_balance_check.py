"""Independent checks of the crater equations of Theory Part 5, §5.7a (draft 5.1), before any engine code.

A small, self-contained implementation of (5.17)-(5.25): crater geometry from the void identity, the
storage curve with pore water, the level, the continuous downstream obstruction, spill, the water
balance and the wet-wall criterion with its domain guard. It is a reference for the engine, not part of
it. Each test prints PASS/FAIL; the exit code is the number of failures.

Checks (review of draft 5.1):
  1. wet-wall validity domain enforced (no extrapolation, no artificial stability)
  2. pore-water accounting: no double counting; wall water from the level z_c, not the stored volume
  3. continuous obstruction: open / partly obstructed / closed; Q_out -> 0 smoothly; one debris geometry
  4. water balance: no inflow; inflow without outflow; debris falling into the crater; spill over the rim
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field

G = 9.81
FAILS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   ({detail})" if detail else ""), flush=True)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- wet-wall criterion (5.17)
class DomainError(ValueError):
    pass


WALL_DOMAIN = dict(r=(0.4, 0.6), xi=(0.0, 1.0), rho_p=(0.0, 0.5))


def wall_critical_height(c0, gam, gw, rho, h_w, H_w, tension=True):
    """H_c of (5.17). Raises DomainError outside the checked range (§5.7a.5, validity domain)."""
    xi = h_w / H_w if H_w > 0 else 0.0
    rho_p = rho * H_w / c0
    r = gw / gam
    if not (WALL_DOMAIN["xi"][0] <= xi <= WALL_DOMAIN["xi"][1]):
        raise DomainError(f"xi = h_w/H_w = {xi:g} outside [0, 1]")
    if xi > 0 and not (WALL_DOMAIN["r"][0] <= r <= WALL_DOMAIN["r"][1]):
        raise DomainError(f"gamma_w/gamma = {r:g} outside the checked range [0.4, 0.6]")
    if not (WALL_DOMAIN["rho_p"][0] <= rho_p <= WALL_DOMAIN["rho_p"][1]):
        raise DomainError(f"rho' = rho H_w/c_u0 = {rho_p:g} outside the checked range [0, 0.5]")
    den = gam - gw * xi * xi - 2.0 * rho
    if den <= 0:
        raise DomainError(f"denominator gamma - gamma_w xi^2 - 2 rho = {den:g} <= 0")
    return (3.776 if tension else 2.0) * c0 / den


# --------------------------------------------------------------------------- pipe flow (5.2)-(5.4)
def pipe_flow(HW, b, D, L, n_p=0.016, K_u=0.05, K_d=1.0, h_t=0.0):
    """Discharge of a horizontal rectangular pipe, entrance height D, headwater HW above its invert."""
    if D <= 0 or HW <= 0 or b <= 0:
        return 0.0
    if HW <= 1.5 * D:
        y = 2.0 * HW / 3.0
        Qi = b * y * math.sqrt(2 * G * (HW - y) / (1 + K_u))
        w = 0.0
    else:
        y = D
        Qi = b * D * math.sqrt(2 * G * (HW - D / 2) / (1 + K_u))
        w = 1.0
    A = b * y
    P = b + 2 * y + w * b
    R = A / P
    f = 8 * G * n_p ** 2 / R ** (1 / 3)
    head = HW - max(y / 2, h_t)
    Qo = A * math.sqrt(2 * G * max(head, 0.0) / (K_u + K_d + f * L / (4 * R))) if head > 0 else 0.0
    return min(Qi, Qo)


# --------------------------------------------------------------------------- crater
@dataclass
class Crater:
    ell: float          # crater length x_2 - x_1 (m)
    W: float            # crater width (m)
    zg: float           # mean ground elevation over the footprint (m)
    z_rim: float        # lowest rim elevation (m)
    z_inv: float        # pipe invert (m)
    a_p: float          # pipe height (m)
    b_p: float          # pipe width (m)
    L_down: float       # downstream pipe length (m)
    n: float = 0.35     # intact porosity
    n_d: float = 0.35   # debris porosity
    V_fall: float = 0.0
    V_pipe: float = 0.0
    V_exp: float = 0.0
    V_spoil: float = 0.0   # bulk debris set beside the crater when it would overfill it (§5.7)
    W_c: float = 0.0    # total crater water (free + pore)
    released: float = 0.0   # cumulative pore water brought in by fallen soil
    pore_storage: bool = True

    # geometry (5.18)-(5.19)
    @property
    def kappa(self):
        return (1 - self.n) / (1 - self.n_d)

    @property
    def A_c(self):
        return self.ell * self.W

    @property
    def V_open(self):
        return self.V_pipe - (self.kappa - 1) * self.V_fall + self.V_exp + self.V_spoil

    @property
    def z_d(self):
        return self.zg - self.V_open / self.A_c

    @property
    def V_db(self):
        return self.kappa * self.V_fall - self.V_exp - self.V_spoil

    @property
    def z_cr(self):
        return self.z_inv + self.a_p

    # storage curve (5.20)
    def V_p(self, z):
        if not self.pore_storage or self.V_db <= 0:
            return 0.0
        span = self.z_d - self.z_inv
        frac = 1.0 if span <= 0 else min(max((z - self.z_inv) / span, 0.0), 1.0)
        return self.n_d * self.V_db * frac

    def S(self, z):
        return self.V_p(z) + self.A_c * max(z - self.z_d, 0.0)

    def level(self):
        """z_c = S^-1(W_c) by bisection (S is continuous and non-decreasing)."""
        if self.W_c <= 0:
            return self.z_inv
        lo, hi = self.z_inv, max(self.zg, self.z_d) + 1.0
        while self.S(hi) < self.W_c:
            hi += 10.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if self.S(mid) < self.W_c:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def free_water(self):
        return self.A_c * max(self.level() - self.z_d, 0.0)

    # outflows (5.21), (5.25)
    def a_open(self):
        return min(max(self.z_cr - max(self.z_d, self.z_inv), 0.0), self.a_p)

    def Q_out(self, z_c=None):
        z_c = self.level() if z_c is None else z_c
        ao = self.a_open()
        z_o = max(self.z_d, self.z_inv)        # bottom of the open part of the entrance
        return pipe_flow(z_c - z_o, self.b_p, ao, self.L_down)

    def Q_spill(self, z_c=None):
        z_c = self.level() if z_c is None else z_c
        return 1.705 * self.W * (z_c - self.z_rim) ** 1.5 if z_c > self.z_rim else 0.0

    def wall_water_depth(self, z_g):
        return max(0.0, min(self.level(), z_g) - self.z_d)

    # events
    def fall(self, dV, S_r=1.0, new_pipe=0.0):
        """Soil of intact bulk volume dV falls into the crater, bringing S_r n dV of pore water."""
        self.V_fall += dV
        self.V_pipe += new_pipe
        if self.V_open < 0:                     # bulked debris would overfill the crater: excess to spoil
            self.V_spoil += -self.V_open
        if self.pore_storage:
            w = S_r * self.n * dV
            self.W_c += w
            self.released += w


def integrate(cr: Crater, Q_in, T, dt=1.0):
    """RK4 on dW_c/dt = Q_in - Q_out - Q_spill (5.22); returns cumulative in/out/spill."""
    cin = cout = cspill = 0.0
    t = 0.0

    def rate(W):
        old = cr.W_c
        cr.W_c = W
        zc = cr.level()
        qo, qs = cr.Q_out(zc), cr.Q_spill(zc)
        cr.W_c = old
        return Q_in - qo - qs, qo, qs

    while t < T - 1e-12:
        h = min(dt, T - t)
        W0 = cr.W_c
        k1, o1, s1 = rate(W0)
        k2, o2, s2 = rate(W0 + 0.5 * h * k1)
        k3, o3, s3 = rate(W0 + 0.5 * h * k2)
        k4, o4, s4 = rate(W0 + h * k3)
        cr.W_c = max(W0 + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6, 0.0)
        cin += Q_in * h
        cout += h * (o1 + 2 * o2 + 2 * o3 + o4) / 6
        cspill += h * (s1 + 2 * s2 + 2 * s3 + s4) / 6
        t += h
    return cin, cout, cspill


def base_crater(**kw):
    """A 4 m long crater over a 1 m pipe under 5 m of cover, roof collapsed, as after the first collapse.
    With n_d = n the crater is a_p = 1 m deep (debris at 9.0 m), and the lowest rim is at 9.8 m."""
    d = dict(ell=4.0, W=1.0, zg=10.0, z_rim=9.8, z_inv=4.0, a_p=1.0, b_p=1.0, L_down=20.0)
    d.update(kw)
    cr = Crater(**d)
    cr.V_pipe = cr.b_p * cr.a_p * cr.ell            # pipe void in the reach
    cover = cr.zg - cr.z_cr
    cr.fall(cr.b_p * cover * cr.ell, S_r=1.0)       # roof block over the reach, saturated
    return cr


def main():
    print("== 1. Wet-wall validity domain (5.17)")
    Hc = wall_critical_height(20.0, 20.0, 9.81, 0.0, 0.0, 3.0)
    check("dry wall, constant strength: H_c = 3.776 c/gamma", abs(Hc - 3.776) < 1e-12, f"{Hc:.4f} m")
    Hf = wall_critical_height(20.0, 20.0, 9.81, 0.0, 3.0, 3.0)
    check("full crater: H_c = 3.776 c/(gamma - gamma_w)", abs(Hf - 3.776 * 20 / (20 - 9.81)) < 1e-12, f"{Hf:.4f} m")
    Ht = wall_critical_height(20.0, 20.0, 9.81, 0.0, 0.0, 3.0, tension=False)
    check("tension cut-off case uses 2 c/gamma", abs(Ht - 2.0) < 1e-12, f"{Ht:.4f} m")
    for label, args in [("gamma_w/gamma = 0.3 with water", (20.0, 32.7, 9.81, 0.0, 1.0, 3.0)),
                        ("rho' = 0.6", (20.0, 20.0, 9.81, 4.0, 0.0, 3.0)),
                        ("xi > 1", (20.0, 20.0, 9.81, 0.0, 4.0, 3.0)),
                        ("non-positive denominator (rho' in range, weak gamma)", (20.0, 6.0, 0.0, 3.0, 0.0, 3.0))]:
        try:
            wall_critical_height(*args)
            check(f"rejects {label}", False, "no error raised")
        except DomainError as e:
            check(f"rejects {label}", True, str(e))
    try:
        wall_critical_height(20.0, 32.7, 9.81, 0.0, 0.0, 3.0)
        check("dry wall: gamma_w/gamma irrelevant, not rejected", True)
    except DomainError as e:
        check("dry wall: gamma_w/gamma irrelevant, not rejected", False, str(e))

    print("== 2. Pore-water accounting")
    cr = base_crater()
    check("void identity: crater depth = a_p after roof collapse (n_d = n)", abs((cr.zg - cr.z_d) - cr.a_p) < 1e-12,
          f"depth {cr.zg - cr.z_d:.6f} m")
    # the roof was saturated: it brought exactly its own pore water, which sits in the debris pores
    check("saturated roof brings exactly the water its pores hold (n_d = n)",
          abs(cr.W_c - cr.n_d * cr.V_db) < 1e-9, f"W_c {cr.W_c:.6f}, pore space {cr.n_d * cr.V_db:.6f}")
    zc = cr.level()
    check("that water fills the pores up to the debris surface, with no free water",
          abs(zc - cr.z_d) < 1e-7 and cr.free_water() < 1e-6, f"z_c {zc:.6f}, z_d {cr.z_d:.6f}")
    check("S(z_c) = W_c (level inversion)", abs(cr.S(zc) - cr.W_c) < 1e-9)
    # water only in the pores: no pressure on the exposed wall
    cr2 = base_crater(); cr2.W_c *= 0.5
    check("water held in the pores does not load the wall (h_w from z_c, not W_c)",
          cr2.wall_water_depth(cr2.zg) == 0.0 and cr2.W_c > 0, f"W_c {cr2.W_c:.3f} m3, h_w 0")
    # double counting: a second saturated fall into standing water, n_d = n
    cr3 = base_crater(); cr3.W_c += 2.0                       # 2 m3 of free water
    fw0, zd0, Wc0 = cr3.free_water(), cr3.z_d, cr3.W_c
    cr3.fall(1.5, S_r=1.0)
    check("saturated soil falling into water (n_d = n): free water unchanged",
          abs(cr3.free_water() - fw0) < 1e-6, f"before {fw0:.6f}, after {cr3.free_water():.6f} m3")
    check("... and W_c rose by exactly the released pore water n dV (counted once)",
          abs(cr3.W_c - Wc0 - cr3.n * 1.5) < 1e-12)
    # bulking: n_d > n draws the extra pore space from the free water
    cr4 = base_crater(n_d=0.45); cr4.V_pipe += 4.0           # a deeper crater, so bulked debris stays below the rim
    cr4.W_c = cr4.n_d * cr4.V_db + 0.2                       # pores full plus 0.2 m3 of free water
    fw0 = cr4.free_water()
    check("(setup) bulked crater holds free water below the rim", fw0 > 0 and cr4.level() < cr4.z_rim,
          f"free {fw0:.3f} m3, z_c {cr4.level():.3f}, z_d {cr4.z_d:.3f}, rim {cr4.z_rim}")
    dV = 0.5
    cr4.fall(dV, S_r=1.0)
    expect = (cr4.n_d - cr4.n) / (1 - cr4.n_d) * dV           # extra pore space of the bulked debris
    check("bulked debris (n_d > n): free water falls by the extra pore space only",
          abs((fw0 - cr4.free_water()) - expect) < 1e-6, f"drop {fw0 - cr4.free_water():.6f}, expected {expect:.6f} m3")

    cs = base_crater(n_d=0.50)                               # strong bulking in a 1 m deep crater
    Vs0 = (1 - cs.n) * cs.V_fall
    check("bulked debris that would overfill the crater goes to spoil: debris surface stays at or below ground",
          cs.z_d <= cs.zg + 1e-12 and cs.V_spoil > 0, f"z_d {cs.z_d:.4f}, ground {cs.zg}, spoil {cs.V_spoil:.3f} m3")
    Vs_debris = (1 - cs.n_d) * (cs.V_db + cs.V_spoil)
    check("... and the solids are conserved (debris + spoil = fallen solids)", abs(Vs_debris - Vs0) < 1e-12)

    print("== 3. Continuous obstruction (5.25)")
    cr = base_crater(); cr.W_c += 0.5 * (cr.z_rim - cr.z_d) * cr.A_c
    zc = cr.level()
    q_full = pipe_flow(zc - cr.z_inv, cr.b_p, cr.a_p, cr.L_down)

    def q_at(z_d):
        c = Crater(**{k: getattr(cr, k) for k in ("ell", "W", "zg", "z_rim", "z_inv", "a_p", "b_p", "L_down", "n", "n_d")})
        # place the debris surface at z_d through the same void identity (V_open from the footprint)
        c.V_pipe = (c.zg - z_d) * c.A_c
        return c.Q_out(zc), c.a_open()

    q0, a0 = q_at(cr.z_inv - 0.5)
    check("fully open (debris below the invert): Q_out = full-pipe flow", abs(q0 - q_full) < 1e-12 and a0 == cr.a_p,
          f"{q0:.4f} m3/s")
    zs = [cr.z_inv - 0.5 + i * 0.001 for i in range(int((cr.z_cr + 0.5 - (cr.z_inv - 0.5)) / 0.001) + 1)]
    qs = [q_at(z)[0] for z in zs]
    mono = all(qs[i + 1] <= qs[i] + 1e-12 for i in range(len(qs) - 1))
    jump = max(abs(qs[i + 1] - qs[i]) for i in range(len(qs) - 1))
    check("Q_out non-increasing as the debris rises", mono)
    check("no jump: largest change per 1 mm of debris rise < 2 % of full flow", jump < 0.02 * q_full,
          f"{100 * jump / q_full:.3f} %")
    qp, ap_ = q_at(cr.z_inv + 0.5 * cr.a_p)
    check("partly obstructed (half open): 0 < Q_out < full", 0 < qp < q_full, f"{qp:.4f} m3/s, a_open {ap_:.2f} m")
    qe, _ = q_at(cr.z_cr - 1e-4)
    check("Q_out -> 0 smoothly as the opening closes (a_open = 0.1 mm)", qe < 1e-3 * q_full, f"{qe:.2e} m3/s")
    qc, ac = q_at(cr.z_cr + 0.2)
    check("completely closed (debris above the crown): Q_out = 0, a_open = 0", qc == 0.0 and ac == 0.0)
    c5 = base_crater(n_d=0.45); c5.W_c = c5.n_d * c5.V_db
    zd_before, ao_before, S_before = c5.z_d, c5.a_open(), c5.S(c5.zg)
    c5.fall(2.0, S_r=0.0, new_pipe=0.0)
    check("one debris geometry: a fall changes z_d, the opening and the storage curve together",
          c5.z_d != zd_before and c5.S(c5.zg) != S_before and c5.a_open() == min(max(c5.z_cr - max(c5.z_d, c5.z_inv), 0), c5.a_p))

    print("== 4. Crater water balance (5.22)")
    # 4a no inflow, blocked
    cr = base_crater(); cr.W_c += 2.0
    W0, z0 = cr.W_c, cr.level()
    cin, cout, csp = integrate(cr, 0.0, 600.0, 5.0)
    check("no inflow, outlet blocked: W_c and z_c unchanged", abs(cr.W_c - W0) < 1e-12 and abs(cr.level() - z0) < 1e-9)
    # 4b inflow without outflow
    cr = base_crater(); W0 = cr.W_c
    cin, cout, csp = integrate(cr, 0.002, 600.0, 5.0)             # 1.2 m3, below the 3.2 m3 to the rim
    err = cr.W_c - (W0 + cin - cout - csp)
    check("inflow without outflow: W_c = W_c0 + Q_in t, no spill below the rim",
          abs(cr.W_c - (W0 + 0.002 * 600)) < 1e-9 and csp == 0.0 and cout == 0.0 and cr.level() < cr.z_rim,
          f"z_c {cr.level():.3f} m, budget error {err:.1e} m3")
    # 4c debris falling into the crater mid-run
    cr = base_crater(n_d=0.45); cr.W_c = cr.n_d * cr.V_db; W0 = cr.W_c
    rel0 = cr.released
    a1 = integrate(cr, 0.002, 300.0, 5.0)
    cr.fall(1.0, S_r=1.0)
    a2 = integrate(cr, 0.002, 300.0, 5.0)
    cin = a1[0] + a2[0]; cout = a1[1] + a2[1]; csp = a1[2] + a2[2]
    rel_after_start = cr.released - rel0
    err = cr.W_c - (W0 + cin - cout - csp + rel_after_start)
    check("debris falling into the crater: budget closes with the released pore water", abs(err) < 1e-9,
          f"budget error {err:.1e} m3")
    # 4d spill over the rim, run to steady state
    cr = base_crater(); W0 = cr.W_c
    Qin = 0.05
    cin, cout, csp = integrate(cr, Qin, 20000.0, 2.0)
    zc = cr.level()
    z_ss = cr.z_rim + (Qin / (1.705 * cr.W)) ** (2 / 3)
    err = cr.W_c - (W0 + cin - cout - csp)
    check("spill: steady level = rim + (Q_in / 1.705 W)^(2/3)", abs(zc - z_ss) < 1e-4, f"{zc:.5f} vs {z_ss:.5f} m")
    check("spill: Q_spill -> Q_in at steady state", abs(cr.Q_spill() - Qin) < 1e-5 * max(Qin, 1))
    check("spill: budget closes", abs(err) < 1e-8, f"budget error {err:.1e} m3")
    # 4e partly open downstream pipe: drains, budget closes
    cr = base_crater(zg=10.0, z_inv=4.0); cr.V_pipe += 18.0      # deeper crater: debris at mid-height of the pipe
    check("(setup) debris surface below the crown, entrance partly open", cr.z_inv < cr.z_d < cr.z_cr,
          f"z_d {cr.z_d:.2f} m, a_open {cr.a_open():.2f} m")
    cr.W_c += 8.0; W0 = cr.W_c
    cin, cout, csp = integrate(cr, 0.0, 3000.0, 1.0)
    err = cr.W_c - (W0 + cin - cout - csp)
    check("outflow through a partly open pipe: crater drains, budget closes", cout > 0 and abs(err) < 1e-8,
          f"drained {cout:.3f} m3, budget error {err:.1e} m3")

    print(f"\n== RESULT: {'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAIL'}")
    for f_ in FAILS:
        print("   " + f_)
    return len(FAILS)


if __name__ == "__main__":
    sys.exit(main())
