"""V3.2.1 check: an emptied reservoir offers no stage head (no phantom water).

Small demo dam with a tiny lake and a slide displacement, run long enough to drain.
New behaviour: stage falls to the curve bottom once storage is gone, prism inflow
stops, reservoir water balance closes. Legacy flag reproduces the old defect.
"""
import sys, warnings
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import breach_engine_2d_v3_2 as eng

def run(legacy: bool):
    # flat, non-erodible channel (Hanson with kd = 0, banks/headcut/lateral off) fed by a small lake
    nx, ny = 20, 6
    zb = np.zeros((nx, ny))
    mesh = eng.create_prism_mesh(20.0, 6.0, nx, ny, zb, 0.0, z_floor=0.0)
    mat = eng.MaterialProps(kd=0.0)
    cfg = eng.EngineConfig(transport=eng.TransportFormula.HANSON, downstream_boundary="outfall",
                           lateral_erosion_enabled=False, headcut_enabled=False, bank_collapse_enabled=False)
    res = eng.Reservoir({0.0: 0.0, 0.5: 400.0, 1.0: 1200.0}, 0.5)
    res.legacy_unlimited_draw = legacy
    res.apply_displacement(100.0, 1.0)          # debris occupies the bottom of the basin
    e = eng.UltimateBreachEngine(mesh, res, mat, cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        e.run(t_end=900.0, Qin=0.0, verbose=False)
    late = [h for h in e.history if h["time"] > 800.0]
    q_late = float(np.mean([h["Q_in_prism"] for h in late]))
    return e, res, q_late

fails = 0
def check(name, ok, detail):
    global fails
    print(("PASS  " if ok else "FAIL  ") + name + "  " + detail)
    fails += 0 if ok else 1

e, res, q_late = run(legacy=False)
check("reservoir drains to empty", res.empty, f"volume={res.volume:.3g} m3, level={res.level:.3f} m")
check("no prism inflow from an empty lake", q_late < 1e-3, f"mean Q_in_prism after 800 s = {q_late:.3g} m3/s")
check("clipped water is negligible", res.clipped_m3 < 1e-6, f"clipped={res.clipped_m3:.3g} m3")
err = e.reservoir_water_balance_error()
check("reservoir balance closes to the clipped amount", abs(err - res.clipped_m3) < 1e-6 and abs(err) < 1e-6, f"err={err:+.3g} m3")
check("prism water balance", abs(e.water_balance_error()) < 1e-6, f"err={e.water_balance_error():+.2e} m3")

e2, res2, q_late2 = run(legacy=True)
check("legacy flag reproduces the old phantom inflow", q_late2 > 1e-3 and res2.clipped_m3 > 50.0,
      f"legacy Q late={q_late2:.3g} m3/s, clipped={res2.clipped_m3:.3g} m3, err={e2.reservoir_water_balance_error():+.3g} m3")
print(f"\n{6-fails}/6 V3.2.1 reservoir checks passed")
sys.exit(1 if fails else 0)
