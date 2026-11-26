"""Theory Part 5 verification: exit headcut at the pipe outlet (5.6, draft 5.10)."""
import unittest
from pathlib import Path

from lumped import exit_headcut as xh
from lumped import ends
from lumped.geometry import Dam
from lumped import headcut as hc

DAM = Dam(6.0, 3.0, 3.0, 3.0, 50.0)          # a taller dam, so a plunging drop can form under the outlet
KD, TC, CU, GAM, N = 20e-6, 0.0, 10000.0, 20000.0, 0.016


def start(z_inv=3.0, D=0.3):
    x_o = DAM.x_down(z_inv + D / 2)
    return xh.ExitHeadcut(x_h=x_o, z_h=z_inv), x_o


class TestExitHeadcut(unittest.TestCase):
    def test_no_flow_no_change(self):
        h, x_o = start()
        self.assertEqual(xh.step(h, DAM, 0.0, 0.3, 3.0, 3.3, x_o, 10.0, KD, TC, CU, GAM, N), (h, x_o))

    def test_surface_then_plunging(self):
        """Stage 1 lowers the base without moving the brink; plunging starts once the drop exceeds d_c."""
        h, x_o = start()
        Q, b = 0.05, 0.3
        dc = hc.critical_depth_unit(Q / b)
        saw2 = False
        for _ in range(20000):
            h1, x_o1 = xh.step(h, DAM, Q, b, 3.0, 3.3, x_o, 1.0, KD, TC, CU, GAM, N)
            self.assertLessEqual(h1.z_h, h.z_h); self.assertGreaterEqual(h1.z_h, 0.0)
            self.assertLessEqual(h1.x_h, h.x_h)
            if h1.stage == 1:
                self.assertEqual(h1.x_h, h.x_h)
            else:
                self.assertGreater(3.0 - h1.z_h, dc - 1e-12)
                saw2 = True
            h, x_o = h1, x_o1
            if saw2 and h.x_h < x_o + 1e-9 and h.x_h < DAM.x_c1:
                break
        self.assertTrue(saw2)

    def test_outlet_follows_brink_and_volumes(self):
        """Once the brink passes the outlet, x_o = x_h; the roof removed is b * roof area exactly, and the
        channel volume is b * channel area (monotone, never counted twice)."""
        h, x_o0 = start()
        x_o = x_o0
        b, z_inv, z_cr = 0.3, 3.0, 3.3
        h = xh.ExitHeadcut(x_h=x_o - 0.5, z_h=1.0, stage=2)       # a brink already 0.5 m upstream of the outlet
        h1, x_o1 = xh.step(h, DAM, 0.05, b, z_inv, z_cr, x_o, 1.0, KD, TC, CU, GAM, N)
        self.assertAlmostEqual(x_o1, h1.x_h, 12)
        self.assertAlmostEqual(h1.V_roof, b * ends.roof_area(DAM, z_cr, h1.x_h, x_o), 12)
        self.assertAlmostEqual(h1.vol, b * xh.channel_area(DAM, z_inv, h1.x_h, h1.z_h), 12)
        h2, x_o2 = xh.step(h1, DAM, 0.05, b, z_inv, z_cr, x_o1, 1.0, KD, TC, CU, GAM, N)
        self.assertAlmostEqual(h2.V_roof - h1.V_roof, b * ends.roof_area(DAM, z_cr, h2.x_h, x_o1), 12)
        self.assertGreaterEqual(h2.vol, h1.vol)

    def test_channel_area_simple(self):
        """Channel below the invert: from the face at the brink level down to z_h, out to the face."""
        A = xh.channel_area(DAM, 3.0, DAM.x_down(3.0), 2.0)
        # triangle between the face (slope 3H:1V) and the level z_h, over a 1 m drop: 1/2 * 3 * 1
        self.assertAlmostEqual(A, 1.5, 12)


class TestDriverOption(unittest.TestCase):
    def test_off_by_default_and_on_budgets(self):
        from lumped.tests.test_piping_run import p1_case, TABLE
        from lumped.stability_table import StabilityTable
        from lumped.piping_run import PipingRun
        T = StabilityTable.from_csv(str(TABLE))
        off = PipingRun(p1_case(), T, dt=1.0).run(60.0)
        self.assertIsNone(off.s.hc)
        on = PipingRun(p1_case(exit_headcut=True), T, dt=1.0).run(60.0)
        self.assertIsNotNone(on.s.hc)
        self.assertLess(on.max_water_err, 1e-12)
        self.assertLess(on.max_solids_err, 1e-12)
        self.assertGreater(on.s.hc.vol, 0.0)
        self.assertGreaterEqual(on.s.hc.z_h, 0.0)
        self.assertLessEqual(on.s.x_o, off.s.x_o + 1e-12)
        kinds = {e["type"] for e in on.events}
        self.assertNotIn("handover", kinds - {e["type"] for e in off.events})   # no breach created by the option


if __name__ == "__main__":
    unittest.main()
