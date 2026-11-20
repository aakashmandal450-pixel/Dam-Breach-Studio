"""Theory Part 4 verification (docs/theory/04_headcut.md, Section 4.7)."""
import math
import sys
import unittest
from pathlib import Path

from lumped import headcut as hc
from lumped.hydraulics import G, RHO_W

GW = RHO_W * G
CAL = Path(__file__).resolve().parents[2] / "calibration"


def hand_tau_hf(Hh, dc, dbw):
    """Independent transcription of DSO-2017-02 App. A1 Eqs. 3-7, written out step by step."""
    r = (Hh - dbw) / Hh
    Cn = 0.146 + 27.5 * r * (dc / Hh) ** 0.852 * math.exp(-6.1 * r)
    base = (0.823 + (Hh - dbw) / dc) / 0.483
    Xws = dc * base ** (1.0 / (Cn + 1.6))
    Sws = -0.483 * (Cn + 1.6) * (Xws / dc) ** (Cn + 0.6)
    Xp = Xws - dbw / Sws - 0.411 * dc
    return 0.025 * GW * dc * (Hh / dc) ** 0.026 * (dc / Xp) ** 1.06 * (dbw / dc) ** 0.221


class TestFaceStress(unittest.TestCase):
    def test_hand_calculation(self):
        for Hh, dc, dbw in [(1.0, 0.3, 0.3), (2.0, 0.6, 0.8), (5.0, 1.2, 1.5), (0.6, 0.1, 0.1)]:
            self.assertAlmostEqual(hc.face_stress(Hh, dc, dbw), hand_tau_hf(Hh, dc, dbw), places=10)

    def test_no_drop_no_stress(self):
        self.assertEqual(hc.face_stress(0.2, 0.3, 0.3), 0.0)    # H_h <= d_bw: no plunging jet
        self.assertEqual(hc.face_stress(1.0, 0.0, 0.0), 0.0)

    def test_tailwater_floor(self):
        # d_bw is taken >= d_c
        self.assertEqual(hc.face_stress(1.0, 0.3, 0.1), hc.face_stress(1.0, 0.3, 0.3))


class TestUndercut(unittest.TestCase):
    gt = 19.5e3

    def test_strong_soil_low_drop_positive(self):
        self.assertGreater(hc.undercut_at_failure(0.5, 0.1, 0.1, 10e3, self.gt), 0.0)

    def test_tall_face_cannot_stand(self):
        cu = 10e3
        self.assertLessEqual(hc.undercut_at_failure(6.0 * cu / self.gt, 0.3, 0.3, cu, self.gt), 0.0)

    def test_cohesionless_face_cannot_stand(self):
        self.assertLessEqual(hc.undercut_at_failure(1.0, 0.2, 0.2, 0.0, self.gt), 0.0)


class TestAdvance(unittest.TestCase):
    def test_zero_below_tau_c(self):
        tau = hc.face_stress(0.5, 0.1, 0.1)
        self.assertEqual(hc.advance_rate(0.5, 0.1, 0.1, 10e3, 19.5e3, 1e-5, tau + 1.0, cap=1.0), 0.0)

    def test_cap_when_face_unstable(self):
        self.assertEqual(hc.advance_rate(3.0, 0.3, 0.3, 1e3, 19.5e3, 1e-5, 0.1, cap=0.123), 0.123)

    def test_formula_when_stable(self):
        Hh, dc, cu, gt, kd, tc = 0.5, 0.1, 10e3, 19.5e3, 1e-5, 0.1
        Ev = hc.undercut_at_failure(Hh, dc, dc, cu, gt)
        expect = Hh / (2 * Ev) * kd * (hc.face_stress(Hh, dc, dc) - tc)
        self.assertAlmostEqual(hc.advance_rate(Hh, dc, dc, cu, gt, kd, tc, cap=1.0), min(expect, 1.0), places=14)


class TestStagedModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(CAL))
        import cases
        from lumped.model import LumpedBreach, params_from_case
        cls.runs = {}
        for cid in ("E1S1", "E2S2"):
            case = cases.load_case(cid)
            p, res, z_s0, notch, qin = params_from_case(case)
            eng = LumpedBreach(p, res, z_s0, notch, qin, p.dam.H)
            t_end = float(case["t_end"])
            dt = t_end / 5000.0
            hist = [eng.step(dt) for _ in range(5000)]
            cls.runs[cid] = (eng, hist)

    def test_stage2_starts_exactly_when_plunging(self):
        for cid, (eng, hist) in self.runs.items():
            prev = 1
            for o in hist:
                st = o.get("stage")
                if st is None:
                    break
                if prev == 1 and st == 2:
                    # 'stage' in the output is the state at the start of the step; the switch happened
                    # in the previous step, whose flow was plunging
                    self.assertTrue(last["plunging"], cid)
                if st == 1 and "Hh" in o and o["Hh"] > o["dc"] and o["Qb"] > 0:
                    self.assertTrue(o["plunging"], cid)
                prev, last = st, o

    def test_stages_and_water_balance(self):
        for cid, (eng, _) in self.runs.items():
            self.assertGreaterEqual(eng.max_stage, 3, cid)          # the headcut reaches the control
            self.assertLess(eng.s.z_b, 0.5 * eng.z_b0, cid)         # and the control is lowered
            self.assertLess(abs(eng.water_balance_error()) / eng.V0, 1e-9, cid)
        self.assertEqual(self.runs["E2S2"][0].max_stage, 4)         # residual block slides -> stage 4

    def test_off_switch_gives_surface_model(self):
        import cases
        from lumped.model import run_case
        r = run_case(cases.load_case("E1S1"), headcut="off", dt=7200.0 / 2000)
        self.assertEqual(r["max_stage"], 0)


if __name__ == "__main__":
    unittest.main()
