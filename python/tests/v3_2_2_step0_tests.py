"""V3.2.2 (Step 0) checks: grain-shear erosion option, breach-width metric, initiation basis."""
import sys, warnings
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import breach_engine_2d_v3_2 as eng

fails, total = 0, 0
def check(name, ok, detail=""):
    global fails, total
    total += 1
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + detail if detail else ""))
    fails += 0 if ok else 1

def mesh_with_flow(h, u):
    zb = np.zeros((6, 4))
    m = eng.create_prism_mesh(6.0, 4.0, 6, 4, zb, h)
    m.u[:] = u
    return m

# 1. grain shear formula and cap
cfg = eng.EngineConfig(friction_model="manning", manning_n=0.05, erosion_shear="grain")
hy = eng.Hydrodynamics(cfg, 1000.0, grain_n=0.0264)
m = mesh_with_flow(2.0, 3.0)
hy.bed_shear(m)
expect = 1000 * 9.81 * 0.0264**2 * 9.0 / 2.0 ** (1 / 3)
check("grain shear = rho g n'^2 U^2 / h^(1/3)", np.allclose(m.tau_b, expect), f"{m.tau_b[0,0]:.2f} vs {expect:.2f} Pa")
total_tau = 1000 * 9.81 * 0.05**2 * 9.0 / 2.0 ** (1 / 3)
check("total shear still reported", abs(hy.last_tau_total_max - total_tau) < 1e-9, f"{hy.last_tau_total_max:.2f} Pa")
cfg2 = eng.EngineConfig(friction_model="manning", manning_n=0.02, erosion_shear="grain")
hy2 = eng.Hydrodynamics(cfg2, 1000.0, grain_n=0.0264)
m2 = mesh_with_flow(2.0, 3.0); hy2.bed_shear(m2)
check("grain shear capped at total when n' > n", np.allclose(m2.tau_b, 1000 * 9.81 * 0.02**2 * 9.0 / 2.0 ** (1 / 3)))
# n independence of erosion shear for the same flow
for n in (0.035, 0.05):
    c = eng.EngineConfig(friction_model="manning", manning_n=n, erosion_shear="grain")
    h_ = eng.Hydrodynamics(c, 1000.0, grain_n=0.0264); mm = mesh_with_flow(2.0, 3.0); h_.bed_shear(mm)
    check(f"erosion shear independent of hydraulic n (n={n})", np.allclose(mm.tau_b, expect))
cfg3 = eng.EngineConfig(friction_model="manning", manning_n=0.05)
hy3 = eng.Hydrodynamics(cfg3, 1000.0); m3 = mesh_with_flow(2.0, 3.0); hy3.bed_shear(m3)
check("default 'total' unchanged", np.allclose(m3.tau_b, total_tau))
# engine default grain n from D50 (Strickler)
mesh, res, mat, c4 = eng.make_demo_setup()
c4.erosion_shear = "grain"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    e = eng.UltimateBreachEngine(mesh, res, mat, c4)
check("grain n from D50 (Strickler)", abs(e.grain_n - mat.D50 ** (1 / 6) / 21.1) < 1e-12, f"n'={e.grain_n:.4f} for D50={mat.D50} m")

# 2. breach width metric
mesh, res, mat, c5 = eng.make_demo_setup(pilot_notch=False)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    e5 = eng.UltimateBreachEngine(mesh, res, mat, c5)
rows = np.where(e5._crest_rows)[0]
low = np.full(mesh.ny, 0.3); low[8:12] = 2.0               # 2 m deep notch, 0.3 m strip elsewhere
mesh.z_b[rows, :] -= low[None, :]
w_new = e5.breach_development()["width_m"]
c5.breach_width_fraction = 0.0
w_old = e5.breach_development()["width_m"]
check("width counts only columns >= 50% of max lowering", abs(w_new - 4 * mesh.dy) < 1e-9, f"{w_new} m (legacy {w_old} m)")
check("legacy width (fraction 0) counts the stripped crest", abs(w_old - mesh.ny * mesh.dy) < 1e-9)

# 3. initiation basis
mon = eng.InitiationMonitor()
mon.records = [{"time": 10.0, "max_lowering_m": 1.2, "channelization_index": 4.0, "BDI": 0.1},
               {"time": 50.0, "max_lowering_m": 3.0, "channelization_index": 1.1, "BDI": 0.3}]
crit_final = eng.InitiationCriterion(min_lowering_m=1.0, min_channelization=1.5, t_max_s=100.0)
crit_best = eng.InitiationCriterion(min_lowering_m=1.0, min_channelization=1.5, t_max_s=100.0, channelization_basis="best")
rf = eng.initiation_success(mon, crit_final, seeded=False)
rb = eng.initiation_success(mon, crit_best, seeded=False)
check("final basis fails a run that ended uniform", (not rf["success"]) and rf["channelization_at_lowering"] == 1.1)
check("best basis (legacy) still reports met", rb["success"] and rb["channelization_at_lowering"] == 4.0)

# 4. stop when the lake is drained (flat non-erodible channel, small lake)
mesh = eng.create_prism_mesh(20.0, 6.0, 20, 6, np.zeros((20, 6)), 0.0, z_floor=0.0)
c6 = eng.EngineConfig(transport=eng.TransportFormula.HANSON, downstream_boundary="outfall",
                      lateral_erosion_enabled=False, headcut_enabled=False, bank_collapse_enabled=False)
res6 = eng.Reservoir({0.0: 0.0, 0.5: 400.0, 1.0: 1200.0}, 0.5)
e6 = eng.UltimateBreachEngine(mesh, res6, eng.MaterialProps(kd=0.0), c6)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    e6.run(t_end=5000.0, Qin=0.0, verbose=False, stop_when_drained_s=60.0, drained_volume_m3=20.0)
check("run stops 60 s after the lake is drained", e6.stop_reason == "reservoir_drained" and e6.time < 5000.0,
      f"stopped at t={e6.time:.0f} s ({e6.stop_reason}), lake {res6.volume:.2f} m3")

# 5. transport capacity factor scales capacity laws linearly
for f in (eng.TransportFormula.WU, eng.TransportFormula.MPM, eng.TransportFormula.VAN_RIJN):
    c1 = eng.EngineConfig(transport=f); c2 = eng.EngineConfig(transport=f, transport_capacity_factor=2.5)
    m = eng.MaterialProps(D50=0.001)
    tau = np.array([5.0, 20.0])
    q1 = eng.SedimentTransport(c1, m).capacity(tau); q2 = eng.SedimentTransport(c2, m).capacity(tau)
    check(f"capacity factor scales {f.value}", np.allclose(q2, 2.5 * q1) and q1[1] > 0)

# 6. suspended load (Wu, Wang & Jia 2000) is optional and additive
cb = eng.EngineConfig(transport=eng.TransportFormula.WU)
cs = eng.EngineConfig(transport=eng.TransportFormula.WU, suspended_load="wu2000")
m = eng.MaterialProps(D50=0.00012)
tau = np.array([0.01, 1.0, 5.0]); U = np.array([0.5, 0.5, 1.0])
tb, ts = eng.SedimentTransport(cb, m), eng.SedimentTransport(cs, m)
qb, qs = tb.capacity(tau, U), ts.capacity(tau, U)
ws = ts.settling_velocity()
check("settling velocity of 0.12 mm sand is about 1 cm/s", 0.005 < ws < 0.015, f"w_s = {ws * 100:.2f} cm/s")
check("suspended load off by default", np.allclose(qb, tb._bed_capacity(tau)))
check("suspended load adds a positive amount above threshold", qs[0] == qb[0] == 0.0 and np.all(qs[1:] > qb[1:]),
      f"bed {qb[1:]} vs total {qs[1:]}")

print(f"\n{total - fails}/{total} V3.2.2 Step 0 checks passed")
sys.exit(1 if fails else 0)
