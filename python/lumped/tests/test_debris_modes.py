"""Theory Part 5 verification: the debris comparison treatments of 5.7 (level, instant removal, virtual
tank) and the end-wall volume correction (draft 5.11)."""
import copy
import unittest

from lumped import crater as cm
from lumped.geometry import Dam
from lumped.tests.test_crater import base_crater, DAM

SLOPED = Dam(3.0, 2.0, 3.0, 3.0, 50.0)       # crest 9-11 m at z = 3


class TestTreatments(unittest.TestCase):
    def test_instant_removal_opens_to_the_invert(self):
        cr = base_crater(debris="instant")
        self.assertAlmostEqual(cr.z_d, cr.z_inv, 12)                 # void = roof + pipe over the reach
        self.assertEqual(cr.V_db, 0.0)
        self.assertAlmostEqual(cr.V_exp_out, cr.kappa * cr.V_fall, 12)
        self.assertEqual(cr.W_c, 0.0)                                 # pore water leaves with the soil
        self.assertEqual(cr.a_open(), cr.a_p)

    def test_tank_same_geometry_debris_stored(self):
        a, b = base_crater(debris="instant"), base_crater(debris="tank")
        self.assertAlmostEqual(a.z_d, b.z_d, 12)
        self.assertAlmostEqual(b.V_tank, b.kappa * b.V_fall, 12)
        self.assertEqual(b.V_exp_out, 0.0)

    def test_level_mode_unchanged_default(self):
        cr = base_crater()
        self.assertEqual(cr.debris, "level")
        self.assertAlmostEqual(cr.zg - cr.z_d, cr.a_p, 12)
        self.assertEqual(cr.V_exp, 0.0)

    def test_solids_identity_all_modes(self):
        for mode in ("level", "instant", "tank"):
            cr = base_crater(debris=mode, n_d=0.45)
            for w in ("up", "down", "sides"):
                cr.retreat_wall(w, S_r=1.0)
            self.assertAlmostEqual((1 - cr.n) * cr.V_fall,
                                   (1 - cr.n_d) * (cr.V_db + cr.V_spoil + cr.V_exp), 12)
            if mode != "level":
                self.assertAlmostEqual(cr.V_exp, cr.V_tank + cr.V_exp_out, 12)


class TestEndWallVolume(unittest.TestCase):
    def test_floor_kept_on_a_sloping_face(self):
        """Instant removal on the upstream face: end-wall retreats keep the floor at the invert (the fallen
        volume is the soil over the new strip, not 1/2 H_w^2 W, which over-counts on a slope)."""
        cr = cm.Crater(SLOPED, 6.0, 7.0, 0.5, 1.0, 0.3, 0.5, 10.0, debris="instant")
        cr.V_pipe = cr.b_p * cr.a_p * cr.ell
        pts = [6.0, 7.0]
        from lumped.geometry import integrate_positive
        cr.fall(cr.b_p * integrate_positive(lambda x: SLOPED.z_dam(x) - cr.z_cr, pts), S_r=0.0)
        self.assertAlmostEqual(cr.z_d, cr.z_inv, 12)
        for _ in range(3):
            cr.retreat_wall("up", S_r=0.0)
            cr.retreat_wall("down", S_r=0.0)
            self.assertAlmostEqual(cr.z_d, cr.z_inv, 9)

    def test_level_ground_matches_half_H_squared(self):
        cr = base_crater()
        Hw = cr.wall_heights()["up"][0]
        V0 = cr.V_fall
        cr.retreat_wall("up", S_r=0.0)
        self.assertAlmostEqual(cr.V_fall - V0, 0.5 * Hw * Hw * cr.W, 12)   # flat crest: theory's 1/2 H_w^2


class TestVirtualTankInDriver(unittest.TestCase):
    def test_geometry_frozen_until_tank_empty(self):
        from lumped.piping_run import PipingRun
        from lumped.stability_table import StabilityTable
        from lumped.tests.test_piping_run import p1_case, TABLE
        T = StabilityTable.from_csv(str(TABLE))
        r = PipingRun(p1_case(), T, dt=1.0).run(120.0)              # level mode: crater exists, sealed later
        s = copy.deepcopy(r.s)
        cr = s.crater
        cr.debris, cr.V_tank, cr.W_c = "tank", 2e-5, 0.0             # empty crater, small tank: inflow erodes
        b0, D0 = s.pipe.b, s.pipe.D
        for _ in range(400):
            n = r.advance(s, 0.02)
            if n.crater.V_tank > 0.0:
                self.assertEqual((n.pipe.b, n.pipe.D), (b0, D0))       # frozen while the tank holds debris
                self.assertLess(n.crater.V_tank, s.crater.V_tank + 1e-18)
            s = n
            if s.crater.V_tank == 0.0:
                break
        self.assertEqual(s.crater.V_tank, 0.0)
        self.assertAlmostEqual(s.crater.V_exp_out, 2e-5, 15)
        n = r.advance(s, 0.02)
        self.assertGreaterEqual(n.pipe.b, s.pipe.b)


if __name__ == "__main__":
    unittest.main()
