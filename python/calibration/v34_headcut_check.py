"""V3.4 headcut check (diagnostic): does the scarp headcut rule (C1, with F2) depend on the cell size?

One scarp of height H on a flat bed, a steady unit discharge q over it and a shallow tailwater at its foot. Only the
headcut rule acts (no flow solver, no other erosion), for 600 s in morph steps of 0.64 s. The law says the face
retreats at R = C (q H)^(1/3) for as long as the overfall lasts, so after 600 s it has moved R x 600 s and the
eroded volume per metre width is R x 600 s x H, on any grid.
Prints the retreat, the eroded volume and the time at which the rule stopped acting, for cells of 2.13 / 1.42 / 1.07 /
0.5 / 0.25 m, a vertical face and a 1:1 face, H = 0.5 / 1 / 3 m. Takes about a minute.

Usage (from the python folder):  python -u calibration\\v34_headcut_check.py --desktop <folder>
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import breach_engine_2d_v3_2 as eng  # noqa: E402

C_H, Q, T_END, DT, TAIL = 0.05, 2.0, 600.0, 0.64, 0.2
GRIDS = (12.8 / 6, 12.8 / 9, 12.8 / 12, 0.5, 0.25)


def run(dx, H, face_len, L=120.0, x0=90.0):
    n = int(round(L / dx))
    x = (np.arange(n) + 0.5) * dx
    z = np.where(x < x0, H, 0.0) if face_len <= 0 else np.clip((x0 + face_len - x) / face_len, 0.0, 1.0) * H
    m = eng.create_prism_mesh(L, 3 * dx, n, 3, np.tile(z[:, None], (1, 3)), 0.0, z_floor=-1.0)
    cfg = eng.EngineConfig(h_dry=1e-3, headcut_mode="scarp", headcut_C=C_H, headcut_seg_slope=0.1,
                           headcut_min_slope=0.5, headcut_overfall="free")
    hc = eng.Headcut(cfg, eng.MaterialProps(porosity=0.35))
    qx, qy = np.full((n, 3), Q), np.zeros((n, 3))

    def x_half():                                   # where the bed crosses half the scarp height
        zz = m.z_b[:, 1]
        k = np.where(zz < 0.5 * H)[0]
        if k.size == 0 or k.min() == 0:
            return float("nan")
        k = int(k.min())
        return float(x[k - 1] + (zz[k - 1] - 0.5 * H) / (zz[k - 1] - zz[k]) * dx)

    x_start, t, vol, t_stop = x_half(), 0.0, 0.0, None
    while t < T_END:
        m.h = np.where(m.z_b < 1e-9, TAIL, 0.05)    # thin flow over the scarp, tailwater on the lower bed
        v = hc.migrate(m, qx, DT, qy=qy)
        t += DT
        vol += v
        if v == 0.0 and t_stop is None:
            t_stop = t
        elif v > 0.0:
            t_stop = None
    return x_start - x_half(), vol / (3 * dx), t_stop


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desktop", default=None)
    a = ap.parse_args()
    rows = [f"V3.4 headcut check: scarp rule alone, q = {Q} m2/s, C = {C_H}, 600 s, thresholds 0.1 / 0.5, overfall 'free'",
            "H[m]  face       cell[m]   retreat[m]   exact[m]   volume[m3/m]   exact[m3/m]   rule stopped at[s]"]
    for H in (0.5, 1.0, 3.0):
        R = C_H * (Q * H) ** (1.0 / 3.0)
        for face, name in ((0.0, "vertical"), (H, "1:1")):
            for dx in GRIDS:
                ret, vol, ts = run(dx, H, face)
                rows.append(f"{H:4.1f}  {name:9s} {dx:8.2f} {ret:12.2f} {R * T_END:10.1f} {vol:14.2f} {R * T_END * H:13.1f}   "
                            f"{'did not stop' if ts is None else f'{ts:.0f}'}")
                print(rows[-1], flush=True)
    text = "\n".join(rows)
    print("\n" + text, flush=True)
    if a.desktop:
        Path(a.desktop, f"v34_headcut_check_{time.strftime('%Y%m%d_%H%M')}.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
