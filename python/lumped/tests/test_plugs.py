"""Theory Part 5, section 5.7b (frozen 2026-11-26): D5 both mouths obstructed by the deposit, and the
D1-a plug breakthrough (5.26)-(5.28). ARS P1 geometry, high k_d (fast; the crater geometry does not
depend on k_d)."""
import unittest

from lumped.piping_run import GAMMA_W, PipingRun
from lumped.stability_table import StabilityTable
from lumped.tests.test_piping_run import N, SOIL, TABLE, p1_case

_CACHE = {}


def runs():
    if not _CACHE:
        T = StabilityTable.from_csv(str(TABLE))
        _CACHE["T"] = T
        _CACHE["sealed"] = PipingRun(p1_case(plugs=True), T, dt=0.5).run(700.0)
        _CACHE["light"] = PipingRun(p1_case(plugs=True, n_d=0.6), T, dt=0.5).run(40.0)
        _CACHE["inst_on"] = PipingRun(p1_case(plugs=True, debris="instant"), T, dt=0.5).run(60.0)
        _CACHE["inst_off"] = PipingRun(p1_case(debris="instant"), T, dt=0.5).run(60.0)
    return _CACHE


def ev(r, kind):
    return [e for e in r.events if e["type"] == kind]


class TestCriterion(unittest.TestCase):
    def test_icr_by_hand(self):
        r = runs()["sealed"]
        gs = (SOIL.gamma_sat - N * GAMMA_W) / (1 - N)
        gsd = (1 - N) * gs + N * GAMMA_W
        self.assertAlmostEqual(r.i_cr(0.3), (gsd - GAMMA_W) / GAMMA_W, places=12)
        self.assertAlmostEqual(r.i_cr(0.3) - r.i_cr(1e9), 0.0, places=9)    # c_d = 0: no width effect


class TestSealedP1(unittest.TestCase):
    """Frozen rules on P1: both mouths buried at crater start, neither plug reaches i_cr."""

    @classmethod
    def setUpClass(cls):
        cls.r = runs()["sealed"]

    def test_both_mouths_covered(self):
        self.assertEqual(len(ev(self.r, "plug_dn_formed")), 1)
        self.assertEqual(len(ev(self.r, "plug_up_formed")), 1)
        self.assertFalse(ev(self.r, "plug_dn_fail") or ev(self.r, "plug_up_fail"))

    def test_margins_by_hand(self):
        r, s = self.r, self.r.s
        cr, zc = s.crater, s.crater.level()
        m = r.plug_margins(s, zc)
        ell = cr.z_d - cr.z_cr
        self.assertAlmostEqual(m["dn"]["i"], (zc - cr.z_cr) / ell, places=12)
        ell_u = cr.z_d - s.pipe.z_cr
        self.assertAlmostEqual(m["up"]["i"], (s.z_s - max(zc, s.pipe.z_cr)) / ell_u, places=12)
        for d in m.values():
            self.assertAlmostEqual(d["M"], GAMMA_W * d["ell"] * (d["i_cr"] - d["i"]), places=9)
            self.assertLess(d["i"], d["i_cr"])

    def test_sealed_no_inflow(self):
        self.assertEqual(self.r.stopped[0], "sealed")
        self.assertEqual(self.r.hyd(self.r.s)["Q_res"], 0.0)


class TestBreakthrough(unittest.TestCase):
    """Lighter debris (n_d = 0.6, i_cr = 0.66): the upstream plug fails at crater start, the crater fills,
    then the downstream plug fails and the mouth reopens (D1-a)."""

    @classmethod
    def setUpClass(cls):
        cls.r = runs()["light"]

    def test_sequence(self):
        up, dn = ev(self.r, "plug_up_fail"), ev(self.r, "plug_dn_fail")
        self.assertEqual((len(up), len(dn)), (1, 1))
        self.assertLess(up[0]["t"], dn[0]["t"])
        for e in up + dn:
            self.assertGreaterEqual(e["i"], e["i_cr"] * (1 - 1e-6))
        self.assertTrue(self.r.s.crater.open_dn and self.r.s.crater.open_up)
        self.assertGreater(self.r.hyd(self.r.s)["Q_out_cr"], 0.0)

    def test_export_is_the_plug(self):
        cr, dn, up = self.r.s.crater, ev(self.r, "plug_dn_fail")[0], ev(self.r, "plug_up_fail")[0]
        self.assertAlmostEqual(dn["V_plug"], cr.b_p * cr.a_p * dn["ell"], places=12)
        self.assertAlmostEqual(cr.V_exp, dn["V_plug"], places=12)          # the upstream plug is not exported
        self.assertAlmostEqual(cr.V_exp_out, dn["V_plug"], places=12)
        self.assertEqual(up["V_plug"], 0.0)

    def test_budgets(self):
        self.assertLess(self.r.max_water_err, 1e-9)
        self.assertLess(self.r.max_solids_err, 1e-9)


class TestTreatmentsUnchanged(unittest.TestCase):
    def test_instant_identical_with_plugs(self):
        a, b = runs()["inst_on"], runs()["inst_off"]
        self.assertEqual([(e["type"], e["t"]) for e in a.events], [(e["type"], e["t"]) for e in b.events])
        self.assertFalse(any(e["type"].startswith(("plug_", "mouth_")) for e in a.events))


if __name__ == "__main__":
    unittest.main()
