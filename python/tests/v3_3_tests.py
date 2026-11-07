"""V3.3 checks (cal-2 changes, CAL2_PROPOSAL.md). Defaults must reproduce V3.2.2; this file tests the new options.

C2: general slope collapse (collapse_mode='all_pairs').
C1: scarp-based headcut (headcut_mode='scarp').
"""
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import breach_engine_2d_v3_2 as eng

warnings.simplefilter("ignore")
fails, total = 0, 0


def check(name, ok, detail=""):
    global fails, total
    total += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + detail if detail else ""), flush=True)
    fails += 0 if ok else 1


def solids(m, p):
    """Bulk-equivalent solids: bed (bulk) + sediment store converted to bulk volume."""
    return float(np.sum(m.z_b) + np.sum(m.S) / (1.0 - p)) * m.dx * m.dy


def max_slope_deg(z, ds, axis):
    return float(np.degrees(np.arctan(np.max(np.abs(np.diff(z, axis=axis))) / ds)))


def collapse(zb, eta, mode="all_pairs", c=0.0, phi=33.0, iters=200, **kw):
    nx, ny = zb.shape
    m = eng.create_prism_mesh(nx * 0.1, ny * 0.1, nx, ny, zb.copy(), eta)
    mat = eng.MaterialProps(cohesion=c, phi=phi, porosity=0.35)
    cfg = eng.EngineConfig(collapse_mode=mode, collapse_iterations=iters, h_dry=1e-3, **kw)
    bs = eng.BankStability(mat, cfg)
    before = solids(m, mat.porosity)
    moved = bs.check_and_collapse(m)
    return m, moved, solids(m, mat.porosity) - before


phi = 33.0
tphi = np.tan(np.deg2rad(phi))

# ---- C2.1 dry 60 deg step along x relaxes to phi, mass conserved
zb = np.zeros((20, 4)); zb[:10, :] = 0.6                    # 0.6 m drop over one 0.1 m cell (about 80 deg)
m, moved, dm = collapse(zb, -1.0)                           # dry everywhere
s = max_slope_deg(m.z_b, m.dx, 0)
check("C2 dry step along x relaxes to phi", s <= phi + 0.5, f"max slope {s:.1f} deg (phi {phi})")
check("C2 dry step: mass conserved", abs(dm) < 1e-12, f"{dm:.1e} m3")

# ---- C2.2 same in y
zb = np.zeros((4, 20)); zb[:, :10] = 0.6
m, moved, dm = collapse(zb, -1.0)
s = max_slope_deg(m.z_b, m.dy, 1)
check("C2 dry step along y relaxes to phi", s <= phi + 0.5, f"max slope {s:.1f} deg")
check("C2 dry step y: mass conserved", abs(dm) < 1e-12, f"{dm:.1e} m3")

# ---- C2.3 submerged 50 deg step relaxes (V3.2.2 'unsupported' leaves it)
zb = np.zeros((20, 4)); zb[:10, :] = 0.12                   # 50 deg between neighbours, all under 2 m of water
m_new, moved_new, dm = collapse(zb, 2.0)
m_old, moved_old, _ = collapse(zb, 2.0, mode="unsupported")
s_new, s_old = max_slope_deg(m_new.z_b, m_new.dx, 0), max_slope_deg(m_old.z_b, m_old.dx, 0)
check("C2 submerged 50 deg step relaxes to phi", s_new <= phi + 0.5, f"{s_new:.1f} deg")
check("C2 V3.2.2 mode leaves the submerged step", moved_old == 0.0 and s_old > 49.0, f"{s_old:.1f} deg, moved {moved_old}")
check("C2 submerged step: mass conserved", abs(dm) < 1e-12, f"{dm:.1e} m3")

# ---- C2.4 a 25 deg slope (below phi) is untouched
x = np.arange(20) * 0.1
zb = np.tile((np.tan(np.deg2rad(25.0)) * (x.max() - x))[:, None], (1, 4))
m, moved, dm = collapse(zb, -1.0)
check("C2 25 deg slope untouched (phi 33)", moved == 0.0 and np.array_equal(m.z_b, zb), f"moved {moved}")

# ---- C2.5 cohesive bank below its Culmann height is untouched; above it fails
mat = eng.MaterialProps(cohesion=5000.0, phi=phi, porosity=0.35)
bs = eng.BankStability(mat, eng.EngineConfig(collapse_mode="all_pairs"))
beta = np.deg2rad(80.0)
Zc = float(bs.critical_height(np.array([beta]))[0])
ds = 0.6 * Zc / np.tan(beta)                                  # cell size giving an 80 deg bank of height 0.6 Zc
zb = np.zeros((20, 4)); zb[:10, :] = 0.6 * Zc
m = eng.create_prism_mesh(20 * ds, 4 * ds, 20, 4, zb.copy(), -1.0)
moved = eng.BankStability(mat, eng.EngineConfig(collapse_mode="all_pairs", collapse_iterations=50)).check_and_collapse(m)
check("C2 cohesive bank below Culmann height untouched", moved == 0.0, f"Zc {Zc:.2f} m, bank {0.6 * Zc:.2f} m")
zb[:10, :] = 1.5 * Zc
m = eng.create_prism_mesh(20 * ds, 4 * ds, 20, 4, zb.copy(), -1.0)
moved = eng.BankStability(mat, eng.EngineConfig(collapse_mode="all_pairs", collapse_iterations=50)).check_and_collapse(m)
check("C2 cohesive bank above Culmann height fails", moved > 0.0, f"bank {1.5 * Zc:.2f} m, moved {moved:.3g} m3")

# ---- C2.6 separate dry / submerged angles
zb = np.zeros((20, 4)); zb[:10, :] = 0.08                    # about 39 deg, submerged
m, _, _ = collapse(zb, 2.0, collapse_phi_wet=20.0, collapse_phi_dry=45.0)
s = max_slope_deg(m.z_b, m.dx, 0)
check("C2 submerged pair uses collapse_phi_wet", s <= 20.5, f"{s:.1f} deg (wet angle 20)")
zb = np.zeros((20, 4)); zb[:10, :] = 0.08
m, moved, _ = collapse(zb, -1.0, collapse_phi_wet=20.0, collapse_phi_dry=45.0)
check("C2 dry pair uses collapse_phi_dry", moved == 0.0, "39 deg dry step stays (dry angle 45)")

# ---- C2.7 bad option rejected
try:
    collapse(np.zeros((4, 4)), -1.0, mode="nonsense")
    check("C2 unknown collapse_mode rejected", False)
except ValueError:
    check("C2 unknown collapse_mode rejected", True)

# =====================================================================================================================
# C1: scarp-based headcut (headcut_mode='scarp')
# =====================================================================================================================

def scarp_mesh(ds, H=0.3, slope=0.5, Lx=6.0, ny=4, axis=0, wet=True, q=0.05, reverse=False):
    """Flat 'upstream' at H, a planar scarp of the given slope, flat 'downstream' at 0; water on the foot."""
    n = int(round(Lx / ds))
    x = (np.arange(n) + 0.5) * ds
    x0 = 2.0                                                  # scarp starts at x0, ends at x0 + H / slope
    line = np.clip(H - slope * (x - x0), 0.0, H)
    if reverse:
        line = line[::-1]
    zb = np.tile(line[:, None], (1, ny)) if axis == 0 else np.tile(line[None, :], (ny, 1))
    eta = 0.05 if wet else -1.0                               # 5 cm of water over the low part only
    m = eng.create_prism_mesh(zb.shape[0] * ds, zb.shape[1] * ds, zb.shape[0], zb.shape[1], zb.copy(), eta)
    qq = np.full_like(zb, q * (-1.0 if reverse else 1.0))
    qx, qy = (qq, np.zeros_like(zb)) if axis == 0 else (np.zeros_like(zb), qq)
    return m, qx, qy


def run_headcut(m, qx, qy, steps=1, dt=0.5, **kw):
    cfg = eng.EngineConfig(headcut_mode="scarp", headcut_min_slope=0.1, headcut_seg_slope=0.1, h_dry=1e-3, **kw)
    mat = eng.MaterialProps(porosity=0.35)
    hc = eng.Headcut(cfg, mat)
    before = solids(m, mat.porosity)
    vol = 0.0
    film = np.any(m.h > 0)
    for _ in range(steps):
        if film:                                     # flowing water covers the whole bed (2 cm film), as in a run
            m.h = np.full_like(m.z_b, 0.02)
        vol += hc.migrate(m, qx, dt, qy=qy)
    return vol, solids(m, mat.porosity) - before


# C1.1 the same physical scarp on two grids: identical erosion rate in one step
v1, _ = run_headcut(*scarp_mesh(0.10))
v2, _ = run_headcut(*scarp_mesh(0.05))
w1, w2 = v1 / (4 * 0.10), v2 / (4 * 0.05)                     # per unit width
check("C1 same scarp, dx and dx/2: same eroded volume per width (one step)", abs(w1 - w2) / w1 < 1e-9,
      f"{w1:.6g} vs {w2:.6g} m3/m")
# C1.2 over many steps the retreat stays within 10 %
v1, dm1 = run_headcut(*scarp_mesh(0.10), steps=400)
v2, dm2 = run_headcut(*scarp_mesh(0.05), steps=400)
w1, w2 = v1 / (4 * 0.10), v2 / (4 * 0.05)
check("C1 same scarp, dx and dx/2: eroded volume per width within 10 % after 400 steps", abs(w1 - w2) / w1 < 0.10,
      f"{w1:.4g} vs {w2:.4g} m3/m")
check("C1 mass conserved", abs(dm1) < 1e-12 and abs(dm2) < 1e-12, f"{dm1:.1e}, {dm2:.1e} m3")
# C1.3 rate law uses the scarp height: energy law R = C (q H)^(1/3), volume per width R H dt
cfgE = eng.EngineConfig()
expect = cfgE.headcut_C * (0.05 * 0.3) ** (1 / 3) * 0.3 * 0.5
v, _ = run_headcut(*scarp_mesh(0.10))
check("C1 one-step volume per width = C (q H_s)^(1/3) H_s dt", abs(v / 0.4 - expect) / expect < 1e-9,
      f"{v / 0.4:.6g} vs {expect:.6g} m3/m")
# C1.4 a gentle slope (0.05 per cell) is not a scarp
v, _ = run_headcut(*scarp_mesh(0.10, slope=0.05))
check("C1 slope 0.05 below the segment threshold: no headcut", v == 0.0)
# C1.5 a scarp in y (flow in +y) and one with flow in -x are found, with the same rate
vy, _ = run_headcut(*scarp_mesh(0.10, axis=1))
vr, _ = run_headcut(*scarp_mesh(0.10, reverse=True))
check("C1 y-direction scarp: same rate as x", abs(vy - v1 / 400 * 0) >= 0 and abs(vy / 0.4 - expect) / expect < 1e-9,
      f"{vy / 0.4:.6g} m3/m")
check("C1 flow in -x: same rate", abs(vr / 0.4 - expect) / expect < 1e-9, f"{vr / 0.4:.6g} m3/m")
# C1.6 flow away from the drop, or a dry foot: no headcut
m, qx, qy = scarp_mesh(0.10)
v, _ = run_headcut(m, -qx, qy)
check("C1 flow away from the scarp: no headcut", v == 0.0)
v, _ = run_headcut(*scarp_mesh(0.10, wet=False))
check("C1 dry foot: no headcut", v == 0.0)
# C1.7 minimum height
v, _ = run_headcut(*scarp_mesh(0.10), headcut_min_height=0.5)
check("C1 headcut_min_height above the scarp height: no headcut", v == 0.0)
# C1.8 bad option rejected
try:
    run_headcut(*scarp_mesh(0.10), headcut_mode_override=True)
except TypeError:
    pass
try:
    hc = eng.Headcut(eng.EngineConfig(headcut_mode="nonsense"), eng.MaterialProps())
    m, qx, qy = scarp_mesh(0.10)
    hc.migrate(m, qx, 0.5, qy=qy)
    check("C1 unknown headcut_mode rejected", False)
except ValueError:
    check("C1 unknown headcut_mode rejected", True)

print(f"\nV3.3 checks: {total - fails} of {total} passed", flush=True)
sys.exit(1 if fails else 0)
