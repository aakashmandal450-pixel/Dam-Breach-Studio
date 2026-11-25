"""Theory Part 5 verification, stage 3c: the piping driver (event sequence, event location, budgets).
Uses the ARS P1 geometry with a high k_d so the pipe stage lasts about 35 s (fast); the physics checks
do not depend on the erodibility value."""
import math
import unittest
from pathlib import Path

from lumped import roof
from lumped.geometry import Dam
from lumped.model import Reservoir
from lumped.piping_run import PipingCase, PipingRun, timeline
from lumped.stability_table import StabilityTable

TABLE = Path(__file__).resolve().parents[1] / "verification" / "stability_table.csv"
G = 9.81
RHO_D, GS, W = 1696.0, 2.65, 0.1149
N = 1 - RHO_D / (GS * 1000)
SOIL = roof.Soil(c_u0=5000.0, rho=0.0, gamma_sat=(RHO_D + N * 1000) * G, gamma_moist=RHO_D * (1 + W) * G)


def p1_case(**kw):
    d = dict(dam=Dam(1.3, 1.83, 3.0, 3.0, 100.0), soil=SOIL, kd=150e-6, tau_c=0.0, b0=0.04, D0=0.04,
             z_inv0=0.2, z_s0=1.1, porosity=N)
    d.update(kw)
    return PipingCase(**d)


def first(run, kind):
    return next(e for e in run.events if e["type"] == kind)


_CACHE = {}


class DriverMixin:
    @classmethod
    def setUpClass(cls):
        if not _CACHE:                                   # one set of runs shared by all test classes
            _CACHE["T"] = StabilityTable.from_csv(str(TABLE))
            _CACHE["runs"] = {dt: PipingRun(p1_case(), _CACHE["T"], dt=dt).run(60.0) for dt in (2.0, 1.0, 0.5)}
        cls.T, cls.runs = _CACHE["T"], _CACHE["runs"]


class TestSequence(DriverMixin, unittest.TestCase):
    def test_boundary_retreat_before_interior_collapse(self):
        """The first failure is an inlet retreat (boundary), not a crater; the crater starts later."""
        r = self.runs[1.0]
        kinds = [e["type"] for e in r.events]
        self.assertEqual(kinds[0], "inlet_retreat")
        self.assertIn("crater_start", kinds)
        self.assertLess(kinds.index("inlet_retreat"), kinds.index("crater_start"))
        self.assertEqual(kinds.count("crater_start"), 1)

    def test_outcomes_recorded_separately(self):
        types = {e["type"] for e in self.runs[1.0].events}
        allowed = {"inlet_retreat", "outlet_retreat", "outlet_uplift_C", "crater_start", "crater_extend_up",
                   "crater_extend_down", "wall_up", "wall_down", "wall_sides", "handover"}
        self.assertTrue(types <= allowed | {t for t in types if t.startswith("stop_")})

    def test_deterministic(self):
        a = PipingRun(p1_case(), self.T, dt=1.0).run(60.0)
        b = self.runs[1.0]
        self.assertEqual([(e["type"], e["t"]) for e in a.events], [(e["type"], e["t"]) for e in b.events])

    def test_crater_state_at_start(self):
        """At the start the crater is the failed reach, width b_p, depth ~ a_p (n_d = n), level from the pores."""
        e = first(self.runs[1.0], "crater_start")
        self.assertAlmostEqual(e["cr_W"], e["b"], 12)
        zg = Dam(1.3, 1.83, 3.0, 3.0, 100.0).H
        self.assertLess(e["z_d"], zg + 1e-9)
        self.assertGreater(e["cr_x2"] - e["cr_x1"], 0.0)

    def test_timeline_merges_continuous_motion(self):
        tl = timeline(self.runs[1.0])
        self.assertEqual(tl[0]["type"], "inlet_retreat")
        self.assertGreater(tl[0]["n"], 1)
        self.assertAlmostEqual(tl[0]["dist"], sum(e["dist"] for e in self.runs[1.0].events
                                                  if e["type"] == "inlet_retreat" and e["t"] <= tl[0]["t_end"]), 12)


class TestEventLocation(DriverMixin, unittest.TestCase):
    def test_onset_inside_the_step(self):
        """The onset of the inlet retreat is located inside a step, not at a step boundary."""
        for dt, r in self.runs.items():
            t = first(r, "inlet_retreat")["t"]
            self.assertGreater(abs(t / dt - round(t / dt)), 1e-6)

    def test_first_order_convergence(self):
        """Crater start time converges with p ~ 1 in dt (5.8: collapse time converges with p ~ 1)."""
        t = {dt: first(r, "crater_start")["t"] for dt, r in self.runs.items()}
        d1, d2 = t[2.0] - t[1.0], t[1.0] - t[0.5]
        p = math.log(abs(d1 / d2), 2)
        self.assertTrue(0.6 < p < 1.6, f"order {p:.2f} (times {t})")
        self.assertLess(abs(d2), 0.05 * t[0.5])


class TestBudgets(DriverMixin, unittest.TestCase):
    def test_constant_level_budgets(self):
        for r in self.runs.values():
            self.assertLess(r.max_water_err, 1e-12)
            self.assertLess(r.max_solids_err, 1e-12)
            for e in r.events:
                self.assertLess(abs(e["water_err"]), 1e-9)
                if "solids_err" in e:
                    self.assertLess(abs(e["solids_err"]), 1e-9)

    def test_variable_level_reservoir_budget(self):
        """A finite reservoir (prismatic, 500 m2) with inflow: water budget closes every step."""
        res = Reservoir({0.0: 0.0, 2.0: 1000.0, 4.0: 2000.0})
        case = p1_case(constant_level=False, reservoir=res, inflow=lambda t: 0.05)
        r = PipingRun(case, self.T, dt=1.0).run(60.0)
        self.assertLess(r.max_water_err, 1e-12)
        self.assertTrue(r.events)


if __name__ == "__main__":
    unittest.main()
