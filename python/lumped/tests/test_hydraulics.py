"""Theory Part 1 verification (section 1.7)."""
import math
import unittest

from lumped import hydraulics as hy


class TestWeir(unittest.TestCase):
    def test_rectangle_limit(self):
        for b, H in [(1.0, 1.0), (5.0, 2.3), (40.0, 12.0)]:
            self.assertAlmostEqual(hy.weir_exact(b, 0.0, H) / (b * H ** 1.5), math.sqrt(9.81) * (2 / 3) ** 1.5, 9)

    def test_triangle_limit(self):
        for m, H in [(1.0, 1.0), (0.5, 3.0), (2.0, 10.0)]:
            self.assertAlmostEqual(hy.weir_exact(0.0, m, H) / (m * H ** 2.5), math.sqrt(9.81 / 2) * 0.8 ** 2.5, 9)

    def test_dlbreach_close_to_exact(self):
        worst = 0.0
        for ratio in [0.1, 0.3, 1.0, 3.0, 10.0, 100.0]:
            H, m = 2.0, 1.0
            b = ratio * m * H
            worst = max(worst, abs(hy.weir_dlbreach(b, m, H) / hy.weir_exact(b, m, H) - 1.0))
        print(f"\n      max |DL Breach weir / exact - 1| over b/(mH) = 0.1..100: {worst:.3%}")
        self.assertLess(worst, 0.10)

    def test_submergence(self):
        self.assertEqual(hy.submergence(10.0, 0.0, 0.0), 1.0)
        self.assertEqual(hy.submergence(10.0, 6.6, 0.0), 1.0)
        self.assertAlmostEqual(hy.submergence(10.0, 6.7, 0.0), 1.0, 12)
        self.assertLess(hy.submergence(10.0, 10.0, 0.0), 0.001)

    def test_crest_overflow(self):
        self.assertAlmostEqual(hy.crest_overflow(10.0, 1.0), 10.0 * math.sqrt(9.81) * (2 / 3) ** 1.5, 12)


class TestUniformFlow(unittest.TestCase):
    def test_normal_depth_recovers_Q(self):
        for Q, b, m, n, S0 in [(10.0, 2.0, 1.0, 0.03, 0.3), (500.0, 20.0, 0.5, 0.05, 0.4), (0.1, 0.1, 2.0, 0.016, 0.33)]:
            h = hy.normal_depth(Q, b, m, n, S0)
            A, R = hy.area(b, m, h), hy.hydraulic_radius(b, m, h)
            self.assertAlmostEqual(A * R ** (2 / 3) * math.sqrt(S0) / n / Q, 1.0, 9)

    def test_shear(self):
        self.assertAlmostEqual(hy.manning_shear(2.0, 1.0, 1.0, 0.03), 1000 * 9.81 * 0.03 ** 2 * 4.0, 9)


if __name__ == "__main__":
    unittest.main()
