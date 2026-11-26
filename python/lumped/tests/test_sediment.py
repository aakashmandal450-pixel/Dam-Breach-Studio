"""Theory Part 2 verification (section 2.6)."""
import math
import unittest

from lumped import sediment as sd


class TestCohesive(unittest.TestCase):
    def test_threshold(self):
        self.assertEqual(sd.cohesive_rate(0.1, 0.15, 1e-6), 0.0)
        self.assertEqual(sd.cohesive_rate(0.15, 0.15, 1e-6), 0.0)

    def test_units(self):     # kd 1 cm3/(N s) = 1e-6 m3/(N s), excess 1 Pa -> 1e-6 m/s
        self.assertAlmostEqual(sd.cohesive_rate(1.15, 0.15, 1e-6), 1e-6, 15)


class TestNonCohesive(unittest.TestCase):
    def test_settling_velocity_matches_2d(self):
        import breach_engine_2d_v3_2 as E
        for d in (1.2e-4, 1e-3, 1.4e-2):
            st = E.SedimentTransport(E.EngineConfig(), E.MaterialProps(D50=d, D90=2.5 * d))
            self.assertAlmostEqual(sd.settling_velocity(d), st.settling_velocity(), 12)

    def test_wu_bedload_hand(self):
        d, rs = 0.014, 2650.0
        tc = 0.03 * (rs - 1000) * 9.81 * d
        q = sd.wu_bedload(3 * tc, tc, d, rs)
        self.assertAlmostEqual(q, 0.0053 * 2 ** 2.2 * math.sqrt(1.65 * 9.81 * d ** 3), 15)
        self.assertEqual(sd.wu_bedload(0.9 * tc, tc, d, rs), 0.0)

    def test_slope_correction(self):
        self.assertEqual(sd.slope_effective_shear(10.0, 5.0, 0.0, math.radians(35)), 10.0)
        a = sd.slope_effective_shear(10.0, 5.0, math.radians(10), math.radians(35))
        b = sd.slope_effective_shear(10.0, 5.0, math.radians(20), math.radians(35))
        self.assertTrue(10.0 < a < b)

    def test_zhang_shape(self):
        ws = sd.settling_velocity(1e-3)
        lo = sd.zhang_suspended_mass(0.5, 1.0, ws)
        hi = sd.zhang_suspended_mass(5.0, 1.0, ws)
        self.assertTrue(0.0 < lo < hi)
        self.assertEqual(sd.zhang_suspended_mass(0.0, 1.0, ws), 0.0)

    def test_relax(self):
        self.assertAlmostEqual(sd.relax(0.0, 0.1, 1e6, 1.0), 0.1, 12)
        self.assertEqual(sd.relax(0.03, 0.1, 0.0, 1.0), 0.03)
        # matches numerical integration of dC/dx = (C* - C)/Ls
        c, n, L, Ls, cs = 0.02, 200000, 7.0, 3.0, 0.08
        for _ in range(n):
            c += (cs - c) / Ls * (L / n)
        self.assertAlmostEqual(sd.relax(0.02, cs, L, Ls), c, 6)


if __name__ == "__main__":
    unittest.main()
