"""Theory Part 5, section 5.7a.11 (state and geometry rules, decided 2026-11-26).

  crater_spilling   a blocked crater whose water leaves over a rim below the reservoir is never 'sealed';
                    the spill is its own water-budget term and does not erode the rim (overtopping's job)
  pipe <= crater    a pipe connected to a crater whose walls stand does not widen past the crater width;
                    widening only through the wall-failure rule, with its volume in the solids budget
  floor >= base     no crater floor below the dam base z = 0

The runs use the ARS P1 geometry with a high k_d (fast); the crater geometry does not depend on k_d.
At c_u0 = 4 kPa (level) the crater's downstream rim (1.09 m) is below the reservoir (1.10 m); at 7 kPa
the instant-removal walls stand, so the upstream pipe would outgrow the crater without the width rule.
"""
import math
import unittest

from lumped import piping as pp
from lumped import roof
from lumped.piping_run import PipingRun
from lumped.stability_table import StabilityTable
from lumped.tests.test_piping_run import SOIL, TABLE, p1_case

_CACHE = {}


def soil(cu):
    return roof.Soil(c_u0=cu, rho=0.0, gamma_sat=SOIL.gamma_sat, gamma_moist=SOIL.gamma_moist)


def runs():
    if not _CACHE:
        T = StabilityTable.from_csv(str(TABLE))
        _CACHE["spill"] = PipingRun(p1_case(soil=soil(4000.0), debris="level"), T, dt=1.0).run(800.0)
        _CACHE["stand"] = PipingRun(p1_case(soil=soil(7000.0), debris="instant"), T, dt=0.5).run(200.0)
    return _CACHE


class TestErodeWidthLimit(unittest.TestCase):
    def test_sides_stop_at_b_max_volume_exact(self):
        p = pp.Pipe(0.30, 0.30, 0.20, 5.0)
        free, V_free = pp.erode(p, 1e-4, 1, 0.30, 100.0)
        cap, V_cap = pp.erode(p, 1e-4, 1, 0.30, 100.0, b_max=0.305)
        self.assertGreater(free.b, 0.305)
        self.assertAlmostEqual(cap.b, 0.305, places=12)
        self.assertAlmostEqual(cap.D, free.D, places=12)            # floor and roof unaffected
        self.assertAlmostEqual(V_cap, (cap.b * cap.D - p.b * p.D) * p.L, places=12)
        self.assertLess(V_cap, V_free)

    def test_inactive_cap_changes_nothing(self):
        p = pp.Pipe(0.30, 0.30, 0.20, 5.0)
        self.assertEqual(pp.erode(p, 1e-4, 1, 0.3, 10.0), pp.erode(p, 1e-4, 1, 0.3, 10.0, b_max=1.0))


class TestCraterSpilling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = runs()["spill"]

    def test_rim_below_reservoir_is_not_sealed(self):
        r, cr = self.r, self.r.s.crater
        self.assertIsNotNone(cr)
        self.assertLess(cr.z_rim, r.s.z_s)
        self.assertNotEqual(r.stopped and r.stopped[0], "sealed")
        self.assertFalse(any(e["type"] == "sealed" for e in r.events))
        self.assertTrue(any(e["type"] == "spill_start" for e in r.events))
        self.assertGreater(r.hyd(r.s)["Q_spill"], 0.0)
        self.assertEqual(cr.a_open(), 0.0)

    def test_spill_is_a_separate_budget_term(self):
        r = self.r
        self.assertGreater(r.s.cum_spill, 0.0)
        self.assertLessEqual(r.s.cum_spill, r.s.cum_out + 1e-12)
        self.assertLess(r.max_water_err, 1e-9)
        last = r.series[-1]
        self.assertIn("cum_spill", last)

    def test_rim_not_eroded(self):
        """No rim lowering: the crater ends and the rim elevation do not move while it spills."""
        r = self.r
        t0 = next(e["t"] for e in r.events if e["type"] == "spill_start")
        after = [e for e in r.events if e["t"] > t0 and e["type"].startswith(("crater_", "wall_"))]
        self.assertEqual(after, [])


class TestPipeWithinCrater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = runs()["stand"]

    def test_walls_stand_and_pipe_capped(self):
        r = self.r
        self.assertFalse(any(e["type"].startswith("wall_") for e in r.events))
        pts = [x for x in r.series if "cr_W" in x]
        self.assertTrue(pts)
        self.assertTrue(all(x["b"] <= x["cr_W"] * (1 + 1e-9) for x in pts))
        self.assertAlmostEqual(r.s.pipe.b, r.s.crater.W, places=9)   # the cap is active, not idle

    def test_floor_never_below_base(self):
        r = self.r
        zs = [x["z_d"] for x in r.series if "z_d" in x] + [e["z_d"] for e in r.events if "z_d" in e]
        self.assertTrue(zs)
        self.assertGreaterEqual(min(zs), -1e-9)
        self.assertNotEqual(r.stopped and r.stopped[0], "geometry_error")

    def test_solids_budget_closed(self):
        self.assertLess(self.r.max_solids_err, 1e-9)
        self.assertLess(self.r.max_water_err, 1e-9)


if __name__ == "__main__":
    unittest.main()
