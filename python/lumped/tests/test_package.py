"""Phase 0 smoke test: the package imports and the 2-D physics it will reuse is importable."""
import unittest


class TestPackage(unittest.TestCase):
    def test_import_and_version(self):
        import lumped
        self.assertRegex(lumped.__version__, r"^\d+\.\d+\.\d+$")

    def test_2d_physics_importable(self):
        import breach_engine_2d_v3_2 as E
        for name in ("SedimentTransport", "ChenVertical", "ikeda_side_slope_factor",
                     "BankStability", "Headcut", "Reservoir"):
            self.assertTrue(hasattr(E, name), name)


if __name__ == "__main__":
    unittest.main()
