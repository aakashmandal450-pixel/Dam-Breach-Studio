"""Note H-1 pre-screen (not an adopted mechanism): exit-notch side walls retreat at the face-flow erosion rate,
dB_e/dt = 2 k_d (tau_e - tau_c), tau_e from Manning normal flow of the outlet discharge in width B_e on the
downstream face (as 5.6 stage 1; same k_d, tau_c, n). One-way only: the pipe flow is taken from the existing
P1 run without feedback. Reports the exit width against the pipe width at roof collapse across the 5.4a band.
Writes h1_widening_prescreen.txt next to this script."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lumped import hydraulics as hy, piping as pp                # noqa: E402
from lumped.piping_run import PipingRun                           # noqa: E402
from lumped.stability_table import StabilityTable                 # noqa: E402
from lumped.tests.test_piping_run import p1_case                  # noqa: E402

S, N = 1 / 3.0, 0.016


def tau_face(Q, B):
    y = hy.normal_depth(Q, B, 0.0, N, S)
    A = B * y
    return hy.manning_shear(Q, A, A / (B + 2 * y), N), y


def main():
    T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    L = ["H-1 pre-screen: exit-notch widening at the face-flow rate (one-way, no feedback), P1, dt 2 s", ""]
    for kd in (16.5, 6.77, 3.16, 1.48, 0.88):
        r = PipingRun(p1_case(kd=kd * 1e-6), T, dt=2.0, record_every=2.0).run(8000)
        ser = [x for x in r.series if "cr_W" not in x]
        B = ser[0]["b"]
        for i in range(1, len(ser)):
            x = ser[i - 1]
            dt = ser[i]["t"] - x["t"]
            p = pp.Pipe(x["b"], x["D"], x["z_inv"], x["x_o"] - x["x_in"])
            Q = pp.pipe_flow(1.1 - x["z_inv"], p.b, p.D, p.L, N).Q
            B = max(B, x["b"])
            tau, _ = tau_face(Q, B)
            B += 2 * kd * 1e-6 * max(tau, 0.0) * dt
        x = ser[-1]
        p = pp.Pipe(x["b"], x["D"], x["z_inv"], x["x_o"] - x["x_in"])
        Q = pp.pipe_flow(1.1 - x["z_inv"], p.b, p.D, p.L, N).Q
        tau, y = tau_face(Q, B)
        L.append(f"k_d {kd:5.2f}: roof collapse t {x['t']:6.0f} s | pipe b {x['b']:.3f} m | exit B_e {B:.3f} m | "
                 f"B_e/b {B / x['b']:.2f} | exit flow depth {y:.3f} m (crown {x['z_inv'] + x['D']:.3f}) | tau_e {tau:.0f} Pa")
    text = "\n".join(L)
    print(text)
    (HERE / "h1_widening_prescreen.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
