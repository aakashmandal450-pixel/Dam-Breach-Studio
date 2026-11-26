"""Draft F-1 (§5.6b) verification of the standalone face module, before any P1 run:
infinite-slope limit (hand values), G2 = Part 3 planar wedge with u = 0, block volume, Green-Ampt
against its analytic solution, grid independence."""
import math
import unittest

from lumped import face as fc
from lumped.geometry import Dam, culmann_critical_height

G = 9.81
GM, GS = 18550.0, 20170.0        # P1 moist / saturated unit weight [N/m3]
DAM = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
BETA = math.atan(1 / 3)


def soil(c=0.0, cs=0.0, sides=False, tphi=0.625):
    return fc.FaceSoil(c_eff=c, tan_phi=tphi, c_s=cs, gamma_moist=GM, gamma_sat=GS, sides=sides)


def long_slope():
    """A long planar 3H:1V face, 30 m high, so a slab far from both ends is an infinite slope."""
    return fc.Profile([0.0, 90.0], [30.0, 0.0])


class TestInfiniteSlope(unittest.TestCase):
    """G1 slab far from the ends, no sides: FS = [c + (gamma t cos^2 b - u) tan phi]/(gamma t sin b cos b)."""

    def slab(self, sc, s, t=0.3):
        prof = long_slope()
        z_cr = 1.0                                         # 'crown' low on the face; slab well above it
        x_d = prof.daylight(z_cr)
        x_u = x_d - t / math.tan(BETA)
        return fc.evaluate("G1", BETA, x_u - 60.0, x_u, x_d, z_cr, prof, s, sc, w=1.0, nx=4000, nz=8)

    def test_dry(self):
        b = self.slab(fc.Scenario("P0"), soil())
        # the short void-lip at the toe is negligible over 60 m
        self.assertAlmostEqual(b.FS, 0.625 / math.tan(BETA), delta=0.01 * 1.875)

    def test_face_parallel_seepage(self):
        par = lambda x: ((90.0 - x) / 3.0, BETA)          # phreatic line on the surface, parallel flow
        b = self.slab(fc.Scenario("P2", phreatic=par), soil())
        expect = (GS - fc.GAMMA_W) * 0.625 / (GS * math.tan(BETA))
        self.assertAlmostEqual(b.FS, expect, delta=0.01 * expect)
        self.assertLess(b.FS, 1.0)                          # 0.96 for P1 values

    def test_cohesion_term(self):
        t, c = 0.3, 2000.0
        b = self.slab(fc.Scenario("P0"), soil(c=c), t=t)
        expect = (c + GM * t * math.cos(BETA) ** 2 * 0.625) / (GM * t * math.sin(BETA) * math.cos(BETA))
        self.assertAlmostEqual(b.FS, expect, delta=0.01 * expect)


class TestCulmannPart3(unittest.TestCase):
    """G2 with u = 0, c_s = 0, no sides, no crack is the planar wedge (3.9)-(3.10): at the Culmann critical
    height of a cohesive bank the critical wedge has FS = 1."""

    def test_critical_height(self):
        c, phi, beta_bank = 10000.0, math.radians(25.0), math.radians(60.0)
        Hc = culmann_critical_height(c, GM, beta_bank, phi)
        x_toe = 20.0
        prof = fc.Profile([0.0, x_toe - Hc / math.tan(beta_bank), x_toe, 40.0], [Hc, Hc, 0.0, 0.0])
        s = soil(c=c, tphi=math.tan(phi))
        b = fc.critical_G2(prof, 0.0, beta_bank, 0.0, s, fc.Scenario("P0"), w=1.0, na=136, crack=False,
                           alpha_min=math.radians(26.0), nx=800, nz=4)
        self.assertAlmostEqual(b.FS, 1.0, delta=0.005)
        self.assertAlmostEqual(b.theta, 0.5 * (beta_bank + phi), delta=math.radians(0.5))
        cr = fc.critical_G2(prof, 0.0, beta_bank, 0.0, s, fc.Scenario("P0"), w=1.0, na=34, nb=40,
                            alpha_min=math.radians(26.0), nx=400, nz=4)
        self.assertLess(cr.FS, b.FS)                       # a tension crack carries nothing


class TestVolume(unittest.TestCase):
    def test_slab_area_on_the_original_face(self):
        prof = fc.Profile.from_dam(DAM)
        z_cr, t = 0.369, 0.15
        x_d = prof.daylight(z_cr)
        x_u = x_d - 3.0 * t
        x_b = x_u - 0.8
        b = fc.evaluate("G1", BETA, x_b, x_u, x_d, z_cr, prof, soil(), fc.Scenario("P0"), w=0.29, nx=2000, nz=4)
        A = t * (x_d - x_b) - 3.0 * t * t / 2.0                  # (F.3)
        self.assertAlmostEqual(b.A, A, delta=1e-6)
        self.assertAlmostEqual(b.V, 0.29 * A, delta=1e-6)
        self.assertAlmostEqual(b.W, 0.29 * A * GM, delta=1e-3 * b.W)

    def test_cut_profile(self):
        prof = fc.Profile.from_dam(DAM)
        z_cr, t = 0.369, 0.15
        x_d = prof.daylight(z_cr)
        x_u = x_d - 3.0 * t
        new = prof.cut(x_u - 0.8, x_d, lambda x: z_cr + (x_u - x) / 3.0 if x <= x_u else z_cr, breaks=[x_u])
        self.assertAlmostEqual(new.daylight(z_cr), x_u, delta=1e-9)   # the outlet moves to x_u
        self.assertAlmostEqual(float(new(x_u - 0.4)), float(prof(x_u - 0.4)) - t, delta=1e-9)


class TestGreenAmpt(unittest.TestCase):
    def test_against_analytic(self):
        K, H, dth = 3e-6, 0.11, 0.166
        T = lambda d: (dth / K) * (-d - H * math.log(1 - d / H))
        d = 1e-6
        for _ in range(100):
            d = fc.green_ampt_up(d, 8.28, K, H, dth)          # 828 s in 100 steps
        self.assertAlmostEqual(T(d), T(1e-6) + 828.0, delta=1e-6 * 828)
        self.assertLess(d, H)

    def test_tends_to_capillary_height(self):
        d = fc.green_ampt_up(1e-6, 1e9, 3e-6, 0.11, 0.166)
        self.assertAlmostEqual(d, 0.11, delta=1e-6)


class TestGrid(unittest.TestCase):
    def test_min_fs_grid_independent(self):
        prof = fc.Profile.from_dam(DAM)
        s = fc.FaceSoil(0.0, 0.625, 1000.0, GM, GS, sides=True)
        sc = fc.Scenario("P1", delta=0.05)
        a = fc.critical_G1(prof, 0.369, BETA, DAM.x_c1, s, sc, 0.29, t_max=0.8, nt=15, nb=15)
        b = fc.critical_G1(prof, 0.369, BETA, DAM.x_c1, s, sc, 0.29, t_max=0.8, nt=60, nb=60)
        self.assertAlmostEqual(a.FS, b.FS, delta=0.005 * b.FS)

    def test_resolution_limits_flagged(self):
        """The critical slab sits on the resolution limits (t_min = 0.25 b, L_min = b/2) and says so."""
        prof = fc.Profile.from_dam(DAM)
        s = fc.FaceSoil(0.0, 0.625, 1000.0, GM, GS, sides=True)
        a = fc.critical_G1(prof, 0.369, BETA, DAM.x_c1, s, fc.Scenario("P1", delta=0.05), 0.29, t_max=0.8,
                           nt=20, nb=20)
        self.assertTrue(a.info["at_limit"])
        self.assertGreaterEqual(a.t, 0.25 * 0.29 - 1e-12)
        self.assertGreaterEqual(a.x_d - a.x_b, 0.5 * 0.29 - 1e-9)


if __name__ == "__main__":
    unittest.main()
