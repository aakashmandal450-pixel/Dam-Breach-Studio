"""Theory Part 5 verification, stage 1: pipe hydraulics and wall erosion (5.2)-(5.7), section 5.8."""
import math
import unittest

from lumped import piping as pp
from lumped.hydraulics import G, RHO_W

N = 0.016


def sweep(lo, hi, k=4000):
    return [lo + (hi - lo) * i / (k - 1) for i in range(k)]


class TestInlet(unittest.TestCase):
    def test_weir_form_below_priming(self):
        """(5.2) equals 1.705 b HW^1.5 / sqrt(1 + K_u) for HW <= 1.5 D."""
        for b, D in [(0.04, 0.04), (0.2, 0.2), (1.0, 0.5)]:
            for HW in sweep(1e-4, 1.5 * D, 50):
                q = pp.inlet_control(HW, b, D)
                ref = 1.705 * b * HW ** 1.5 / math.sqrt(1 + pp.K_U)
                self.assertAlmostEqual(q / ref, 1.0, 3)          # 1.705 is rounded in the theory
                exact = pp.C_INLET * b * HW ** 1.5 / math.sqrt(1 + pp.K_U)
                self.assertAlmostEqual(q / exact, 1.0, 12)

    def test_zero_head(self):
        self.assertEqual(pp.pipe_flow(0.0, 0.2, 0.2, 10, N).Q, 0.0)
        self.assertEqual(pp.pipe_flow(-1.0, 0.2, 0.2, 10, N).Q, 0.0)


class TestDischarge(unittest.TestCase):
    CASES = [(0.2, 0.2, 50.0), (0.2, 0.2, 2.0), (0.04, 0.04, 10.0), (1.0, 0.5, 3.0), (0.5, 1.0, 100.0)]

    def test_monotone_except_priming(self):
        """(5.3)-(5.4): Q_b non-decreasing in HW, except one step at HW = 1.5 D (priming)."""
        for b, D, L in self.CASES:
            hs = sweep(1e-4, 12 * D)
            qs = [pp.pipe_flow(h, b, D, L, N).Q for h in hs]
            drops = [(hs[i], qs[i - 1], qs[i]) for i in range(1, len(hs)) if qs[i] < qs[i - 1] * (1 - 1e-12)]
            for h, _, _ in drops:
                self.assertTrue(abs(h - 1.5 * D) <= 12 * D / 3999 + 1e-12, f"drop at HW={h} away from priming")
            self.assertLessEqual(len(drops), 1)

    def test_outlet_governs_when_full(self):
        """Q_o <= Q_i always once the pipe is full."""
        for b, D, L in self.CASES + [(0.2, 0.2, 1e-6), (2.0, 0.1, 0.01)]:
            for h in sweep(1.5 * D * 1.0001, 50 * D, 300):
                fl = pp.pipe_flow(h, b, D, L, N)
                self.assertEqual(fl.w, 1)
                self.assertLessEqual(fl.Q_o, fl.Q_i * (1 + 1e-12))
                self.assertEqual(fl.control, "outlet")

    def _step(self, b, D, L):
        eps = 1e-9
        before = pp.pipe_flow(1.5 * D, b, D, L, N)
        after = pp.pipe_flow(1.5 * D * (1 + eps), b, D, L, N)
        return before, after

    def test_priming_step_long_pipe_down(self):
        """F > K_u + K_d (1.05): the barrel already controls; priming wets the roof, Q steps down."""
        b, D, L = 0.2, 0.2, 50.0
        before, after = self._step(b, D, L)
        self.assertGreater(before.F, pp.K_U + pp.K_D)
        self.assertEqual(before.control, "outlet")
        self.assertLess(after.Q, before.Q)

    def test_priming_step_short_pipe_up(self):
        """F < 1.05 on both sides: entrance control before, full barrel after; Q steps up by at most sqrt 2."""
        b, D, L = 1.0, 0.5, 0.5
        before, after = self._step(b, D, L)
        self.assertLess(after.F, pp.K_U + pp.K_D)
        self.assertEqual(before.control, "inlet")
        self.assertGreater(after.Q, before.Q)
        self.assertLessEqual(after.Q / before.Q, math.sqrt(2) + 1e-9)
        # the bound is approached as F -> 0
        before0, after0 = self._step(b, D, 1e-9)
        self.assertAlmostEqual(after0.Q / before0.Q, math.sqrt(2 * (1 + pp.K_U) / (pp.K_U + pp.K_D)), 6)

    def test_full_pipe_equals_part1_orifice(self):
        """(5.3) for a full pipe is Part 1 (1.9) with z_bp at the centreline; bare orifice when f L -> 0, K = 1."""
        b, D, L, z_inv = 0.3, 0.2, 25.0, 0.4
        for z_s in (1.0, 2.5, 7.0):
            HW = z_s - z_inv
            fl = pp.pipe_flow(HW, b, D, L, N)
            R = b * D / (2 * b + 2 * D)
            f = 8 * G * N ** 2 / R ** (1 / 3)
            q19 = b * D * math.sqrt(2 * G * (z_s - (z_inv + D / 2)) / (pp.K_U + pp.K_D + f * L / (4 * R)))
            self.assertAlmostEqual(fl.Q / q19, 1.0, 12)
            q_orifice = pp.outlet_control(HW, b, D, 0.0, N, Ku=0.0, Kd=1.0)
            self.assertAlmostEqual(q_orifice / (b * D * math.sqrt(2 * G * (HW - D / 2))), 1.0, 12)


class TestShear(unittest.TestCase):
    def test_long_pipe_limit(self):
        """(5.5) -> rho g R dh / L when f L/(4R) >> K_u + K_d; exactly tau = rho g R dh/L * F/(K + F)."""
        b = D = 0.2
        for L in (5.0, 50.0, 500.0, 5000.0):
            HW = 10.1
            fl = pp.pipe_flow(HW, b, D, L, N)
            hec = RHO_W * G * fl.R * (HW - D / 2) / L
            tau = pp.wall_shear(fl)
            self.assertAlmostEqual(tau / hec, fl.F / (pp.K_U + pp.K_D + fl.F), 10)
            if fl.F > 100:
                self.assertGreater(tau / hec, 0.99)

    def test_theory_table(self):
        """Numbers quoted in section 5.4: 0.2 m pipe, 10 m head, n = 0.016."""
        for L, t55, thet in ((50.0, 91, 98), (5.0, 554, 981)):
            fl = pp.pipe_flow(10.1, 0.2, 0.2, L, N)
            self.assertAlmostEqual(pp.wall_shear(fl), t55, delta=1.0)
            self.assertAlmostEqual(RHO_W * G * fl.R * 10.0 / L, thet, delta=1.0)


class TestErosion(unittest.TestCase):
    def test_no_growth_below_tau_c(self):
        self.assertEqual(pp.erosion_rate(5.0, 1e-5, 5.0), 0.0)
        self.assertEqual(pp.erosion_rate(4.9, 1e-5, 5.0), 0.0)
        p = pp.Pipe(0.04, 0.04, 0.2, 10.0)
        self.assertEqual(pp.erode(p, 0.0, 1, 0.04, 1.0), (p, 0.0))

    def test_roof_fixed_while_part_full(self):
        p = pp.Pipe(0.1, 0.1, 0.3, 8.0)
        q, _ = pp.erode(p, 1e-4, 0, 0.06, 10.0)
        self.assertAlmostEqual(q.z_cr, p.z_cr, 14)
        self.assertLess(q.z_inv, p.z_inv)
        self.assertGreater(q.b, p.b)

    def test_volume_equals_wetted_area(self):
        """Eroded volume = wetted erodible area x eps dt, and equals the rectangle's volume change (round-off)."""
        for w, y in ((1, 0.1), (0, 0.06), (0, 0.1)):
            p = pp.Pipe(0.12, 0.1, 0.3, 8.0)
            eps, dt = 2e-4, 3.0
            q, V = pp.erode(p, eps, w, y, dt)
            wetted = (p.b + 2 * y + w * p.b) * p.L
            self.assertAlmostEqual(V, wetted * eps * dt, 14)
            self.assertAlmostEqual((q.b * q.D - p.b * p.D) * p.L, V, 14)

    def test_first_order_rates(self):
        """As dt -> 0: dz_inv/dt = -eps, db/dt = 2 eps y/D (= 2 eps when full), dz_cr/dt = w eps."""
        eps = 1e-4
        for w, y in ((1, 0.1), (0, 0.05)):
            p = pp.Pipe(0.12, 0.1, 0.3, 8.0)
            dt = 1e-2
            q, _ = pp.erode(p, eps, w, y, dt)
            self.assertAlmostEqual((p.z_inv - q.z_inv) / dt / eps, 1.0, 6)    # differences of O(1) numbers / dt
            self.assertAlmostEqual((q.z_cr - p.z_cr) / dt / eps, float(w), 6)
            self.assertAlmostEqual((q.b - p.b) / dt / (2 * eps * y / p.D), 1.0, 4)   # O(eps dt / D) second-order term

    def test_floor_stops_at_base(self):
        p = pp.Pipe(0.1, 0.1, 0.001, 5.0)
        q, V = pp.erode(p, 1e-3, 1, 0.1, 5.0)          # 5 mm of erosion, 1 mm of floor left
        self.assertEqual(q.z_inv, 0.0)
        self.assertAlmostEqual(V, (p.b * 0.001 + p.b * 0.005 + 2 * 0.1 * 0.005) * p.L, 14)
        r, _ = pp.erode(q, 1e-3, 1, 0.1, 5.0)
        self.assertEqual(r.z_inv, 0.0)

    def test_time_integration_volume(self):
        """A pipe eroded for many steps: total eroded volume equals the final minus initial void."""
        p = pp.Pipe(0.04, 0.04, 0.2, 2.0)
        V = 0.0
        for _ in range(2000):
            fl = pp.pipe_flow(1.0 - p.z_inv, p.b, p.D, p.L, N)
            eps = pp.erosion_rate(pp.wall_shear(fl), 1.5e-4, 0.0)   # k_d = 150 cm3/(N s) = 1.5e-4 m3/(N s)
            p, dV = pp.erode(p, eps, fl.w, fl.y, 0.5)
            V += dV
        self.assertAlmostEqual(V, (p.b * p.D - 0.04 * 0.04) * 2.0, 12)


if __name__ == "__main__":
    unittest.main()
