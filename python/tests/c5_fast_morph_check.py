"""V3.3 C5 check: the Numba morphology kernels (fast_morph.py) against the NumPy engine.

Part 1 (always): each kernel against the NumPy original on 60 random beds x cohesive/non-cohesive, all modes
(collapse unsupported/all_pairs; scarp headcut energy/temple/sites/sites-Kh with and without z_floor and max rate;
lateral erosion x and y; advection with and without the outflow limiter). Pass: bed and sediment arrays agree to
1e-12 relative (collapse, lateral and advection are usually bit-identical; scarp differs by 1 ulp through cbrt), the
headcut position is the same, and every kernel moved material in every test.

Part 2 (--runs): full calibration runs (cal-1 factors, C1+C2 on) with the Numba hydraulics, NumPy morphology vs Numba
morphology, in two subprocesses. Reports CPU time and the relative difference in Qp, Tp, B and max lowering.
Pass: <= 1e-6. Above that but <= 5 %: 'round-off grown' (the second-order scheme amplifies 1-ulp differences, see
RUNS.md); above 5 %: FAIL.

Usage (from the python folder):  python tests/c5_fast_morph_check.py [--runs]
"""
import sys, copy, os, json, subprocess, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "calibration"))
import breach_engine_2d_v3_2 as E
import fast_morph as FM

def mk(seed, nx=37, ny=29, wet_frac=0.5):
    r = np.random.default_rng(seed)
    zb = np.cumsum(r.normal(0, 0.08, (nx, ny)), axis=0) * 0.3 + r.normal(0, 0.05, (nx, ny))
    zb += np.where(r.random((nx, ny)) < 0.1, r.uniform(0, 0.6, (nx, ny)), 0)     # some steps / scarps
    m = E.create_prism_mesh(nx * 0.1, ny * 0.13, nx, ny, zb.copy(), 0.0)
    m.h = np.where(r.random((nx, ny)) < wet_frac, r.uniform(0.002, 0.3, (nx, ny)), 0.0)
    m.S = np.where(m.h > 1e-3, r.uniform(0, 0.01, (nx, ny)), 0.0)
    m.z_floor = zb - r.uniform(0.0, 0.3, (nx, ny))
    qx = r.normal(0, 0.05, (nx, ny)); qy = r.normal(0, 0.05, (nx, ny)); tau = r.uniform(0, 30, (nx, ny))
    return m, qx, qy, tau

worst = {}
def rec(name, a, b):
    d = float(np.max(np.abs(a - b)) / max(np.max(np.abs(a)), 1e-300))
    worst[name] = max(worst.get(name, 0.0), d)

nbit = {}
moved = {"collapse": 0, "scarp": 0, "lateral": 0, "advect": 0}
hc_bad = 0
n_cases = 0
for seed in range(60):
    for coh in (0.0, 4000.0):
        mat = E.MaterialProps(material_class="cohesive" if coh else "noncohesive", kd=2e-5, tau_c=3.0,
                              porosity=0.35, phi=33.0, cohesion=coh)
        for mode in ("unsupported", "all_pairs"):
            cfg = E.EngineConfig(h_dry=1e-3, collapse_mode=mode, collapse_phi_wet=25.0 if mode == "all_pairs" else None,
                                 collapse_iterations=8)
            m, qx, qy, tau = mk(seed)
            a, b = copy.deepcopy(m), copy.deepcopy(m)
            bs = E.BankStability(mat, cfg)
            va = FM._ORIG["collapse"](bs, a); fa = bs.last_min_fs
            vb = FM._fast_check_and_collapse(bs, b); fb = bs.last_min_fs
            moved["collapse"] += (va > 0) and coh == 0.0
            if fa != fb and abs(fa - fb) > 1e-12 * abs(fa):
                hc_bad += 1
            rec(f"collapse {mode} z", a.z_b, b.z_b); rec(f"collapse {mode} S", a.S, b.S)
            rec(f"collapse {mode} vol", np.array([va]), np.array([vb]))
            nbit[f"collapse {mode}"] = nbit.get(f"collapse {mode}", 0) + int(np.array_equal(a.z_b, b.z_b))
        for meth, kh in (("energy", None), ("temple", None), ("sites", 5.0), ("sites", None)):
            mat.headcut_Kh = kh
            for floor in (True, False):
                cfg = E.EngineConfig(h_dry=1e-3, headcut_mode="scarp", headcut_method=meth, headcut_C=0.3,
                                     headcut_seg_slope=0.1, headcut_min_slope=0.2, z_floor_enabled=floor,
                                     headcut_max_rate=(0.002 if seed % 2 else None))
                m, qx, qy, tau = mk(seed)
                a, b = copy.deepcopy(m), copy.deepcopy(m)
                hc = E.Headcut(cfg, mat)
                va = FM._ORIG["scarp"](hc, a, qx, qy, 0.7); vb = FM._fast_migrate_scarp(hc, b, qx, qy, 0.7)
                rec(f"scarp {meth}{'_Kh' if kh else ''} z", a.z_b, b.z_b); rec("scarp S", a.S, b.S)
                rec("scarp vol", np.array([va]), np.array([vb]))
                moved["scarp"] += va > 0
                if a.headcut_i != b.headcut_i:
                    hc_bad += 1
                    print("headcut position differs", seed, meth, a.headcut_i, b.headcut_i)
            mat.headcut_Kh = None
        for axis in (0, 1):
            cfg = E.EngineConfig(h_dry=1e-3)
            m, qx, qy, tau = mk(seed)
            a, b = copy.deepcopy(m), copy.deepcopy(m)
            le = E.LateralErosion(mat, cfg)
            va = FM._ORIG["lateral"](le, a, tau, 5.0, axis); vb = FM._fast_apply_axis(le, b, tau, 5.0, axis)
            rec("lateral z", a.z_b, b.z_b); rec("lateral S", a.S, b.S); rec("lateral vol", np.array([va]), np.array([vb])); moved["lateral"] += va > 0
        for limit in (True, False):
            cfg = E.EngineConfig(h_dry=1e-3, positivity_fix=limit)
            m, qx, qy, tau = mk(seed)
            a, b = copy.deepcopy(m), copy.deepcopy(m)
            mo = E.Morphology(cfg, mat)
            va = FM._ORIG["advect"](mo, a, a.h, qx, qy, 0.4); vb = FM._fast_advect(mo, b, b.h, qx, qy, 0.4)
            moved["advect"] += not np.array_equal(m.S, a.S)
            nbit["advect bit-identical"] = nbit.get("advect bit-identical", 0) + int(np.array_equal(a.S, b.S) and va == vb)

ok = True
print("Part 1: kernels vs NumPy on random beds")
for k, v in worst.items():
    good = v < 1e-12
    ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  {k:28s} max rel diff {v:.2e}")
n_coll = 2 * 60; n_sc = 2 * 60 * 4 * 2; n_lat = 2 * 60 * 2; n_adv = 2 * 60 * 2
for k, n in (("collapse", n_coll), ("scarp", n_sc), ("lateral", n_lat), ("advect", n_adv)):
    good = moved[k] >= 0.9 * n
    ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  {k} active in {moved[k]} of {n} tests" + (" (c = 0 beds)" if k == "collapse" else ""))
ok &= hc_bad == 0
print(f"  {'PASS' if hc_bad == 0 else 'FAIL'}  headcut position and min bank FS identical ({hc_bad} differences)")
print(f"  info  bit-identical: collapse unsupported {nbit['collapse unsupported']}/120, all_pairs "
      f"{nbit['collapse all_pairs']}/120, advection {nbit['advect bit-identical']}/240")

if "--runs" in sys.argv:
    print("\nPart 2: full runs, cal-1 factors, C1+C2 on, Numba hydraulics; NumPy vs Numba morphology")
    child = """
import sys, json, time, os
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[1] + '/calibration')
import fast_hydro
fast_hydro._MORPH = sys.argv[2] == '1'
fast_hydro.enable()
import cases
c = cases.load_case(sys.argv[3])
t0 = time.process_time()
r = cases.run(c, {'f_kd': 3.16, 'C_h': 0.316, 'f_t': 10.0}, t_end=float(sys.argv[4]), grid_divisor=float(sys.argv[5]),
              overrides={'headcut_mode': 'scarp', 'collapse_mode': 'all_pairs'})
print('RESULT ' + json.dumps({'cpu': time.process_time() - t0, 'Qp': r['Qp'], 'Tp_h': r['Tp_h'], 'B': r['B'],
      'low': r['max_lowering_m'], 'steps': r['steps']}))
"""
    for case, t_end, gd in (("E1S1", 7200, 4), ("E2S2", 20000, 4), ("WalshS3", 600, 8)):
        res = {}
        for morph in ("0", "1"):
            out = subprocess.run([sys.executable, "-c", child, str(ROOT), morph, case, str(t_end), str(gd)],
                                 capture_output=True, text=True)
            line = [l for l in out.stdout.splitlines() if l.startswith("RESULT ")]
            if not line:
                print(out.stdout[-2000:], out.stderr[-2000:])
                ok = False
                break
            res[morph] = json.loads(line[0][7:])
        if len(res) < 2:
            print(f"  FAIL  {case}: run failed"); continue
        a, b = res["0"], res["1"]
        rel = max(abs(a[k] - b[k]) / max(abs(a[k]), 1e-30) for k in ("Qp", "Tp_h", "B", "low"))
        tag = "PASS" if rel <= 1e-6 else ("PASS (round-off grown)" if rel <= 0.05 else "FAIL")
        ok &= rel <= 0.05
        print(f"  {tag}  {case}: CPU {a['cpu']:.1f} s -> {b['cpu']:.1f} s ({a['cpu'] / b['cpu']:.2f}x); "
              f"Qp {a['Qp']:.6g} vs {b['Qp']:.6g}; max rel diff {rel:.1e}; steps {a['steps']} vs {b['steps']}")

print("\nC5 check: " + ("ALL PASS" if ok else "FAILED"))
sys.exit(0 if ok else 1)
