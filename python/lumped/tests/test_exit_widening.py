"""Note H-1 (H1-a) verification, step 1 of the reviewed sequence, then the controlled coupling checks:
(H.1) against fine quadrature at constant Q, no widening below the critical shear, the wall volume
against direct integration, the B_e = b limit equal to the 5.6 stage-1 channel, self-limiting widening,
the option off reproducing the existing run exactly, budgets."""
import math
import unittest

import numpy as np

from lumped import exit_headcut as xh
from lumped import exit_widening as xw
from lumped.geometry import Dam
from lumped.piping_run import PipingRun
from lumped.stability_table import StabilityTable
from lumped.tests.test_piping_run import TABLE, p1_case

M, N, KD = 3.0, 0.016, 3.16e-6


class TestLaw(unittest.TestCase):
    def test_constant_Q_against_quadrature(self):
        """Explicit steps converge (first order) to the ODE solution from fine RK4."""
        Q, B0, T = 0.05, 0.10, 600.0

        def rk4(n):
            B, h = B0, T / n
            for _ in range(n):
                k1 = xw.rate(Q, B, M, N, KD, 0.0)
                k2 = xw.rate(Q, B + 0.5 * h * k1, M, N, KD, 0.0)
                k3 = xw.rate(Q, B + 0.5 * h * k2, M, N, KD, 0.0)
                k4 = xw.rate(Q, B + h * k3, M, N, KD, 0.0)
                B += h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            return B
        ref = rk4(4000)
        errs = []
        for dt in (8.0, 4.0, 2.0):
            B = B0
            for _ in range(int(T / dt)):
                B, _ = xw.step(B, 0.04, 0.3, Q, M, N, KD, 0.0, dt)
            errs.append(abs(B - ref))
        self.assertLess(errs[-1] / ref, 5e-4)                    # 0.03 % at dt = 2 s
        self.assertAlmostEqual(errs[0] / errs[1], 2.0, delta=0.3)
        self.assertAlmostEqual(errs[1] / errs[2], 2.0, delta=0.3)

    def test_no_widening_below_threshold_or_without_flow(self):
        _, tau = xw.notch_flow(0.05, 0.2, M, N)
        self.assertEqual(xw.rate(0.05, 0.2, M, N, KD, tau * 1.01), 0.0)          # review correction A
        self.assertEqual(xw.rate(0.0, 0.2, M, N, KD, 0.0), 0.0)
        B, dV = xw.step(0.2, 0.04, 0.3, 0.0, M, N, KD, 0.0, 100.0)
        self.assertEqual((B, dV), (0.2, 0.0))

    def test_self_limiting_in_the_wide_regime(self):
        """H-A4 as stated in the note: in a narrow, deep slot R grows with B and so does the rate; once the
        notch is wide against its flow depth (B >~ 3 y) the rate falls as B grows. P1 is in that regime."""
        Q = 0.1
        Bs = [0.3, 0.6, 0.9, 1.8, 2.7]
        r = [xw.rate(Q, B, M, N, KD, 0.0) for B in Bs]
        self.assertTrue(all(B > 3 * xw.notch_flow(Q, B, M, N)[0] for B in Bs))
        self.assertTrue(all(a > b for a, b in zip(r, r[1:])))
        self.assertLess(xw.rate(Q, 0.04, M, N, KD, 0.0), xw.rate(Q, 0.1, M, N, KD, 0.0))   # narrow slot

    def test_limit_equals_exit_headcut_channel(self):
        """B_e = b: the notch flow is the 5.6 stage-1 face channel exactly."""
        for Q, b in ((0.002, 0.04), (0.06, 0.17), (0.24, 0.29)):
            y, tau = xw.notch_flow(Q, b, M, N)
            y2, tau2 = xh._rect_flow(Q, b, 1.0 / M, N)
            self.assertAlmostEqual(tau, tau2, places=10)


class TestVolume(unittest.TestCase):
    def test_wall_area_against_profile(self):
        """A_w = area of the face above the invert between the crown and invert daylight points."""
        dam = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
        z_inv, D = 0.071, 0.297
        x_t = dam.x_c1 + dam.zd * dam.H
        xd, xi = x_t - dam.zd * (z_inv + D), x_t - dam.zd * z_inv
        xs = np.linspace(xd, xi, 20001)
        h = np.array([dam.z_dam(x) for x in xs]) - z_inv
        self.assertAlmostEqual(float(np.trapezoid(h, xs)), xw.wall_area(D, dam.zd), delta=1e-8)

    def test_step_books_only_widening_beyond_the_pipe(self):
        B1, dV = xw.step(0.10, 0.12, 0.3, 0.05, M, N, KD, 0.0, 10.0)   # pipe has grown past the notch
        adv = 0.10 + xw.rate(0.05, 0.10, M, N, KD, 0.0) * 10.0
        self.assertAlmostEqual(B1, max(adv, 0.12), places=12)
        self.assertAlmostEqual(dV, xw.wall_area(0.3, M) * max(adv - 0.12, 0.0), places=12)


_CACHE = {}


def runs():
    if not _CACHE:
        T = StabilityTable.from_csv(str(TABLE))
        _CACHE["off"] = PipingRun(p1_case(), T, dt=0.5).run(60.0)
        _CACHE["on"] = PipingRun(p1_case(exit_widening=True), T, dt=0.5).run(60.0)
    return _CACHE


class TestCoupled(unittest.TestCase):
    def test_option_off_reproduces_exactly(self):
        """H-A7 (and no feedback in H1-a alone: the pipe relations already have a free outlet, so the
        event sequence with the option on is the same too)."""
        a, b = runs()["off"], runs()["on"]
        key = lambda r: [(e["type"], e["t"], e.get("x_in"), e.get("b")) for e in r.events]
        self.assertEqual(key(a), key(runs()["off"]))
        self.assertEqual(key(a), key(b))
        self.assertIsNone(a.s.B_e)

    def test_widening_and_budget(self):
        r = runs()["on"]
        pts = [x for x in r.series if "B_e" in x]
        self.assertTrue(pts)
        self.assertAlmostEqual(pts[0]["B_e"], p1_case().b0, places=12)                  # H-A1
        self.assertTrue(all(x["B_e"] >= x["b_out"] - 1e-12 for x in pts))
        Bs = [x["B_e"] for x in pts]
        self.assertTrue(all(b2 >= b1 - 1e-12 for b1, b2 in zip(Bs, Bs[1:])))
        self.assertGreater(r.s.B_e, r.s.pipe.b)
        self.assertGreater(r.s.V_exit, 0.0)
        self.assertLess(r.max_water_err, 1e-9)

    def test_separate_experiments(self):
        T = StabilityTable.from_csv(str(TABLE))
        with self.assertRaises(ValueError):
            PipingRun(p1_case(exit_widening=True, exit_headcut=True), T)


if __name__ == "__main__":
    unittest.main()
