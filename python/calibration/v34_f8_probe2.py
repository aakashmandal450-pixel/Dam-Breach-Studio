"""V3.4 F8 probe 2: does bank collapse (F4 collapse_to_repose / F5 bank_wedge) flatten the headcut
face faster than the headcut rule can steepen it?

Probe 1 showed the F7 volume retreat is exact and face-preserving on every grid when it runs ALONE.
But the coupled Laurel Run diagnostic shows the scarp slope never exceeding ~0.6 and the headcut
almost never active. So something else is flattening the face in the full model.

Suspect: the collapse rule. F4 (collapse_to_repose) relaxes any face steeper than the material's
repose/Culmann angle. Laurel Run tan_phi = 0.55, Castlewood tan_phi = 0.9 -- both BELOW the
headcut's 1.0 (45 deg) detection threshold. If collapse flattens the face to the repose angle every
step, the headcut detector can never see a >= 1.0 face again, and the headcut starves.

Setup: identical vertical scarp to probe 1. Three configurations, same grid sweep:
  (a) headcut only                      -- the probe 1 baseline
  (b) headcut + collapse (to repose)    -- F4 on
  (c) collapse only                     -- how fast collapse alone flattens the face
We print the steepest cumulative slope in the profile over time. If (b) decays to near the repose
slope while (a) stays >= 1.0, the collapse rule is confirmed as the cause.

Usage (from the python folder):  python -u calibration\\v34_f8_probe2.py
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
H = float(__import__('os').environ.get('PROBE_H', '3.0'))
FACE_SLOPE = 1.0
T_END = 200.0
DT = 0.64
GRIDS = (12.8 / 6, 12.8 / 9, 12.8 / 12)

# Laurel Run material (cohesive, the case that collapses to Qp ~ 0.2)
TAN_PHI = 0.55
COHESION = 25.0e3
POROSITY = 0.35


def steepest_cumulative(z_line, ds):
    z = np.asarray(z_line, dtype=float)
    n = z.size
    best = 0.0
    for a in range(n - 1):
        for b in range(a + 1, n):
            drop = z[a] - z[b]
            if drop > 0:
                s = drop / ((b - a) * ds)
                if s > best:
                    best = s
    return best


def build(dx, collapse, headcut):
    L, x0 = 120.0, 90.0  # x0 = face location
    n = int(round(L / dx))
    x = (np.arange(n) + 0.5) * dx
    z = np.where(x < x0, H, 0.0)
    m = eng.create_prism_mesh(L, 3 * dx, n, 3, np.tile(z[:, None], (1, 3)), 0.0, z_floor=-1.0)
    cfg = eng.EngineConfig(
        h_dry=1e-3, headcut_mode="scarp", headcut_C=C_H,
        headcut_seg_slope=0.1, headcut_min_slope=0.5, headcut_min_height=0.0,
        headcut_overfall="free", headcut_face_slope=FACE_SLOPE,
        headcut_enabled=headcut,
        bank_collapse_enabled=collapse,
        collapse_to_repose=True,          # F4
        collapse_mode="bank_wedge",       # F5
    )
    mat = eng.MaterialProps(porosity=POROSITY, phi=np.degrees(np.arctan(TAN_PHI)),
                            cohesion=COHESION, material_class="cohesive")
    return m, cfg, mat, n


def run(dx, collapse, headcut, label):
    m, cfg, mat, n = build(dx, collapse, headcut)
    hc = eng.Headcut(cfg, mat)
    bank = eng.BankStability(mat, cfg)
    qx, qy = np.full((n, 3), Q), np.zeros((n, 3))

    out = []
    t, vol, col = 0.0, 0.0, 0.0
    report_at = [0.0, 12.8, 25.6, 51.2, 102.4, 200.0]
    ri = 0
    while t < T_END + 1e-9:
        if ri < len(report_at) and t >= report_at[ri] - 1e-9:
            out.append((t, steepest_cumulative(m.z_b[:, 1], dx), vol / (3 * dx), col))
            ri += 1
        m.h = np.where(m.z_b < 1e-9, TAIL, 0.05)
        if headcut:
            vol += hc.migrate(m, qx, DT, qy=qy)
        if collapse:
            col += bank.check_and_collapse(m)
        t += DT

    print(f"\n  --- {label} ---")
    print(f"  {'t[s]':>7}  {'steepest':>9}  {'hc vol[m2/m]':>12}  {'collapsed[m3]':>13}")
    for t, s, v, c in out:
        print(f"  {t:7.1f}  {s:9.3f}  {v:12.4f}  {c:13.3f}", flush=True)
    zl = m.z_b[:, 1]
    nz = np.where(zl < H - 1e-9)[0]
    i0 = max(0, (int(nz.min()) - 2) if nz.size else 0)
    print(f"  bed[{i0}:{i0 + 14}] = " + " ".join(f"{v:.2f}" for v in zl[i0:i0 + 14]))
    return out[-1][1] if out else float("nan")


def main():
    print(__doc__.split("Usage")[0].strip())
    R = C_H * (Q * H) ** (1.0 / 3.0)
    print(f"\nrepose slope (tan_phi) = {TAN_PHI}   headcut detect threshold = {FACE_SLOPE}"
          f"   R_exact = {R:.5f} m/s   exact hc vol @200s = {R * T_END * H:.3f} m2/m")
    for dx in GRIDS:
        print(f"\n{'=' * 78}\n  dx = {dx:.4f} m   n = {int(round(120.0 / dx))}\n{'=' * 78}")
        a = run(dx, collapse=False, headcut=True, label="(a) headcut only")
        b = run(dx, collapse=True, headcut=True, label="(b) headcut + collapse (F4/F5)")
        c = run(dx, collapse=True, headcut=False, label="(c) collapse only")
        print(f"\n  >> dx={dx:.3f}: final steepest slope  (a) {a:.3f}   (b) {b:.3f}   (c) {c:.3f}"
              f"   [detect needs >= {FACE_SLOPE}]")


if __name__ == "__main__":
    main()
