"""V3.4 checks (engine findings 2026-11-10, ENGINE_FINDINGS_2026-11-10.md).

F1: hydrostatic reconstruction of Chen & Noelle (2017), cfg.hydrostatic_reconstruction = "chen_noelle".
    - steady normal flow down a 1:2.2 plane: velocity within 15 % of the exact normal flow on a coarse (6 m step per
      cell) and a fine (0.45 m step) grid, and nearly the same on both (the Audusse scheme gives 25 % and 52 %);
    - lake at rest over a rough bed with steps, dry islands, random dry cells and a perched puddle stays at rest
      (machine precision);
    - a bore running up and down a beach: no negative depth, no NaN, mass conserved to 1e-12;
    - the default ("audusse") reproduces V3.3 bit for bit on the beach test;
    - bad option values and spatial order 2 are rejected.
F2: headcut only at a free overfall, cfg.headcut_overfall = "free" (scarp mode):
    - a free scarp (+x, -x, +y) erodes exactly as with "any" (V3.3); a scarp drowned 0.5 m above its top does not;
    - switch at the scarp top (tailwater 1 cm below: active, 1 cm above: inactive);
    - Numba kernel equal to the NumPy reference on 40 random beds; bad options rejected.
Runs with NumPy (python tests/v3_4_tests.py) and Numba (python tests/run_with_fast.py tests/v3_4_tests.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import breach_engine_2d_v3_2 as eng  # noqa: E402

N_PASS = N_ALL = 0


def check(name, ok, info=""):
    global N_PASS, N_ALL
    N_ALL += 1
    N_PASS += bool(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {info}", flush=True)


# ---------------------------------------------------------------------------------------------------------------------
# F1.1 normal flow on a steep plane
# ---------------------------------------------------------------------------------------------------------------------
S_PLANE, N_PLANE = 0.45, 0.04


def plane(mode, dx, t_end=600.0):
    L, ny = 180.0, 3
    nx = int(L / dx)
    x = (np.arange(nx) + 0.5) * dx
    zb = np.tile((L - x)[:, None] * S_PLANE, (1, ny))
    m = eng.create_prism_mesh(L, ny * dx, nx, ny, zb.copy(), 0.0)
    cfg = eng.EngineConfig(h_dry=1e-3, friction_model="manning", manning_n=N_PLANE, downstream_boundary="outfall",
                           hydrostatic_reconstruction=mode)
    hyd = eng.Hydrodynamics(cfg)
    t = 0.0
    while t < t_end:
        t += hyd.step(m, zb[0, 0] + 0.25, 1.0)[0]
    i = int(0.6 * nx)
    h, u = m.h[i, 1], m.u[i, 1]
    hn = (h * u * N_PLANE / np.sqrt(S_PLANE)) ** 0.6
    return u / (h * u / hn)          # model velocity / exact normal-flow velocity at the same unit discharge


r_cn_c, r_cn_f = plane("chen_noelle", 13.33), plane("chen_noelle", 1.0)
r_au_c = plane("audusse", 13.33)
check("F1 plane, coarse grid (6 m step/cell): Chen-Noelle velocity within 15 % of exact", abs(r_cn_c - 1) <= 0.15,
      f"{r_cn_c * 100:.0f} % (Audusse {r_au_c * 100:.0f} %)")
check("F1 plane, fine grid (0.45 m step/cell): Chen-Noelle velocity within 15 % of exact", abs(r_cn_f - 1) <= 0.15,
      f"{r_cn_f * 100:.0f} %")
check("F1 plane: Chen-Noelle coarse and fine grid within 10 % of each other", abs(r_cn_c / r_cn_f - 1) <= 0.10,
      f"{r_cn_c / r_cn_f:.3f}")
check("F1 plane: Audusse defect present (documents V3.3): coarse-grid velocity < 40 % of exact", r_au_c < 0.40,
      f"{r_au_c * 100:.0f} %")

# ---------------------------------------------------------------------------------------------------------------------
# F1.2 lake at rest
# ---------------------------------------------------------------------------------------------------------------------
rng = np.random.default_rng(3)
nx, ny = 30, 20
zb = rng.uniform(0, 0.9, (nx, ny))
zb[10:, :] += 0.6
zb[20:, :] += 0.8
zb[3:6, 3:6] = 2.0
zb[rng.random((nx, ny)) < 0.08] = 1.7
for mode in ("audusse", "chen_noelle"):
    m = eng.create_prism_mesh(30.0, 20.0, nx, ny, zb.copy(), 1.0)
    m.z_b[24:29, 12:17] = 2.4
    m.z_b[25:28, 13:16] = 2.0
    m.h[25:28, 13:16] = 0.2
    cfg = eng.EngineConfig(h_dry=1e-3, manning_n=0.03, friction_model="manning", downstream_boundary="wall",
                           hydrostatic_reconstruction=mode)
    hyd = eng.Hydrodynamics(cfg)
    V0 = m.h.sum()
    for _ in range(2000):
        hyd.step(m, 1.0, 0.5)
    wet = (m.h > 1e-3) & (m.z_b < 1.0)
    vmax = max(abs(m.u).max(), abs(m.v).max())
    eerr = abs((m.h + m.z_b)[wet] - 1.0).max()
    perr = abs(m.h[25:28, 13:16] - 0.2).max()
    check(f"F1 lake at rest ({mode}): |u|,|v| < 1e-12, level error < 1e-12, puddle unchanged, volume unchanged",
          vmax < 1e-12 and eerr < 1e-12 and perr < 1e-12 and abs(m.h.sum() - V0) < 1e-9,
          f"{vmax:.1e} m/s, {eerr:.1e} m, {perr:.1e} m")

# ---------------------------------------------------------------------------------------------------------------------
# F1.3 run-up / run-down on a beach (moving wet-dry front)
# ---------------------------------------------------------------------------------------------------------------------
H_SUM_V33 = 379.952477037845      # beach test with the V3.3 engine (Audusse), NumPy and Numba, 2026-11-10


def beach(mode):
    nxb, nyb = 120, 6
    x = (np.arange(nxb) + 0.5) * 0.5
    zb_ = np.tile(np.where(x < 30, 0.0, (x - 30) * 0.3)[:, None], (1, nyb))
    m = eng.create_prism_mesh(60.0, 3.0, nxb, nyb, zb_.copy(), 1.0)
    m.h[:20] += 0.8
    cfg = eng.EngineConfig(h_dry=1e-3, manning_n=0.02, friction_model="manning", downstream_boundary="wall",
                           hydrostatic_reconstruction=mode)
    hyd = eng.Hydrodynamics(cfg)
    V0 = m.h.sum() * 0.25
    t = q_in = 0.0
    hmin = 0.0
    while t < 120:
        dt, ql, qr = hyd.step(m, 1.0, 0.5)
        t += dt
        q_in += ql * dt
        hmin = min(hmin, float(m.h.min()))
    return hmin, bool(np.isnan(m.h).any()), (m.h.sum() * 0.25 - V0 - q_in) / V0, float(m.h.sum())


for mode in ("audusse", "chen_noelle"):
    hmin, nan, merr, hs = beach(mode)
    check(f"F1 beach run-up ({mode}): depth >= 0, no NaN, mass error < 1e-12", hmin >= 0 and not nan and abs(merr) < 1e-12,
          f"min h {hmin:.1e}, mass {merr:.1e}")
    if mode == "audusse":
        check("F1 default (audusse) reproduces V3.3 on the beach test", abs(hs / H_SUM_V33 - 1) < 1e-12,
              f"h sum {hs:.12f} vs {H_SUM_V33:.12f}")

# ---------------------------------------------------------------------------------------------------------------------
# F1.4 options
# ---------------------------------------------------------------------------------------------------------------------
m = eng.create_prism_mesh(10.0, 3.0, 10, 3, np.zeros((10, 3)), 0.5)
for bad, label in ((dict(hydrostatic_reconstruction="xyz"), "bad name"),
                   (dict(hydrostatic_reconstruction="chen_noelle", spatial_order=2), "spatial order 2")):
    try:
        eng.Hydrodynamics(eng.EngineConfig(**bad)).step(m, 0.5, 0.1)
        check(f"F1 option rejected: {label}", False)
    except ValueError:
        check(f"F1 option rejected: {label}", True)

# ---------------------------------------------------------------------------------------------------------------------
# F2: headcut only at a free overfall (headcut_overfall = "free")
# ---------------------------------------------------------------------------------------------------------------------
H_SC = 0.3


def scarp(ds=0.1, tail=None, axis=0, reverse=False):
    """Flat top at H, 1:2 scarp, flat foot at 0. tail = water-surface level everywhere it is above the bed
    (None: a 2 cm film everywhere, i.e. a free overfall)."""
    n = int(round(6.0 / ds))
    x = (np.arange(n) + 0.5) * ds
    line = np.clip(H_SC - 0.5 * (x - 2.0), 0.0, H_SC)
    if reverse:
        line = line[::-1]
    zb = np.tile(line[:, None], (1, 4)) if axis == 0 else np.tile(line[None, :], (4, 1))
    m = eng.create_prism_mesh(zb.shape[0] * ds, zb.shape[1] * ds, zb.shape[0], zb.shape[1], zb.copy(), 0.0)
    m.h = np.full_like(zb, 0.02) if tail is None else np.maximum(tail - zb, 0.0)
    qq = np.full_like(zb, 0.05 * (-1.0 if reverse else 1.0))
    qx, qy = (qq, np.zeros_like(zb)) if axis == 0 else (np.zeros_like(zb), qq)
    return m, qx, qy


def hc_volume(m, qx, qy, overfall, steps=1):
    cfg = eng.EngineConfig(headcut_mode="scarp", headcut_min_slope=0.3, headcut_seg_slope=0.1, h_dry=1e-3,
                           headcut_overfall=overfall)     # sampled slope of the 1:2 scarp is just under 0.5
    hc = eng.Headcut(cfg, eng.MaterialProps(porosity=0.35))
    return sum(hc.migrate(m, qx, 0.5, qy=qy) for _ in range(steps))


for axis, rev in ((0, False), (0, True), (1, False)):
    lab = {(0, False): "+x", (0, True): "-x", (1, False): "+y"}[(axis, rev)]
    v_any = hc_volume(*scarp(axis=axis, reverse=rev), "any")
    v_free = hc_volume(*scarp(axis=axis, reverse=rev), "free")
    check(f"F2 free overfall ({lab}): 'free' erodes exactly as 'any' (V3.3)", v_free == v_any and v_any > 0,
          f"{v_free:.6g} vs {v_any:.6g} m3")
    v_any_d = hc_volume(*scarp(tail=H_SC + 0.5, axis=axis, reverse=rev), "any")
    v_free_d = hc_volume(*scarp(tail=H_SC + 0.5, axis=axis, reverse=rev), "free")
    check(f"F2 scarp drowned 0.5 m above its top ({lab}): 'any' erodes, 'free' does not",
          v_any_d > 0 and v_free_d == 0.0, f"any {v_any_d:.3g} m3, free {v_free_d:.3g} m3")
v_below = hc_volume(*scarp(tail=H_SC - 0.01), "free")
v_above = hc_volume(*scarp(tail=H_SC + 0.01), "free")
check("F2 switch: tailwater 1 cm below the scarp top -> active; 1 cm above -> inactive", v_below > 0 and v_above == 0.0,
      f"{v_below:.3g} / {v_above:.3g} m3")

# NumPy reference vs Numba kernel on random beds (only when the Numba morphology is active)
try:
    import fast_morph as FM
    fm_on = FM._ENABLED
except Exception:
    fm_on = False
if fm_on:
    import copy
    worst, nact = 0.0, 0
    for seed in range(40):
        r = np.random.default_rng(seed)
        nxr, nyr = 33, 27
        zr = np.cumsum(r.normal(0, 0.08, (nxr, nyr)), axis=0) * 0.3 + np.where(r.random((nxr, nyr)) < 0.1,
                                                                                 r.uniform(0, 0.6, (nxr, nyr)), 0)
        m0 = eng.create_prism_mesh(nxr * 0.1, nyr * 0.13, nxr, nyr, zr.copy(), 0.0)
        m0.h = np.where(r.random((nxr, nyr)) < 0.6, r.uniform(0.002, 0.5, (nxr, nyr)), 0.0)
        qx0, qy0 = r.normal(0, 0.05, (nxr, nyr)), r.normal(0, 0.05, (nxr, nyr))
        cfg = eng.EngineConfig(h_dry=1e-3, headcut_mode="scarp", headcut_C=0.3, headcut_seg_slope=0.1,
                               headcut_min_slope=0.2, headcut_overfall="free")
        hc = eng.Headcut(cfg, eng.MaterialProps(porosity=0.35))
        a, b = copy.deepcopy(m0), copy.deepcopy(m0)
        va = FM._ORIG["scarp"](hc, a, qx0, qy0, 0.7)
        vb = FM._fast_migrate_scarp(hc, b, qx0, qy0, 0.7)
        nact += va > 0
        worst = max(worst, float(np.max(np.abs(a.z_b - b.z_b))), abs(va - vb) / max(abs(va), 1e-30))
    check("F2 Numba kernel = NumPy reference ('free', 40 random beds)", worst < 1e-12 and nact >= 30,
          f"max diff {worst:.1e}, active in {nact}/40")

for bad, label in ((dict(headcut_mode="scarp", headcut_overfall="xyz"), "bad name"),
                   (dict(headcut_mode="cell", headcut_overfall="free"), "'free' with cell mode")):
    try:
        m, qx, qy = scarp()
        eng.Headcut(eng.EngineConfig(**bad), eng.MaterialProps()).migrate(m, qx, 0.5, qy=qy)
        check(f"F2 option rejected: {label}", False)
    except ValueError:
        check(f"F2 option rejected: {label}", True)

print(f"\nV3.4 checks: {N_PASS} of {N_ALL} passed")
sys.exit(0 if N_PASS == N_ALL else 1)
