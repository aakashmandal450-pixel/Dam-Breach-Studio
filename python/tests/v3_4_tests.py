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
F3: adaptation length without the dx floor, cfg.adaptation_dx_floor = False:
    - uniform flow over an erodible bed: pickup within 5 % at dx 1 m and 0.25 m (with the floor: x1.9), both
      adaptation-length modes; identical to the floor version where the floor is inactive.
F4: slope collapse to the repose angle every morph step, cfg.collapse_to_repose = True:
    - a 4 m vertical sand bank, one call: with 3 passes (V3.3) the collapse reaches less far at dx 0.25 m than at
      1 m; to repose the crest retreat is the same on both grids and equal to the exact value, no pair is steeper
      than tan(phi), volume is conserved;
    - independent of the safety cap when the cap is not reached; calls ending at the cap are counted;
    - off (default) = V3.3; Numba kernel equal to the NumPy reference; bad cap rejected.
F5: Culmann on whole banks with the wedge removed by volume, cfg.collapse_mode = "bank_wedge" (c > 0):
    - a vertical wall (c 25 kPa, tan phi 0.55) stands at 8.0 m and fails at 8.6 m at cells of 2.13 / 1.42 / 1.07 /
      0.5 m; at 9 m the fallen volume equals the Culmann wedge on every grid and the top retreats H / tan(alpha)
      within one cell; solids conserved (dry and wet toe); the four bank directions agree;
    - a 14 m bank spread over 2-4 cells fails as one bank; a bank flatter than phi and a low wall do not move;
    - sweeps: one wall settles in one sweep; a chain of two walls stops by itself with every bank at FS >= 1, in
      the same number of sweeps on finer grids; independent of the cap; cap hits counted;
    - c = 0 acts as "all_pairs"; bad mode rejected; with the Numba backend the result equals NumPy.
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

# ---------------------------------------------------------------------------------------------------------------------
# F3: adaptation length without the cell-size floor (adaptation_dx_floor = False)
# ---------------------------------------------------------------------------------------------------------------------
def pickup(dx, floor, mode="depth_scaled"):
    """Uniform 5 cm flow at 1.5 m/s over an erodible flat bed (D50 5 mm), one transport interval of 0.5 s:
    mean bed lowering [m]. 5 h = 0.25 m, so the dx floor is active for dx = 1 m."""
    n = int(round(8 / dx))
    zb_ = np.zeros((n, 3))
    m = eng.create_prism_mesh(8.0, 3 * dx, n, 3, zb_.copy(), 0.05)
    m.z_floor = zb_ - 1.0
    cfg = eng.EngineConfig(h_dry=1e-3, adaptation_length_mode=mode, adaptation_length=0.25, adaptation_dx_floor=floor)
    mo = eng.Morphology(cfg, eng.MaterialProps(material_class="noncohesive", D50=0.005, porosity=0.35, phi=33.0))
    z0 = m.z_b.copy()
    mo._transport_exner(m, m.h, np.full_like(zb_, 0.075), np.zeros_like(zb_), np.full_like(zb_, 20.0), 0.5)
    return float(np.mean(z0 - m.z_b))


for mode in ("depth_scaled", "fixed"):
    a1, a4 = pickup(1.0, True, mode), pickup(0.25, True, mode)
    b1, b4 = pickup(1.0, False, mode), pickup(0.25, False, mode)
    check(f"F3 ({mode}) with the dx floor (V3.3): pickup depends on dx (documents the defect)", a4 / a1 > 1.5,
          f"dx 1 / 0.25 m: {a1 * 1e6:.1f} / {a4 * 1e6:.1f} um")
    check(f"F3 ({mode}) without the floor: pickup within 5 % at dx 1 and 0.25 m", abs(b4 / b1 - 1) < 0.05,
          f"{b1 * 1e6:.1f} / {b4 * 1e6:.1f} um")
    check(f"F3 ({mode}): no floor = floor where the floor is inactive (dx 0.25 m <= Ls)", a4 == b4, f"{a4:.6e} / {b4:.6e}")

# ---------------------------------------------------------------------------------------------------------------------
# F4: slope collapse to the repose angle every morph step (collapse_to_repose = True)
# ---------------------------------------------------------------------------------------------------------------------
PHI_F4, H_BANK = 33.0, 4.0


def bank(dx, **opts):
    """A dry vertical bank 4 m high in sand (c = 0, phi 33 deg), 24 m long, one collapse call.
    Returns the mesh, the bank object and the bulk volume before the call."""
    n = int(round(24.0 / dx))
    x = (np.arange(n) + 0.5) * dx
    zb_ = np.tile(np.where(x < 12.0, H_BANK, 0.0)[:, None], (1, 3))
    m = eng.create_prism_mesh(24.0, 3 * dx, n, 3, zb_.copy(), 0.0)
    cfg = eng.EngineConfig(h_dry=1e-3, collapse_mode="all_pairs", **opts)
    bs = eng.BankStability(eng.MaterialProps(material_class="noncohesive", cohesion=0.0, phi=PHI_F4, porosity=0.35), cfg)
    v0 = float(np.sum(m.z_b)) * m.dx * m.dy
    bs.check_and_collapse(m)
    return m, bs, v0, x


def crest_retreat(m, x):
    """Distance from the original bank line (x = 12 m) to the point where the bed is still within 1 cm of the top."""
    z = m.z_b[:, 1]
    lowered = x[z < H_BANK - 0.01]
    return 12.0 - float(lowered.min()) if lowered.size else 0.0


tanphi = float(np.tan(np.deg2rad(PHI_F4)))
r3 = {dx: crest_retreat(*bank(dx)[0:4:3]) for dx in (1.0, 0.25)}
check("F4 3 passes per call (V3.3): the collapse reaches less far on a finer grid (documents the defect)",
      r3[1.0] > 2.5 * r3[0.25], f"crest retreat at dx 1 / 0.25 m: {r3[1.0]:.2f} / {r3[0.25]:.2f} m")
out = {dx: bank(dx, collapse_to_repose=True, collapse_max_passes=100000) for dx in (1.0, 0.25)}
rr = {dx: crest_retreat(o[0], o[3]) for dx, o in out.items()}
exact = 0.5 * H_BANK / tanphi            # a repose slope through the mid-height of the bank conserves volume
check("F4 to repose: crest retreat equal on both grids and to the exact value (within one coarse cell)",
      abs(rr[1.0] - rr[0.25]) <= 1.0 and all(abs(v - exact) <= 1.0 for v in rr.values()),
      f"dx 1 / 0.25 m: {rr[1.0]:.2f} / {rr[0.25]:.2f} m, exact {exact:.2f} m")
for dx, (m, bs, v0, x) in out.items():
    steep = float(np.max(np.abs(np.diff(m.z_b, axis=0)))) / dx
    check(f"F4 to repose (dx {dx} m): no pair steeper than tan(phi); volume conserved",
          steep <= tanphi + 2e-6 / dx and abs(float(np.sum(m.z_b)) * m.dx * m.dy - v0) < 1e-9 * v0,
          f"max slope {steep:.5f} vs {tanphi:.5f}; passes {bs.last_passes}")
ma = bank(0.25, collapse_to_repose=True, collapse_max_passes=100000)
mb = bank(0.25, collapse_to_repose=True, collapse_max_passes=200000)
check("F4 the result does not depend on the safety cap once the cap is not reached",
      np.array_equal(ma[0].z_b, mb[0].z_b) and ma[1].last_passes == mb[1].last_passes < 100000,
      f"passes {ma[1].last_passes}")
h0 = eng.BankStability.stats["limit_hits"]
bank(0.25, collapse_to_repose=True, collapse_max_passes=5)
h1 = eng.BankStability.stats["limit_hits"]
bank(1.0, collapse_to_repose=True, collapse_max_passes=100000)
check("F4 a call that ends at the cap is counted (limit_hits); one that settles is not",
      h1 == h0 + 1 and eng.BankStability.stats["limit_hits"] == h1, f"hits {h0} -> {h1}")
d3, dd = bank(0.25), bank(0.25, collapse_to_repose=False, collapse_max_passes=7)
m3 = bank(0.25, collapse_iterations=3)
check("F4 default (off) = V3.3: exactly collapse_iterations passes, the cap is ignored",
      np.array_equal(d3[0].z_b, dd[0].z_b) and np.array_equal(d3[0].z_b, m3[0].z_b) and d3[1].last_passes == 3,
      f"passes {d3[1].last_passes}")
try:
    bank(1.0, collapse_to_repose=True, collapse_max_passes=0)
    check("F4 option rejected: collapse_max_passes < 1", False)
except ValueError:
    check("F4 option rejected: collapse_max_passes < 1", True)
if fm_on:
    import copy
    worst, npass = 0.0, True
    for seed in range(20):
        r = np.random.default_rng(100 + seed)
        nxr, nyr = 29, 23
        zr = np.cumsum(r.normal(0, 0.3, (nxr, nyr)), axis=0) + np.where(r.random((nxr, nyr)) < 0.1, 1.5, 0.0)
        m0 = eng.create_prism_mesh(nxr * 0.2, nyr * 0.25, nxr, nyr, zr.copy(), 0.0)
        m0.h = np.where(r.random((nxr, nyr)) < 0.5, r.uniform(0.002, 0.5, (nxr, nyr)), 0.0)
        cfg = eng.EngineConfig(h_dry=1e-3, collapse_mode="all_pairs", collapse_to_repose=True, collapse_max_passes=100000)
        ba = eng.BankStability(eng.MaterialProps(material_class="noncohesive", cohesion=0.0, phi=PHI_F4), cfg)
        bb = eng.BankStability(eng.MaterialProps(material_class="noncohesive", cohesion=0.0, phi=PHI_F4), cfg)
        a, b = copy.deepcopy(m0), copy.deepcopy(m0)
        FM._ORIG["collapse"](ba, a)
        FM._fast_check_and_collapse(bb, b)
        worst = max(worst, float(np.max(np.abs(a.z_b - b.z_b))), float(np.max(np.abs(a.S - b.S))))
        npass &= ba.last_passes == bb.last_passes
    check("F4 Numba kernel = NumPy reference (to repose, 20 random beds, same number of passes)",
          worst < 1e-9 and npass, f"max diff {worst:.1e}")

# ---------------------------------------------------------------------------------------------------------------------
# F5: Culmann on whole banks, wedge removed by volume (collapse_mode = "bank_wedge"); F5_THEORY_NOTE_2026-11-12.md
# ---------------------------------------------------------------------------------------------------------------------
C_F5, TANPHI_F5, POR_F5 = 25e3, 0.55, 0.35
PHI_F5 = float(np.degrees(np.arctan(TANPHI_F5)))
GAM_F5 = (2650.0 * (1 - POR_F5) + 1000.0 * POR_F5) * 9.81


def hc_f5(beta):
    ph = np.arctan(TANPHI_F5)
    return 4 * C_F5 * np.sin(beta) * np.cos(ph) / (GAM_F5 * (1 - np.cos(beta - ph)))


def solids(m):
    return (float(np.sum(m.z_b)) * (1 - POR_F5) + float(np.sum(m.S))) * m.dx * m.dy


def bank5(dx, prof, eta=0.0, cap=50, orient=0, mode="bank_wedge", c=C_F5):
    """Bed profile prof(x) [m] on 0..40 m, 3 cells wide, one collapse call. orient: 0 = bank drops toward +x,
    1 = toward -x, 2 = toward +y, 3 = toward -y. Returns (profile after, bank object, bulk volume moved, x, mesh)."""
    n = int(round(40.0 / dx))
    x = (np.arange(n) + 0.5) * dx
    z1 = np.asarray(prof(x), dtype=float)
    if orient in (1, 3):
        z1 = z1[::-1]
    zb_ = np.tile(z1[:, None], (1, 3))
    if orient >= 2:
        m = eng.create_prism_mesh(3 * dx, 40.0, 3, n, zb_.T.copy(), eta, z_floor=-50.0)
    else:
        m = eng.create_prism_mesh(40.0, 3 * dx, n, 3, zb_.copy(), eta, z_floor=-50.0)
    cfg = eng.EngineConfig(h_dry=1e-3, collapse_mode=mode, collapse_to_repose=True, collapse_max_passes=cap)
    bs = eng.BankStability(eng.MaterialProps(material_class="cohesive", cohesion=c, phi=PHI_F5, porosity=POR_F5), cfg)
    s0 = solids(m)
    vol = bs.check_and_collapse(m)
    zz = (m.z_b[1, :] if orient >= 2 else m.z_b[:, 1]).copy()
    if orient in (1, 3):
        zz = zz[::-1]
    bs.cons = abs(solids(m) - s0) / s0
    return zz, bs, vol / (3 * dx), x, m


def wall5(H):
    return lambda x: np.where(x < 20.0, H, 0.0)


GRIDS_F5 = (12.8 / 6, 12.8 / 9, 12.8 / 12, 0.5)
hc90 = float(hc_f5(np.pi / 2))
res8 = [bank5(dx, wall5(8.0)) for dx in GRIDS_F5]
res86 = [bank5(dx, wall5(8.6)) for dx in GRIDS_F5]
check("F5 vertical wall, cells 2.13 / 1.42 / 1.07 / 0.5 m: stands at 8.0 m and fails at 8.6 m on every grid",
      all(r[2] == 0.0 for r in res8) and all(r[2] > 0.0 for r in res86), f"Culmann Hc(90 deg) = {hc90:.2f} m")
al9 = 0.5 * (np.pi / 2 + np.arctan(TANPHI_F5))
v9, r9 = 0.5 * 81.0 / np.tan(al9), 9.0 / np.tan(al9)
res9 = [bank5(dx, wall5(9.0)) for dx in GRIDS_F5]
vols = [r[2] for r in res9]
rets = [20.0 - float(r[3][r[0] < 9.0 - 1e-9].min()) for r in res9]
check("F5 9 m wall: fallen volume equal to the Culmann wedge on every grid (to 1e-9)",
      all(abs(v - v9) < 1e-9 * v9 for v in vols), f"{v9:.3f} m3/m exact; " + " / ".join(f"{v:.3f}" for v in vols))
check("F5 9 m wall: top retreat equal to H / tan(alpha) within one cell on every grid",
      all(abs(rt - r9) <= dx for rt, dx in zip(rets, GRIDS_F5)), f"{r9:.2f} m exact; " + " / ".join(f"{v:.2f}" for v in rets))
check("F5 solids conserved to round-off (dry toe)", all(r[1].cons < 1e-12 for r in res9 + res86),
      f"max rel. error {max(r[1].cons for r in res9 + res86):.1e}")
wet9 = [bank5(dx, wall5(9.0), eta=2.0) for dx in GRIDS_F5]
check("F5 wet toe (2 m of water): same wedge volume, solids conserved, debris in the sediment store",
      all(abs(r[2] - v9) < 1e-9 * v9 and r[1].cons < 1e-12 and float(np.sum(r[4].S)) > 0 for r in wet9),
      f"max rel. error {max(r[1].cons for r in wet9):.1e}")
ok_or, info_or = True, []
for o in (1, 2, 3):
    zz, bs_, vv, _, _ = bank5(12.8 / 9, wall5(9.0), orient=o)
    ok_or &= bool(np.allclose(zz, res9[1][0], atol=1e-12)) and abs(vv - res9[1][2]) < 1e-9
    info_or.append(f"{vv:.3f}")
check("F5 banks facing -x, +y, -y fail exactly as the bank facing +x", ok_or, " / ".join(info_or) + " m3/m")
# a 14 m bank spread over 2, 3 and 4 drops (1.07 m cells): the pair rule sees only the single steps
ok_sp, info_sp = True, []
dxs = 12.8 / 12
for nd in (2, 3, 4):
    def prof(x, nd=nd):
        k = np.floor((x - 20.0) / dxs + 1e-9)
        return np.where(x < 20.0, 14.0, np.clip(14.0 * (1 - (k + 1) / nd), 0.0, 14.0))
    beta_b = np.arctan2(14.0, (nd - 1) * dxs)
    should = hc_f5(beta_b) < 14.0
    vw = bank5(dxs, prof)[2]
    vp = bank5(dxs, prof, mode="all_pairs")[2]
    ok_sp &= (vw > 0) == bool(should) and should and vp == 0.0
    info_sp.append(f"{nd} drops: Hc {float(hc_f5(beta_b)):.1f} m, wedge {vw:.1f} m3/m, pair rule {vp:.1f}")
check("F5 a 14 m bank over 2, 3, 4 cells fails as one bank (the pair rule moves nothing)", ok_sp, "; ".join(info_sp))
flat = bank5(dxs, lambda x: np.clip((20.0 - x) * 0.5, 0.0, 15.0) )
low = bank5(dxs, wall5(5.0))
check("F5 a bank flatter than phi (20 m high, slope 0.5) and a 5 m wall: nothing moves",
      flat[2] == 0.0 and low[2] == 0.0, f"min FS wall {low[1].last_min_fs:.2f}")
# iterations (sweeps)
check("F5 one wall settles in one sweep (the second sweep finds nothing), on every grid",
      all(r[1].last_passes == 2 for r in res9), "sweeps " + " / ".join(str(r[1].last_passes) for r in res9))
terr = lambda x: np.where(x < 12.0, 18.0, np.where(x < 20.0, 9.0, 0.0))        # two 9 m walls, 8 m bench
ch = [bank5(dx, terr, cap=50) for dx in (12.8 / 9, 12.8 / 12, 0.5)]
again = []
for r in ch:
    bs2 = eng.BankStability(r[1].mat, r[1].cfg)
    again.append((bs2.check_and_collapse(r[4]), bs2.last_min_fs))
check("F5 chain (two 9 m walls on one line): the loop stops by itself and every bank left has FS >= 1",
      all(3 <= r[1].last_passes < 50 for r in ch) and all(a[0] == 0.0 and a[1] >= 1.0 for a in again),
      "sweeps " + " / ".join(str(r[1].last_passes) for r in ch) + f"; min FS after {min(a[1] for a in again):.2f}")
check("F5 chain: the sweeps needed do not grow on a finer grid; fallen volume agrees within 5 %",
      max(r[1].last_passes for r in ch) <= min(r[1].last_passes for r in ch) + 1
      and max(r[2] for r in ch) / min(r[2] for r in ch) < 1.05,
      "volume " + " / ".join(f"{r[2]:.1f}" for r in ch) + " m3/m")
c500 = bank5(12.8 / 12, terr, cap=500)
check("F5 the result does not depend on the cap once the cap is not reached",
      np.array_equal(c500[0], ch[1][0]) and c500[1].last_passes == ch[1][1].last_passes, f"sweeps {c500[1].last_passes}")
h0 = eng.BankStability.stats["limit_hits"]
bank5(12.8 / 12, terr, cap=1)
check("F5 a call that ends at the cap is counted", eng.BankStability.stats["limit_hits"] == h0 + 1,
      f"hits {h0} -> {eng.BankStability.stats['limit_hits']}")
sand_w = bank5(1.0, wall5(4.0), c=0.0, cap=100000)
sand_p = bank5(1.0, wall5(4.0), c=0.0, mode="all_pairs", cap=100000)
check("F5 c = 0: 'bank_wedge' acts exactly as 'all_pairs' (collapse to the repose angle, F4)",
      np.array_equal(sand_w[0], sand_p[0]) and float(np.max(-np.diff(sand_w[0]))) <= TANPHI_F5 * 1.0 + 2e-6,
      f"max slope {float(np.max(-np.diff(sand_w[0]))):.5f}")
try:
    bank5(1.0, wall5(9.0), mode="xyz")
    check("F5 option rejected: bad collapse_mode", False)
except ValueError:
    check("F5 option rejected: bad collapse_mode", True)
if fm_on:
    import copy
    worst = 0.0
    for prof_, eta_ in ((wall5(9.0), 0.0), (terr, 0.0), (wall5(9.0), 2.0)):
        m0 = bank5(12.8 / 12, prof_, eta=eta_, mode="all_pairs", c=1e9)[4]      # untouched mesh (nothing fails)
        cfg = eng.EngineConfig(h_dry=1e-3, collapse_mode="bank_wedge", collapse_to_repose=True, collapse_max_passes=50)
        mat = eng.MaterialProps(material_class="cohesive", cohesion=C_F5, phi=PHI_F5, porosity=POR_F5)
        a, b = copy.deepcopy(m0), copy.deepcopy(m0)
        FM._ORIG["collapse"](eng.BankStability(mat, cfg), a)
        FM._fast_check_and_collapse(eng.BankStability(mat, cfg), b)
        worst = max(worst, float(np.max(np.abs(a.z_b - b.z_b))), float(np.max(np.abs(a.S - b.S))))
    check("F5 with the Numba backend on: same result as NumPy (the whole-bank rule runs in NumPy)", worst == 0.0,
          f"max diff {worst:.1e}")

print(f"\nV3.4 checks: {N_PASS} of {N_ALL} passed")
sys.exit(0 if N_PASS == N_ALL else 1)
