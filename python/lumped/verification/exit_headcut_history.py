"""Review check (2026-11-26) of the existing exit headcut (5.6) on P1: per-step H_h = z_inv - z_h, d_c,
tau_s (face flow), tau_hf (headcut face), E_r, dX/dt and stage, from the inputs the driver actually
passes to exit_headcut.step (the outlet discharge of the pipe, or of the crater once it exists).
k_d 3.16 (central, 5.4a), dt 2 s, every other input as in the P1 band. Diagnostic only: no code change.
Writes exit_headcut_history.txt next to this script."""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lumped import exit_headcut as xh, headcut as hc, sediment as sd     # noqa: E402
from lumped import piping_run as prm                                      # noqa: E402
from lumped.tests.test_piping_run import p1_case, TABLE                    # noqa: E402
from lumped.stability_table import StabilityTable                         # noqa: E402

ROWS, _step = [], xh.step
NOW = [0.0]
_adv = prm.PipingRun.advance


def adv(self, s, dt):
    NOW[0] = s.t
    return _adv(self, s, dt)


def logged(h, dam, Q, b, z_inv, z_cr, x_o, dt, kd, tau_c, c_u, gamma_t, n, C_h=1.0):
    dc = hc.critical_depth_unit(Q / b) if b > 0 else 0.0
    Hh = max(z_inv - h.z_h, 0.0)
    _, tau_s = xh._rect_flow(Q, b, 1.0 / dam.zd, n) if Q > 0 else (0, 0.0)
    _, tau_cap = xh._rect_flow(Q, b, 2.0, n) if Q > 0 else (0, 0.0)
    tau_hf = hc.face_stress(Hh, dc, dc)
    Er = sd.cohesive_rate(tau_s, tau_c, kd)
    dX = hc.advance_rate(Hh, dc, dc, c_u, gamma_t, kd, tau_c, sd.cohesive_rate(tau_cap, tau_c, kd)) if Hh > dc else 0.0
    new, xo = _step(h, dam, Q, b, z_inv, z_cr, x_o, dt, kd, tau_c, c_u, gamma_t, n, C_h)
    ROWS.append((NOW[0], Q, b, z_inv, h.z_h, Hh, dc, tau_s, tau_hf, Er, dX, new.stage, new.z_h, x_o, xo))
    return new, xo


def main():
    prm.xh.step = logged
    prm.PipingRun.advance = adv
    T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    r = prm.PipingRun(p1_case(kd=3.16e-6, exit_headcut=True), T, dt=2.0).run(2000.0)
    rows = []
    for rw in ROWS:                                   # one row per time (event location repeats steps)
        if not rows or rw[0] > rows[-1][0]:
            rows.append(rw)
        else:
            rows[-1] = rw
    L = ["P1 exit headcut (5.6) time history, k_d 3.16, dt 2 s; inputs as passed by the driver", "",
         f"{'t s':>6} {'Q L/s':>7} {'b':>6} {'z_inv':>6} {'z_h':>6} {'H_h':>6} {'d_c':>6} {'tau_s':>6} "
         f"{'tau_hf':>6} {'E_r mm/min':>10} {'dX/dt':>7} {'stage':>5}"]
    flowing = [rw for rw in rows if rw[1] > 0.0]
    marks = sorted({rw[0] for rw in flowing[::max(1, len(flowing) // 16)]} | {flowing[-1][0]})
    for rw in rows:
        if rw[0] in marks:
            t, Q, b, zi, zh, Hh, dc, ts, thf, Er, dX, st, zh1, xo0, xo1 = rw
            L.append(f"{t:6.0f} {Q * 1e3:7.2f} {b:6.3f} {zi:6.3f} {zh:6.3f} {Hh:6.3f} {dc:6.3f} {ts:6.1f} {thf:6.1f} "
                     f"{Er * 6e4:10.2f} {dX:7.4f} {st:5d}")
    bed0 = next((rw[0] for rw in rows if rw[12] <= 0.0), None)
    mx = max(flowing, key=lambda rw: rw[5] - rw[6])
    stop_q = next((rw[0] for rw in rows if rw[0] > flowing[0][0] and rw[1] == 0.0), None)
    L += ["", f"headcut bed reaches the dam base (z_h = 0) at t = {bed0:.0f} s; outflow stops (crater blocked) at t = "
          f"{stop_q:.0f} s" if stop_q else "",
          f"with flow: largest H_h - d_c = {mx[5] - mx[6]:+.4f} m at t = {mx[0]:.0f} s (H_h {mx[5]:.4f}, d_c {mx[6]:.4f})",
          f"time steps with flow and H_h > d_c (plunging): {sum(1 for rw in flowing if rw[5] > rw[6])} of {len(flowing)}",
          f"outlet moves: {sum(1 for rw in rows if rw[14] < rw[13])}; run outcome: {r.stopped}"]
    text = "\n".join(L)
    print(text)
    (HERE / "exit_headcut_history.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
