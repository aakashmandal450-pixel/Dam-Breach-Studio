"""Theory Part 5 verification, stage 2: roof check along the pipe (5.5, 5.5b, 5.8, 5.9, 5.15, 5.24)."""
import math
import unittest
from pathlib import Path

from lumped import piping as pp
from lumped import roof
from lumped.geometry import Dam
from lumped.hydraulics import G
from lumped.stability_table import StabilityTable, TableRangeError

TABLE = Path(__file__).resolve().parents[1] / "verification" / "stability_table.csv"
GW = roof.GAMMA_W
N = 0.016


def p1_like(b=0.04, D=None, z_inv=0.2, z_s=1.1):
    """ARS P1 geometry (1.3 m high, 1.83 m crest, 3H:1V), pipe through the whole dam."""
    dam = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
    D = D or b
    z_bp = z_inv + D / 2
    x_in, x_o = dam.x_up(z_bp), dam.x_down(z_bp)
    pipe = pp.Pipe(b, D, z_inv, x_o - x_in)
    fl = pp.pipe_flow(z_s - z_inv, b, D, pipe.L, N)
    return dam, pipe, x_in, x_o, z_s, fl


class TableMixin:
    @classmethod
    def setUpClass(cls):
        cls.T = StabilityTable.from_csv(str(TABLE))
        cls.soil = roof.Soil(c_u0=5000.0, rho=0.0, gamma_sat=20000.0, gamma_moist=18730.0)


class TestSoffitPressure(unittest.TestCase):
    def test_outlet_head_is_centreline(self):
        """(5.8) with (5.3): the piezometric head at the outlet is the pipe centreline (free outlet)."""
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.1)
        self.assertEqual(fl.w, 1)
        head_out = z_s - (1 + pp.K_U + fl.f * pipe.L / (4 * fl.R)) * fl.U ** 2 / (2 * G)
        self.assertAlmostEqual(head_out, pipe.z_inv + pipe.D / 2, 10)
        self.assertEqual(roof.soffit_pressure(pipe.L, z_s, pipe.z_cr, fl), 0.0)

    def test_inlet_and_linear_fall(self):
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.1)
        p0 = roof.soffit_pressure(0.0, z_s, pipe.z_cr, fl)
        self.assertAlmostEqual(p0, GW * (z_s - (1 + pp.K_U) * fl.U ** 2 / (2 * G) - pipe.z_cr), 9)
        xs = [0.0, 1.0, 2.0]
        ps = [roof.soffit_pressure(x, z_s, pipe.z_cr, fl) for x in xs]
        self.assertAlmostEqual(ps[0] - ps[1], ps[1] - ps[2], 9)      # linear while positive

    def test_zero_when_part_full(self):
        fl = pp.pipe_flow(0.05, 0.1, 0.1, 5.0, N)
        self.assertEqual(fl.w, 0)
        self.assertEqual(roof.soffit_pressure(0.0, 0.3, 0.35, fl), 0.0)


class TestUnitWeightAndLoad(unittest.TestCase):
    def test_gamma_bar(self):
        s = roof.Soil(5000, 0, 20000, 18000)
        self.assertEqual(roof.gamma_bar(1.0, 0.0, 2.0, s), 20000)      # phreatic above the cover: saturated
        self.assertEqual(roof.gamma_bar(1.0, 0.0, -1.0, s), 18000)     # phreatic below the crown: moist
        self.assertAlmostEqual(roof.gamma_bar(1.0, 0.0, 0.25, s), 0.25 * 20000 + 0.75 * 18000, 9)

    def test_surface_load_only_under_reservoir(self):
        dam = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
        self.assertAlmostEqual(roof.surface_load(dam, 1.5, 1.1), GW * (1.1 - 0.5), 9)
        self.assertEqual(roof.surface_load(dam, 3.0 * 1.2, 1.1), 0.0)  # face above the water
        self.assertEqual(roof.surface_load(dam, 5.0, 1.1), 0.0)        # crest
        self.assertEqual(roof.surface_load(dam, 9.0, 1.1), 0.0)        # downstream face below z_s


class TestMechanismA(TableMixin, unittest.TestCase):
    def test_dry_limit_b_crit(self):
        """(5.9) without water: FS_A = 2 c_u / (gamma b) for any cover, so b_crit = 2 c_u/gamma."""
        soil = roof.Soil(5000.0, 0.0, 19000.0, 19000.0)
        b_crit = 2 * soil.c_u0 / soil.gamma_sat
        for z_inv in (0.1, 0.4, 0.8):
            for b in (0.2, b_crit, 0.8):
                dam = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
                z_bp = z_inv + 0.05
                x_in, x_o = dam.x_up(z_bp), dam.x_down(z_bp)
                pipe = pp.Pipe(b, 0.1, z_inv, x_o - x_in)
                dry = pp.pipe_flow(0.0, b, 0.1, pipe.L, N)
                rcA = roof.RoofCheck([], [], [], [], [], 0, 0, 0, 0, (0, 0))
                roof._mechanisms_ab(rcA, dam, pipe, x_in, x_o, -1.0, dry, soil)
                self.assertAlmostEqual(rcA.FS_A, 2 * soil.c_u0 / (soil.gamma_sat * b), 9)
        self.assertAlmostEqual(2 * soil.c_u0 / (soil.gamma_sat * b_crit), 1.0, 12)


class TestCriterion(TableMixin, unittest.TestCase):
    def test_margins_match_table(self):
        """(5.15): M_c = c_u0 N_c - (sigma_s - p_s) with N from the table (full pipe through 5.16b)."""
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.1)
        rc = roof.check(dam, pipe, x_in, x_o, z_s, fl, self.soil, self.T)
        self.assertGreater(len(rc.x), 10)
        for k in (0, len(rc.x) // 2, len(rc.x) - 1):
            x = rc.x[k]
            C = dam.z_dam(x) - pipe.z_cr
            sig = roof.surface_load(dam, x, z_s)
            ps = roof.soffit_pressure(x - x_in, z_s, pipe.z_cr, fl)
            g_b = roof.gamma_bar(C, pipe.z_cr, z_s, self.soil) * pipe.b / self.soil.c_u0
            nc = self.T.query(C / pipe.b, 1.0, g_b, 0.0, gw_b=GW * pipe.b / self.soil.c_u0,
                              full=True)["mid"]
            self.assertAlmostEqual(rc.net[k], sig - ps, 9)
            self.assertAlmostEqual(rc.M_c[k], self.soil.c_u0 * nc - (sig - ps), 6)

    def test_bounds_order(self):
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.1)
        lo = roof.check(dam, pipe, x_in, x_o, z_s, fl, self.soil, self.T, bound="lo")
        hi = roof.check(dam, pipe, x_in, x_o, z_s, fl, self.soil, self.T, bound="hi")
        self.assertTrue(all(a <= b + 1e-9 for a, b in zip(lo.M_c, hi.M_c)))

    def test_min_and_location_written(self):
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.2)
        rc = roof.check(dam, pipe, x_in, x_o, z_s, fl, self.soil, self.T)
        self.assertEqual(rc.min_M_c, min(rc.M_c))
        self.assertEqual(rc.x_star, rc.x[rc.M_c.index(rc.min_M_c)])
        self.assertTrue(math.isfinite(rc.FS_A) and math.isfinite(rc.M_B))

    def test_section_spacing(self):
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.1)
        xs = roof.sections(x_in, x_o, 0.05)
        self.assertAlmostEqual(xs[0], x_in, 12); self.assertAlmostEqual(xs[-1], x_o, 12)
        self.assertLessEqual(max(b - a for a, b in zip(xs, xs[1:])), 0.05 + 1e-12)

    def test_end_lips_excluded_and_reported(self):
        """Sections with C < 0.25 b_p are not checked; the downstream lip spans zd (D/2 + 0.25 b) (+- dx)."""
        dam, pipe, x_in, x_o, z_s, fl = p1_like(0.1)
        rc = roof.check(dam, pipe, x_in, x_o, z_s, fl, self.soil, self.T)
        self.assertTrue(all(C >= roof.C_MIN * pipe.b for C in rc.C))
        expect = dam.zd * (pipe.D / 2 + roof.C_MIN * pipe.b)
        self.assertAlmostEqual(rc.lips[1], expect, delta=0.5 * pipe.b + 1e-9)
        self.assertAlmostEqual(rc.lips[0], dam.zu * (pipe.D / 2 + roof.C_MIN * pipe.b), delta=0.5 * pipe.b + 1e-9)

    def test_out_of_table_raises(self):
        """A section outside the table (here C/b_p > 32) is a numerical error, never a collapse."""
        dam = Dam(10.0, 5.0, 3.0, 3.0, 100.0)
        x_in, x_o = dam.x_up(0.51), dam.x_down(0.51)
        pipe = pp.Pipe(0.02, 0.02, 0.5, x_o - x_in)
        fl = pp.pipe_flow(9.0 - 0.5, 0.02, 0.02, pipe.L, N)
        with self.assertRaises(TableRangeError):
            roof.check(dam, pipe, x_in, x_o, 9.0, fl, self.soil, self.T)

    def test_no_stable_roof_flagged(self):
        """Tall pipe, heavy weak soil, thin cover: no stable state -> M_c = -inf and noStableRoof listed."""
        dam = Dam(1.0, 1.0, 3.0, 3.0, 100.0)
        b, D, z_inv = 0.2, 0.4, 0.5                     # a/b = 2, crown at 0.9, crest cover 0.1 m -> C/b 0.5
        soil = roof.Soil(c_u0=1300.0, rho=0.0, gamma_sat=19000.0, gamma_moist=19000.0)   # g ~ 2.9
        x_in, x_o = dam.x_up(z_inv + D / 2), dam.x_down(z_inv + D / 2)
        pipe = pp.Pipe(b, D, z_inv, x_o - x_in)
        dry = pp.pipe_flow(0.0, b, D, pipe.L, N)
        T = self.T
        try:
            rc = roof.check(dam, pipe, x_in, x_o, -1.0, dry, soil, T)
        except TableRangeError as e:
            self.fail(f"query left the table: {e}")
        self.assertTrue(rc.no_stable, "expected a no-stable-state section")
        self.assertEqual(rc.min_M_c, -math.inf)
        statuses = {s for _, st in rc.no_stable for s in st}
        self.assertTrue(statuses <= {"SELF_UNSTABLE", "NO_STATIC_BOUND"})

    def test_failing_reaches(self):
        rc = roof.RoofCheck([0, 1, 2, 3, 4, 5], [1] * 6, [0] * 6, [-1, -2, 3, 4, -1, 5], [0] * 6,
                            -2, 1, 0, 0, (0, 0))
        self.assertEqual(roof.failing_reaches(rc), [(0, 1, True, False), (4, 4, False, False)])
        rc.M_c = [1, 1, 1, 1, -1, -1]
        self.assertEqual(roof.failing_reaches(rc), [(4, 5, False, True)])

    def test_crossing_fraction(self):
        self.assertAlmostEqual(roof.crossing_fraction(3.0, -1.0), 0.75, 12)
        self.assertEqual(roof.crossing_fraction(3.0, -math.inf), 1.0)
        with self.assertRaises(ValueError):
            roof.crossing_fraction(-1.0, -2.0)


if __name__ == "__main__":
    unittest.main()
