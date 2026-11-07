"""Profile the 2-D breach engine on short runs of the calibration cases (read-only; nothing is scored or written to
the calibration grid).

For each scenario it does one run WITHOUT the profiler (true ms per step) and one run WITH cProfile (where the time
goes), prints the slowest functions, and saves the raw profile to runs/profile/<scenario>.prof.

Usage (from the python folder):   python -u calibration\\profile_engine.py
Optional:                          python -u calibration\\profile_engine.py --only E2S2_post Goose
Takes about 20-30 min on one core. Run it next to the calibration re-run; it uses one process.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import os
import pstats
import sys
import time
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases as C  # noqa: E402

OUT = HERE.parent.parent / "runs" / "profile"

# name: (case, factors, physical t_end [s], note)
SCENARIOS = {
    "E2S2_pre":   ("E2S2", {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}, 2000.0, "lab, accelerated initiation (A = 10)"),
    "E2S2_post":  ("E2S2", {"f_kd": 10.0, "C_h": 1.0, "f_t": 1.0}, 4800.0, "lab, switches to A = 1 at 3,600 s, then breach flow"),
    "E1S1":       ("E1S1", {"f_kd": 10.0, "C_h": 10.0, "f_t": 1.0}, 3000.0, "lab, through initiation into breach"),
    "Goose":      ("GooseCreek", {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}, 600.0, "field, cohesive, no acceleration"),
    "Castlewood": ("Castlewood", {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}, 1800.0, "field, non-cohesive"),
}


def one_run(case, fac, t_end):
    t0, c0 = time.perf_counter(), time.process_time()
    r = C.run(C.load_case(case), fac, t_end=t_end, chunk_s=60.0)
    return r, time.perf_counter() - t0, time.process_time() - c0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None, help="scenario names to run (default: all)")
    a = ap.parse_args()
    names = a.only or list(SCENARIOS)
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"engine profiling, {len(names)} scenarios, started {time.strftime('%H:%M:%S')}", flush=True)
    summary = []
    for n in names:
        case, fac, t_end, note = SCENARIOS[n]
        print(f"\n=== {n}: {case} {fac}, {t_end:.0f} s physical ({note})", flush=True)
        print("    [1/2] timing run without profiler ...", flush=True)
        r, wall, cpu = one_run(case, fac, t_end)
        ms = 1000 * cpu / max(r["steps"], 1)
        print(f"    steps {r['steps']:,}  cpu {cpu:.1f} s  wall {wall:.1f} s  -> {ms:.3f} ms/step (CPU)  grid {r['grid'][:2]}",
              flush=True)
        print("    [2/2] profiled run ...", flush=True)
        pr = cProfile.Profile()
        pr.enable()
        r2, wall2, cpu2 = one_run(case, fac, t_end)
        pr.disable()
        pr.dump_stats(str(OUT / f"{n}.prof"))
        s = io.StringIO()
        st = pstats.Stats(pr, stream=s)
        st.sort_stats("tottime").print_stats(20)
        print("    --- slowest functions by own time (tottime) ---", flush=True)
        lines = s.getvalue().splitlines()
        start = next((i for i, l in enumerate(lines) if "ncalls" in l), 0)
        for l in lines[start:start + 21]:
            print("    " + l, flush=True)
        s2 = io.StringIO()
        pstats.Stats(pr, stream=s2).sort_stats("cumulative").print_stats("breach_engine", 25)
        print("    --- engine functions by cumulative time ---", flush=True)
        lines = s2.getvalue().splitlines()
        start = next((i for i, l in enumerate(lines) if "ncalls" in l), 0)
        for l in lines[start:start + 26]:
            print("    " + l, flush=True)
        summary.append((n, r["steps"], ms, cpu2 / max(cpu, 1e-9)))
    print("\n=== SUMMARY (CPU time per step, without profiler)", flush=True)
    for n, steps, ms, ovh in summary:
        print(f"    {n:11s} {steps:>9,} steps   {ms:7.3f} ms/step   (profiler overhead x{ovh:.1f})", flush=True)
    print(f"\nprofiles saved in {OUT}; finished {time.strftime('%H:%M:%S')}", flush=True)


if __name__ == "__main__":
    main()
