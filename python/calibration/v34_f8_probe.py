"""V3.4 F8 probe: does the F7 volume-based scarp retreat PRESERVE a steep face, or smear it flat?

This is the question that decides the F8 design. F8 as proposed assumes a concentrated near-vertical
step exists to be detected. The Laurel Run diagnostic shows the scarp slope never exceeds ~0.6, so
either (a) the face never steepens, or (b) the retreat rule flattens it.

Setup: one vertical scarp of height H on a flat bed, steady unit discharge q over it, shallow
tailwater at the foot. ONLY the headcut rule acts (no flow solver, no transport, no collapse) -- the
same isolation as v34_headcut_check.py, but driving the F7 volume path (headcut_face_slope set).

For each grid we print, over time: the bed profile's steepest cumulative slope anywhere, the scarp
height, and how many cells the face spans. If the retreat preserves the face, the steepest slope
stays high (near vertical). If it smears, the slope decays toward zero.

Usage (from the python folder):  python -u calibration\\v34_f8_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import breach_engine_2d_v3_2 as eng  # noqa: E402

C_H = 0.05
Q = 2.0
TAIL = 0.2
H = 3.0
FACE_SLOPE = 1.0
SEG_SLOPE = 0.1
T_END = 400.0
DT = 0.64
GRIDS = (12.8 / 6, 12.8 / 9, 12.8 / 12, 0.5)


def steepest_cumulative(z_line: float, ds: float):
    """Max cumulative slope (drop / horizontal length) over any contiguous window, and its span.

    This is exactly the quantity F8's cumulative detector would test. Returns
    (max_slope, n_cells_of_that_window, height_of_that_window).
    """
    z = np.asarray(z_line, dtype=float)
    n = z.size
    best = (0.0, 0, 0.0)
    for a in range(n - 1):
        for b in range(a + 1, n):
            drop = z[a] - z[b]
            if drop <= 0:
                continue
            slope = drop / ((b - a) * ds)
            if slope > best[0]:
                best = (slope, b - a, drop)
    return best


def face_profile(z_line, ds):
    """Report the face: where the bed falls from crest to base, and its overall slope."""
    z = np.asarray(z_line, dtype=float)
    zc, zb = float(z.max()), float(z.min())
    if zc - zb < 1e-9:
        return 0.0, 0, 0.0
    # first cell at (near) crest, first cell at (near) base
    hi = int(np.argmax(z >= zc - 1e-9))
    lo = int(np.argmax(z <= zb + 1e-9))
    if lo <= hi:
        return 0.0, 0, 0.0
    span = lo - hi
    return (zc - zb) / (span * ds), span, zc - zb


def run(dx):
    L, x0 = 120.0, 90.0
    n = int(round(L / dx))
    x = (np.arange(n) + 0.5) * dx
    z = np.where(x < x0, H, 0.0)  # vertical face at x0
    m = eng.create_prism_mesh(L, 3 * dx, n, 3, np.tile(z[:, None], (1, 3)), 0.0, z_floor=-1.0)
    cfg = eng.EngineConfig(h_dry=1e-3, headcut_mode="scarp", headcut_C=C_H,
                           headcut_seg_slope=SEG_SLOPE, headcut_min_slope=0.5,
                           headcut_min_height=0.0, headcut_overfall="free",
                           headcut_face_slope=FACE_SLOPE)
    hc = eng.Headcut(cfg, eng.MaterialProps(porosity=0.35))
    qx, qy = np.full((n, 3), Q), np.zeros((n, 3))

    R = C_H * (Q * H) ** (1.0 / 3.0)
    print(f"\n{'=' * 78}")
    print(f"  dx = {dx:.4f} m   n = {n}   H = {H} m   vertical face   R_exact = {R:.5f} m/s")
    print(f"{'=' * 78}")
    print(f"  {'t[s]':>7}  {'vol[m2/m]':>10}  {'steepest':>9} {'span':>5} {'Hwin':>6}   "
          f"{'faceslope':>9} {'span':>5} {'Hface':>6}")

    t, vol = 0.0, 0.0
    report_at = [0.0, 25.0, 50.0, 100.0, 200.0, 300.0, 400.0]
    ri = 0
    while t < T_END + 1e-9:
        if ri < len(report_at) and t >= report_at[ri] - 1e-9:
            zl = m.z_b[:, 1]
            smax, sspan, shgt = steepest_cumulative(zl, dx)
            fsl, fspan, fhgt = face_profile(zl, dx)
            print(f"  {t:7.1f}  {vol / (3 * dx):10.4f}  {smax:9.3f} {sspan:5d} {shgt:6.2f}   "
                  f"{fsl:9.3f} {fspan:5d} {fhgt:6.2f}", flush=True)
            ri += 1
        m.h = np.where(m.z_b < 1e-9, TAIL, 0.05)
        vol += hc.migrate(m, qx, DT, qy=qy)
        t += DT

    zl = m.z_b[:, 1]
    # show the actual bed shape around the face so smearing is visible
    nz = np.where(zl < H - 1e-9)[0]
    i0 = max(0, (int(nz.min()) - 3) if nz.size else 0)
    i1 = min(len(zl), i0 + 16)
    print(f"  bed[{i0}:{i1}] = " + " ".join(f"{v:.2f}" for v in zl[i0:i1]))
    print(f"  exact volume after {T_END:.0f} s = {R * T_END * H:.4f} m2/m")
    return vol / (3 * dx)


def main():
    print(__doc__.split("Usage")[0].strip())
    for dx in GRIDS:
        run(dx)


if __name__ == "__main__":
    main()
