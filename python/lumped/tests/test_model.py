"""Whole-model checks: water balance, geometric limits, every case runs."""
import sys
import unittest
from pathlib import Path

PY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PY / "calibration"))
import cases as C  # noqa: E402

from lumped.model import run_case  # noqa: E402

ALL = sorted(p.stem for p in (PY / "calibration" / "cases").glob("*.json"))


class TestModel(unittest.TestCase):
    def test_every_case_runs_short(self):
        """All 20 cases start and run 3000 steps; water balance closes; width within the valley."""
        for cid in ALL:
            with self.subTest(case=cid):
                case = C.load_case(cid)
                t_end = min(case.get("t_end", 43200.0), 3600.0)
                r = run_case(case, dt=t_end / 3000, t_end=t_end)
                self.assertLess(abs(r["water_balance_rel"]), 1e-9)
                self.assertLessEqual(r["B_top"], case["section_width"] * (1 + 1e-9))

    def test_full_run_balance(self):
        for cid in ("Castlewood", "E1S1"):
            r = run_case(C.load_case(cid))
            self.assertLess(abs(r["water_balance_rel"]), 1e-9, cid)


if __name__ == "__main__":
    unittest.main()
