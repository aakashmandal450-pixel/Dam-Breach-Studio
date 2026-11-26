"""Theory Part 5 verification, stage 3a: classification of roof failures and end retreat (5.5b)."""
import math
import unittest
from pathlib import Path

from lumped import ends
from lumped import piping as pp
from lumped import roof
from lumped.geometry import Dam
from lumped.stability_table import StabilityTable

TABLE = Path(__file__).resolve().parents[1] / "verification" / "stability_table.csv"


def rc_of(xs, ms):
    return roof.RoofCheck(list(xs), [1.0] * len(xs), [0.0] * len(xs), list(ms), [0.0] * len(xs),
                          min(ms), 0.0, 0.0, 0.0, (0.0, 0.0))


class TestClassify(unittest.TestCase):
    def test_three_outcomes_kept_separate(self):
        f = ends.classify(rc_of([0, 1, 2, 3, 4, 5, 6], [-2, -1, 1, -1, 2, 3, -4]))
        self.assertAlmostEqual(f.x_up, 1 + 1 * 1 / 2, 12)        # zero between x=1 (-1) and x=2 (+1)
        self.assertAlmostEqual(f.x_dn, 6 - 1 * 4 / 7, 12)        # zero between x=6 (-4) and x=5 (+3)
        self.assertEqual(f.interior, [(3, 3)])
        self.assertFalse(f.whole)

    def test_interior_only(self):
        f = ends.classify(rc_of([0, 1, 2, 3], [1, -1, -1, 2]))
        self.assertIsNone(f.x_up); self.assertIsNone(f.x_dn)
        self.assertEqual(f.interior, [(1, 2)])

    def test_no_failure(self):
        f = ends.classify(rc_of([0, 1, 2], [1, 2, 3]))
        self.assertEqual((f.x_up, f.x_dn, f.interior, f.whole), (None, None, [], False))

    def test_whole_roof(self):
        self.assertTrue(ends.classify(rc_of([0, 1, 2], [-1, -1, -1])).whole)

    def test_no_interpolation_into_unstable_section(self):
        """A last failing section with no stable state: the end moves to that section, not beyond."""
        f = ends.classify(rc_of([0, 1, 2, 3], [-1, -math.inf, 2, 3]))
        self.assertEqual(f.x_up, 1)

    def test_retreat_bounded_by_failed_reach(self):
        """The cut lies between the last failing and the first stable section, never past it."""
        for m in ([-5, 1e-9], [-1e-9, 5], [-1, 1]):
            f = ends.classify(rc_of([0, 1, 2], [m[0], m[1], 4]))
            self.assertTrue(0 <= f.x_up <= 1)


class TestRetreatVolumes(unittest.TestCase):
    dam = Dam(1.3, 1.83, 3.0, 3.0, 100.0)

    def test_roof_area_exact(self):
        z_cr = 0.4
        # upstream face from x_up(0.4) = 1.2 to the crest edge 3.9: triangle 2.7 x 0.9 / 2 = 1.215
        self.assertAlmostEqual(ends.roof_area(self.dam, z_cr, 1.2, 3.9), 0.5 * 2.7 * 0.9, 12)
        # crest 3.9 -> 5.73: rectangle 1.83 x 0.9
        self.assertAlmostEqual(ends.roof_area(self.dam, z_cr, 3.9, 5.73), 1.83 * 0.9, 12)

    def test_volume_conserved_and_not_double_counted(self):
        """Successive retreats remove exactly the roof between successive ends; their sum equals one retreat
        to the final position, and removed + remaining = the initial roof."""
        b, z_cr = 0.2, 0.4
        x_in, x_o = self.dam.x_up(0.3), self.dam.x_down(0.3)
        total = b * ends.roof_area(self.dam, z_cr, x_in, x_o)
        steps_up = [1.5, 2.2, 3.0]
        steps_dn = [8.4, 7.9]
        removed, xi, xo = 0.0, x_in, x_o
        for k in range(3):
            f = ends.Failures(steps_up[k], steps_dn[k] if k < 2 else None, [], False)
            r = ends.retreat(self.dam, b, z_cr, xi, xo, f)
            removed += r.V_up + r.V_dn
            xi, xo = r.x_in, r.x_o
        once = ends.retreat(self.dam, b, z_cr, x_in, x_o, ends.Failures(3.0, 7.9, [], False))
        self.assertAlmostEqual(removed, once.V_up + once.V_dn, 12)
        remaining = b * ends.roof_area(self.dam, z_cr, xi, xo)
        self.assertAlmostEqual(removed + remaining, total, 12)

    def test_ends_never_cross(self):
        r = ends.retreat(self.dam, 0.2, 0.4, 2.0, 8.0, ends.Failures(9.0, 1.0, [], False))
        self.assertLessEqual(r.x_in, r.x_o)
        self.assertEqual((r.x_in, r.x_o), (8.0, 8.0))

    def test_interior_does_not_move_ends(self):
        r = ends.retreat(self.dam, 0.2, 0.4, 2.0, 8.0, ends.Failures(None, None, [(4.0, 5.0)], False))
        self.assertEqual((r.x_in, r.x_o, r.V_up, r.V_dn), (2.0, 8.0, 0.0, 0.0))


class TestP1Geometry(unittest.TestCase):
    def test_first_failure_is_an_inlet_retreat(self):
        """ARS P1 geometry, 0.2 m pipe at 0.2 m, reservoir 1.1 m, c_u0 5 kPa: the weakest sections are at the
        upstream end, so the outcome is an inlet retreat, not a crater."""
        T = StabilityTable.from_csv(str(TABLE))
        dam = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
        b = D = 0.2
        z_inv, z_s = 0.2, 1.1
        x_in, x_o = dam.x_up(z_inv + D / 2), dam.x_down(z_inv + D / 2)
        pipe = pp.Pipe(b, D, z_inv, x_o - x_in)
        fl = pp.pipe_flow(z_s - z_inv, b, D, pipe.L, 0.016)
        soil = roof.Soil(5000.0, 0.0, 20000.0, 18730.0)
        rc = roof.check(dam, pipe, x_in, x_o, z_s, fl, soil, T)
        f = ends.classify(rc)
        self.assertIsNotNone(f.x_up)
        self.assertEqual(f.interior, [])
        self.assertLess(f.x_up, dam.x_c0)             # the retreat stays on the upstream face
        r = ends.retreat(dam, b, pipe.z_cr, x_in, x_o, f)
        self.assertGreater(r.V_up, 0.0)
        self.assertEqual(r.x_o, x_o)


if __name__ == "__main__":
    unittest.main()
