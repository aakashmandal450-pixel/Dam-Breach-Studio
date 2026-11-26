"""Outlet-convention review (note O-1), documentation only: the model's free-discharge outlet head
(5.3), h_o = max(y/2, h_t) above the invert, against the FHWA HDS-5 outlet-control form
h_o = max(TW, (d_c + D)/2) with d_c capped at D, along the P1 pipe stage (k_d 3.16). Reports h_o under
both, the outlet-control discharge ratio Q_HDS5/Q_model at the same geometry (no re-run: the frozen
baseline is not changed), and the crown pressure head at the exit. TW = 0 (free outfall on the face).
Writes outlet_convention_check.txt next to this script."""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lumped import piping as pp                                 # noqa: E402
from lumped.piping_run import PipingRun                          # noqa: E402
from lumped.stability_table import StabilityTable                # noqa: E402
from lumped.tests.test_piping_run import p1_case                 # noqa: E402

G = 9.81


def main():
    T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    r = PipingRun(p1_case(kd=3.16e-6), T, dt=2.0, record_every=100.0).run(1520.0)
    L = ["Outlet convention, P1 (k_d 3.16), TW = 0; heads in m above the pipe invert", "",
         f"{'t s':>5} {'D':>6} {'HW':>6} {'d_c':>6} | {'h_o model':>9} {'h_o HDS-5':>9} | {'Q_o model':>9} {'Q_o HDS-5':>9} "
         f"{'ratio':>6} {'ctrl':>6} | {'crown p exit: model':>19} {'HDS-5':>6}"]
    for x in r.series:
        if "cr_W" in x:
            continue
        b, D, zi = x["b"], x["D"], x["z_inv"]
        L_p = x["x_o"] - x["x_in"]
        HW = 1.1 - zi
        fl = pp.pipe_flow(HW, b, D, L_p, 0.016)
        y, w, A, P, R = pp.section(b, D, HW)
        dc = min((fl.Q ** 2 / (G * b * b)) ** (1 / 3), D)
        ho_m, ho_h = max(0.5 * y, 0.0), max(0.0, 0.5 * (dc + D))
        F = pp.darcy_f(0.016, R) * L_p / (4 * R)
        k = pp.K_U + pp.K_D + F
        Qm = A * math.sqrt(2 * G * max(HW - ho_m, 0) / k)
        Qh = A * math.sqrt(2 * G * max(HW - ho_h, 0) / k)
        L.append(f"{x['t']:5.0f} {D:6.3f} {HW:6.3f} {dc:6.3f} | {ho_m:9.3f} {ho_h:9.3f} | {Qm * 1e3:9.2f} {Qh * 1e3:9.2f} "
                 f"{Qh / Qm:6.3f} {fl.control:>6} | {ho_m - D:19.3f} {ho_h - D:6.3f}")
    text = "\n".join(L)
    print(text)
    (HERE / "outlet_convention_check.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
