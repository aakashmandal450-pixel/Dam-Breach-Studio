"""Theory Part 3 verification (section 3.6)."""
import math
import unittest

from lumped import geometry as g


class TestStability(unittest.TestCase):
    def test_cohesionless(self):
        for phi in (25, 30, 40):
            self.assertAlmostEqual(g.steepest_stable_slope(0.0, 18000.0, 5.0, math.radians(phi)), math.radians(phi), 12)
            self.assertAlmostEqual(g.side_slope_angle(0.0, 18000.0, 5.0, math.radians(phi)), math.radians(phi), 12)

    def test_equals_culmann(self):
        """(3.12) is the Culmann critical height solved for the slope."""
        for C in (2e3, 5e3, 15.5e3, 25e3):
            for H in (1.0, 3.0, 12.8, 21.0):
                for phi in (25, 30, 42):
                    gb, ph = 18000.0, math.radians(phi)
                    bs = g.steepest_stable_slope(C, gb, H, ph)
                    if bs < 0.5 * math.pi - 1e-9:
                        self.assertAlmostEqual(g.culmann_critical_height(C, gb, bs, ph) / H, 1.0, 9)

    def test_trends(self):
        gb, ph = 18000.0, math.radians(30)
        b = [g.side_slope_angle(10e3, gb, H, ph) for H in (2, 5, 10, 20)]
        self.assertTrue(all(x >= y for x, y in zip(b, b[1:])), "beta must not rise as the bank gets higher")
        c = [g.side_slope_angle(C, gb, 10.0, ph) for C in (1e3, 5e3, 10e3, 20e3)]
        self.assertTrue(all(x < y for x, y in zip(c, c[1:])), "beta must rise with cohesion")


class TestAreas(unittest.TestCase):
    def test_full_section(self):
        dam = g.Dam(H=10.0, Wc=5.0, zu=3.0, zd=2.0, L_cr=100.0)
        full = 10.0 * (5.0 + 0.5 * (3.0 + 2.0) * 10.0)
        self.assertAlmostEqual(g.side_area_top(dam, 0.0, dam.x_T, 0.0), full, 9)
        self.assertAlmostEqual(g.side_area_slope(dam, 0.0, 0.0), full, 9)

    def test_above_level(self):
        dam = g.Dam(H=10.0, Wc=5.0, zu=3.0, zd=2.0, L_cr=100.0)
        z = 6.0   # section above z = 6: trapezoid of height 4, crest 5, slopes 3 and 2
        expect = 4.0 * (5.0 + 0.5 * (3.0 + 2.0) * 4.0)
        self.assertAlmostEqual(g.side_area_top(dam, dam.x_up(z), dam.x_down(z), z), expect, 9)


if __name__ == "__main__":
    unittest.main()
