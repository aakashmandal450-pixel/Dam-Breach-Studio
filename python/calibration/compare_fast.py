"""Compare the Numba backend (fast_hydro.py) with the NumPy engine on short runs of every calibration case,
the Walsh S3 setup and the non-default engine options. Read-only: nothing is scored or written to the grid.

PASS criteria per scenario (first-order scheme, as used by cal-1):
  relative difference <= 1e-6 in Qp, Tp, B, maximum lowering, end time and end lake volume, identical step count,
  and water / reservoir / sediment balance errors <= 1e-6 m3 in both runs.
Second-order (MUSCL) check: the second-order scheme is itself sensitive to round-off (a 1e-15 change in Manning n
moves Qp by a few %), so the Numba-NumPy difference is compared with NumPy's own sensitivity to that perturbation;
it passes if it is no larger than 3x that sensitivity (or both are below 1e-6).

Usage (from the python folder):  python -u calibration\\compare_fast.py        (about 30-40 min, one process)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fast_hydro as F  # noqa: E402
import cases as C       # noqa: E402

TOL = 1e-6
FAC = {"f_kd": 10.0, "C_h": 10.0, "f_t": 1.0}
KEYS = ("Qp", "Tp_h", "B", "max_lowering_m", "t_end_phys_s", "lake_volume_end_m3")

# name: (case, t_end physical [s], grid divisor or None, engine overrides or None)
SCENARIOS = [
    ("E1S1", "E1S1", 3000.0, None, None),
    ("E1S3", "E1S3", 3000.0, None, None),
    ("E2S2", "E2S2", 4800.0, None, None),
    ("GooseCreek", "GooseCreek", 600.0, None, None),
    ("Castlewood", "Castlewood", 1800.0, None, None),
    ("SouthFork", "SouthFork", 1800.0, None, None),
    ("WalshS3_H16", "WalshS3", 300.0, 16.0, None),
    ("opt_chezy_total", "E1S1", 3000.0, 4.0, {"friction_model": "chezy", "chezy_C": 30.0, "erosion_shear": "total"}),
    ("opt_wall", "E1S1", 3000.0, 4.0, {"downstream_boundary": "wall"}),
    ("opt_transmissive", "E1S1", 3000.0, 4.0, {"downstream_boundary": "transmissive"}),
    ("opt_cfl_interior", "E1S1", 3000.0, 4.0, {"cfl_interior_only": True}),
]


def run(case, t_end, grid, ov, fast):
    F.enable() if fast else F.disable()
    c0 = time.process_time()
    r = C.run(C.load_case(case), FAC, t_end=t_end, grid_divisor=grid, chunk_s=60.0, overrides=ov)
    return r, time.process_time() - c0


def rel(a, b):
    a, b = float(a), float(b)
    return abs(a - b) / max(abs(a), 1e-12)


def main():
    if not F.HAVE_NUMBA:
        print("FAIL  numba is not installed. Install it with:  python -m pip install numba", flush=True)
        sys.exit(2)
    import numba
    import numpy
    print(f"Numba backend comparison  {time.strftime('%Y-%m-%d %H:%M:%S')}  numba {numba.__version__}, "
          f"numpy {numpy.__version__}, python {sys.version.split()[0]}", flush=True)
    print("compiling the Numba kernels (first call) ...", flush=True)
    t0 = time.perf_counter()
    run("E1S1", 60.0, 4.0, None, True)
    print(f"  done in {time.perf_counter() - t0:.0f} s (cached for later runs)", flush=True)

    results, fails = [], 0
    for name, case, t_end, grid, ov in SCENARIOS:
        print(f"\n=== {name}: {case}, {t_end:.0f} s, grid {grid or 'cal-1'}, overrides {ov}", flush=True)
        a, ca = run(case, t_end, grid, ov, False)
        print(f"    NumPy: {a['steps']:,} steps, {ca:.1f} s CPU", flush=True)
        b, cb = run(case, t_end, grid, ov, True)
        print(f"    Numba: {b['steps']:,} steps, {cb:.1f} s CPU   -> x{ca / max(cb, 1e-9):.1f}", flush=True)
        worst = max(rel(a[k], b[k]) for k in KEYS)
        bal = max(abs(float(x)) for x in list(a["balances"]) + list(b["balances"]))
        ok = worst <= TOL and a["steps"] == b["steps"] and bal <= 1e-6
        for k in KEYS:
            print(f"      {k:20s} NumPy {float(a[k]):.12g}   Numba {float(b[k]):.12g}   rel {rel(a[k], b[k]):.1e}", flush=True)
        print(f"      balances (max abs) {bal:.1e} m3", flush=True)
        print(f"    {'PASS' if ok else 'FAIL'}  worst rel diff {worst:.1e}", flush=True)
        fails += 0 if ok else 1
        results.append((name, ok, worst, ca / max(cb, 1e-9)))

    # second-order: Numba-NumPy difference vs NumPy's own round-off sensitivity
    print("\n=== order2: E1S1 H/4, 3000 s, spatial_order 2 (round-off sensitivity check)", flush=True)
    mesh, res, mat, cfg, meta = C.build(C.load_case("E1S1"), FAC, 4.0)
    n0 = cfg.manning_n
    a, _ = run("E1S1", 3000.0, 4.0, {"spatial_order": 2}, False)
    p, _ = run("E1S1", 3000.0, 4.0, {"spatial_order": 2, "manning_n": n0 * (1 + 1e-15)}, False)
    b, _ = run("E1S1", 3000.0, 4.0, {"spatial_order": 2}, True)
    d_self = max(rel(a[k], p[k]) for k in ("Qp", "Tp_h", "B"))
    d_fast = max(rel(a[k], b[k]) for k in ("Qp", "Tp_h", "B"))
    ok2 = d_fast <= max(3.0 * d_self, TOL)
    print(f"    NumPy vs NumPy with n*(1+1e-15): {d_self:.1e}    NumPy vs Numba: {d_fast:.1e}", flush=True)
    print(f"    {'PASS' if ok2 else 'FAIL'}  (Numba difference within 3x NumPy's own round-off sensitivity)", flush=True)
    fails += 0 if ok2 else 1
    results.append(("order2_sensitivity", ok2, d_fast, float("nan")))

    print("\n=== SUMMARY", flush=True)
    for name, ok, worst, sp in results:
        sp_s = f"x{sp:.1f}" if sp == sp else "   -"
        print(f"    {name:20s} {'PASS' if ok else 'FAIL'}   worst rel diff {worst:.1e}   speed-up {sp_s}", flush=True)
    print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'}", flush=True)
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
