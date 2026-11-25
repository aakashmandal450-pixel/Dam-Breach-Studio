"""Theory Part 5 verification, stage 3b: crater state, storage, outflows, walls and remnants (5.7a, 5.8).
Ported from verification/crater_balance_check.py, with the crater tied to a dam profile."""
import math
import unittest

from lumped import crater as cm
from lumped import piping as pp
from lumped.geometry import Dam

DAM = Dam(10.0, 20.0, 3.0, 3.0, 100.0)          # flat crest from x = 30 to 50 at z = 10


def base_crater(**kw):
    """A 4 m long crater on the crest over a 1 m pipe under 5 m of cover, roof collapsed (n_d = n)."""
    d = dict(dam=DAM, x1=38.0, x2=42.0, W=1.0, z_inv=4.0, a_p=1.0, b_p=1.0, L_down=20.0)
    d.update(kw)
    cr = cm.Crater(**d)
    cr.V_pipe = cr.b_p * cr.a_p * cr.ell
    cr.fall(cr.b_p * (cr.zg - cr.z_cr) * cr.ell, S_r=1.0)
    return cr


def integrate(cr, Q_in, T, dt):
    """RK4 on dW_c/dt = Q_in - Q_out - Q_spill (5.22); returns cumulative in, out, spill."""
    cin = cout = csp = 0.0
    t = 0.0

    def rate(W):
        old = cr.W_c; cr.W_c = W
        zc = cr.level(); qo, qs = cr.Q_out(zc), cr.Q_spill(zc)
        cr.W_c = old
        return Q_in - qo - qs, qo, qs

    while t < T - 1e-12:
        h = min(dt, T - t); W0 = cr.W_c
        k1, o1, s1 = rate(W0); k2, o2, s2 = rate(W0 + 0.5 * h * k1)
        k3, o3, s3 = rate(W0 + 0.5 * h * k2); k4, o4, s4 = rate(W0 + h * k3)
        cr.W_c = max(W0 + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6, 0.0)
        cin += Q_in * h; cout += h * (o1 + 2 * o2 + 2 * o3 + o4) / 6; csp += h * (s1 + 2 * s2 + 2 * s3 + s4) / 6
        t += h
    return cin, cout, csp


class TestWallCriterion(unittest.TestCase):
    def test_exact_limits(self):
        self.assertAlmostEqual(cm.wall_critical_height(20.0, 20.0, 9.81, 0.0, 0.0, 3.0), 3.776, 12)
        self.assertAlmostEqual(cm.wall_critical_height(20.0, 20.0, 9.81, 0.0, 3.0, 3.0), 3.776 * 20 / 10.19, 12)
        self.assertAlmostEqual(cm.wall_critical_height(20.0, 20.0, 9.81, 0.0, 0.0, 3.0, tension=False), 2.0, 12)

    def test_domain_guard(self):
        for args in [(20.0, 32.7, 9.81, 0.0, 1.0, 3.0), (20.0, 20.0, 9.81, 4.0, 0.0, 3.0),
                     (20.0, 20.0, 9.81, 0.0, 4.0, 3.0), (20.0, 6.0, 0.0, 3.0, 0.0, 3.0)]:
            with self.assertRaises(cm.DomainError):
                cm.wall_critical_height(*args)
        cm.wall_critical_height(20.0, 32.7, 9.81, 0.0, 0.0, 3.0)      # dry wall: gamma_w/gamma irrelevant


class TestGeometryAndPores(unittest.TestCase):
    def test_void_identity_depth_is_a_p(self):
        cr = base_crater()
        self.assertAlmostEqual(cr.zg - cr.z_d, cr.a_p, 12)

    def test_saturated_roof_brings_its_pore_water(self):
        cr = base_crater()
        self.assertAlmostEqual(cr.W_c, cr.n_d * cr.V_db, 9)
        zc = cr.level()
        self.assertAlmostEqual(zc, cr.z_d, 6)
        self.assertLess(cr.free_water(), 1e-6)
        self.assertAlmostEqual(cr.S(zc), cr.W_c, 9)

    def test_pore_water_does_not_load_wall(self):
        cr = base_crater(); cr.W_c *= 0.5
        self.assertTrue(all(h == 0.0 for _, h in cr.wall_heights().values()))

    def test_fall_into_water_no_double_count(self):
        cr = base_crater(); cr.W_c += 2.0
        fw0, Wc0 = cr.free_water(), cr.W_c
        cr.fall(1.5, S_r=1.0)
        self.assertAlmostEqual(cr.free_water(), fw0, 6)
        self.assertAlmostEqual(cr.W_c - Wc0, cr.n * 1.5, 12)

    def test_bulking_draws_extra_pore_space(self):
        cr = base_crater(n_d=0.45); cr.V_pipe += 4.0
        cr.W_c = cr.n_d * cr.V_db + 0.2
        fw0 = cr.free_water()
        cr.fall(0.5, S_r=1.0)
        self.assertAlmostEqual(fw0 - cr.free_water(), (cr.n_d - cr.n) / (1 - cr.n_d) * 0.5, 6)

    def test_overfill_goes_to_spoil_and_solids_conserved(self):
        cs = base_crater(n_d=0.50)
        Vs0 = (1 - cs.n) * cs.V_fall
        self.assertLessEqual(cs.z_d, cs.zg + 1e-12)
        self.assertGreater(cs.V_spoil, 0.0)
        self.assertAlmostEqual((1 - cs.n_d) * (cs.V_db + cs.V_spoil), Vs0, 12)


class TestObstruction(unittest.TestCase):
    def setUp(self):
        self.cr = base_crater()
        self.zc = self.cr.z_rim - 0.5

    def q_at(self, z_d):
        c = cm.Crater(DAM, self.cr.x1, self.cr.x2, 1.0, 4.0, 1.0, 1.0, 20.0)
        c.V_pipe = (c.zg - z_d) * c.A_c
        return c.Q_out(self.zc), c.a_open()

    def test_open_partly_closed(self):
        q_full = pp.pipe_flow(self.zc - 4.0, 1.0, 1.0, 20.0, 0.016).Q
        q0, a0 = self.q_at(3.5)
        self.assertAlmostEqual(q0, q_full, 12); self.assertEqual(a0, 1.0)
        qp, _ = self.q_at(4.5)
        self.assertTrue(0 < qp < q_full)
        qe, _ = self.q_at(5.0 - 1e-4)
        self.assertLess(qe, 1e-3 * q_full)
        qc, ac = self.q_at(5.2)
        self.assertEqual((qc, ac), (0.0, 0.0))

    def test_monotone_no_jump(self):
        q_full = self.q_at(3.5)[0]
        zs = [3.5 + i * 0.001 for i in range(2001)]
        qs = [self.q_at(z)[0] for z in zs]
        self.assertTrue(all(qs[i + 1] <= qs[i] + 1e-12 for i in range(len(qs) - 1)))
        self.assertLess(max(abs(qs[i + 1] - qs[i]) for i in range(len(qs) - 1)), 0.02 * q_full)


class TestWaterBalance(unittest.TestCase):
    def test_no_inflow_blocked(self):
        cr = base_crater(); cr.W_c += 2.0
        W0, z0 = cr.W_c, cr.level()
        integrate(cr, 0.0, 600.0, 5.0)
        self.assertAlmostEqual(cr.W_c, W0, 12); self.assertAlmostEqual(cr.level(), z0, 9)

    def test_inflow_without_outflow(self):
        cr = base_crater(); W0 = cr.W_c
        cin, cout, csp = integrate(cr, 0.002, 600.0, 5.0)
        self.assertAlmostEqual(cr.W_c, W0 + 1.2, 9)
        self.assertEqual((cout, csp), (0.0, 0.0))

    def test_fall_mid_run_budget(self):
        cr = base_crater(n_d=0.45); cr.W_c = cr.n_d * cr.V_db; W0 = cr.W_c; rel0 = cr.released
        a1 = integrate(cr, 0.002, 300.0, 5.0); cr.fall(1.0, S_r=1.0); a2 = integrate(cr, 0.002, 300.0, 5.0)
        err = cr.W_c - (W0 + a1[0] + a2[0] - a1[1] - a2[1] - a1[2] - a2[2] + cr.released - rel0)
        self.assertLess(abs(err), 1e-9)

    def test_spill_steady_state(self):
        cr = base_crater(); W0 = cr.W_c; Qin = 0.05
        cin, cout, csp = integrate(cr, Qin, 20000.0, 2.0)
        z_ss = cr.z_rim + (Qin / (cm.C_INLET * cr.W)) ** (2 / 3)
        self.assertAlmostEqual(cr.level(), z_ss, 4)
        self.assertAlmostEqual(cr.Q_spill(), Qin, 5)
        self.assertLess(abs(cr.W_c - (W0 + cin - cout - csp)), 1e-8)

    def test_partly_open_drains(self):
        cr = base_crater(); cr.V_pipe += 18.0
        self.assertTrue(cr.z_inv < cr.z_d < cr.z_cr)
        cr.W_c += 8.0; W0 = cr.W_c
        cin, cout, csp = integrate(cr, 0.0, 3000.0, 1.0)
        self.assertGreater(cout, 0.0)
        self.assertLess(abs(cr.W_c - (W0 + cin - cout - csp)), 1e-8)


class TestWallsAndRemnants(unittest.TestCase):
    def test_end_wall_retreat_conserves_wedge_and_adds_pipe(self):
        cr = base_crater()
        Hw = cr.wall_heights()["up"][0]
        V0, P0, x10 = cr.V_fall, cr.V_pipe, cr.x1
        d = cr.retreat_wall("up", S_r=0.0)
        self.assertAlmostEqual(d, 0.5 * Hw, 12)
        self.assertAlmostEqual(cr.x1, x10 - d, 12)
        self.assertAlmostEqual(cr.V_fall - V0, 0.5 * Hw * Hw * cr.W, 12)
        self.assertAlmostEqual(cr.V_pipe - P0, cr.b_p * cr.a_p * d, 12)

    def test_side_retreat_widens_and_shallows(self):
        cr = base_crater()
        depth0 = cr.zg - cr.z_d
        cr.retreat_wall("sides", S_r=0.0)
        self.assertGreater(cr.W, 1.0)
        self.assertLess(cr.zg - cr.z_d, depth0)      # a wider crater is shallower

    def test_solids_budget_after_walls(self):
        cr = base_crater(n_d=0.45)
        for w in ("up", "down", "sides"):
            cr.retreat_wall(w, S_r=1.0)
        Vs = (1 - cr.n) * cr.V_fall
        self.assertAlmostEqual((1 - cr.n_d) * (cr.V_db + cr.V_spoil + cr.V_exp), Vs, 12)

    def test_remnant_mean_strength(self):
        A, c = cm.remnant_area_and_strength(DAM, 5.0, 35.0, 45.0, 1000.0, 100.0)
        self.assertAlmostEqual(A, 50.0, 12)                    # 10 m of crest, 5 m cover
        self.assertAlmostEqual(c, 1000.0 + 100.0 * 2.5, 9)     # mean depth 2.5 m

    def test_pushout_signs(self):
        mu, md = cm.pushout_margins(DAM, 5.0, 1.0, 9.0, 4.0, 20.0, 38.0, 42.0, 60.0, 20000.0, 0.0)
        self.assertGreater(mu, 0.0); self.assertGreater(md, 0.0)
        mu2, _ = cm.pushout_margins(DAM, 5.0, 1.0, 9.0, 4.0, 37.9, 38.0, 42.0, 60.0, 20000.0, 0.0)
        self.assertLess(mu2, mu)                              # a shorter remnant resists less


if __name__ == "__main__":
    unittest.main()
