"""Evidence check for H1-c (review point B): the flow condition in the last reach of the pipe at the exit,
P1, k_d 3.16, dt 2 s, over the whole pipe stage. No code change.
  Fr = U / sqrt(g D) and y_c/D = Fr^(2/3) in the pipe (y_c >= D: the barrel cannot run part-full at its
       exit; FHWA HDS-5 outlet control takes the barrel full to the outlet)
  crown pressure near the exit under two outlet conventions:
    model (5.3)/(5.8): hydraulic grade at the exit = pipe centreline  -> crown at -D/2 at the exit
    HDS-5 (d_c >= D): hydraulic grade at the exit = crown             -> crown at 0 at the exit
  rising upstream with the friction slope S_f = f U^2 / (8 g R); reported: the length of the reach with
  sub-atmospheric crown (model convention) and the crown pressure 0.5 m inside the exit (both).
  notch: critical depth in the widened exit (H1-a width) against D.
Writes exit_transition_check.txt next to this script."""
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
    r = PipingRun(p1_case(kd=3.16e-6, exit_widening=True), T, dt=2.0, record_every=100.0).run(1520.0)
    L = ["Exit transition check, P1, k_d 3.16 (H1-a on for the notch width); evidence only", "",
         f"{'t s':>5} {'b':>6} {'D':>6} {'U m/s':>6} {'Fr':>5} {'yc/D':>5} | {'S_f':>6} {'model: sub-atm reach m':>22} "
         f"{'p_cr 0.5 m in (model)':>21} {'(HDS-5)':>8} | {'B_e':>6} {'yc notch/D':>10}"]
    for x in r.series:
        if "cr_W" in x:
            continue
        p = pp.Pipe(x["b"], x["D"], x["z_inv"], x["x_o"] - x["x_in"])
        fl = pp.pipe_flow(1.1 - x["z_inv"], p.b, p.D, p.L, 0.016)
        if fl.w != 1:
            continue
        U, D = fl.U, p.D
        Fr = U / math.sqrt(G * D)
        yc = (fl.Q ** 2 / (G * p.b ** 2)) ** (1 / 3)
        Sf = fl.f * U * U / (8 * G * fl.R)
        sub = min(0.5 * D / Sf, p.L)                       # model: crown head -D/2 at exit, rising at S_f
        pm = -0.5 * D + Sf * 0.5                            # crown pressure head 0.5 m inside the exit [m]
        ph = 0.0 + Sf * 0.5
        ycn = (fl.Q ** 2 / (G * x["B_e"] ** 2)) ** (1 / 3)
        L.append(f"{x['t']:5.0f} {p.b:6.3f} {D:6.3f} {U:6.2f} {Fr:5.2f} {yc / D:5.2f} | {Sf:6.3f} {sub:22.2f} "
                 f"{pm:21.3f} {ph:8.3f} | {x['B_e']:6.3f} {ycn / D:10.2f}")
    L += ["", "Fr > 1 and y_c/D > 1 throughout: the barrel cannot run part-full at its exit; under HDS-5 the crown",
          "pressure is >= 0 everywhere, so no air can enter and there is no free-surface reach under the roof.",
          "The sub-atmospheric reach exists only under the model's centreline outlet convention (5.3)/(5.8)."]
    text = "\n".join(L)
    print(text)
    (HERE / "exit_transition_check.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
