"""V3.3 checks (cal-2 changes, CAL2_PROPOSAL.md). Defaults must reproduce V3.2.2; this file tests the new options.

C2: general slope collapse (collapse_mode='all_pairs').
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

print(f"\nV3.3 checks: {total - fails} of {total} passed", flush=True)
sys.exit(1 if fails else 0)
