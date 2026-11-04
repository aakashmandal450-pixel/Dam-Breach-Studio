"""Quick checks of the amendment-1 runner options (short, coarse runs; nothing is scored or written to the grid).

Usage (from the python folder of a TEST COPY, see test_amend1.ps1):  python -u calibration\\smoke_amend1.py
Test 4 starts test 3 again in a child process with checkpoints every 5 s of CPU, kills it twice, resumes it,
and requires the final result to equal test 3 exactly.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cases as C

HERE = Path(__file__).resolve().parent
CK = HERE.parent / "_smoke_ckpt"
FAC = {"f_kd": 10.0, "C_h": 10.0, "f_t": 1.0}
PP = dict(post_peak_stop=True, post_peak_window_s=600.0, max_cpu_seconds=900.0)
KEYS = ("Qp", "Tp_h", "B", "steps", "t_end_phys_s", "stop_cause", "lake_volume_end_m3", "max_lowering_m")


def child():
    r = C.run(C.load_case("E1S1"), FAC, grid_divisor=4, chunk_s=60.0, checkpoint_dir=str(CK),
              checkpoint_every_cpu_s=5.0, **PP)
    (CK.parent / "_smoke_ck_result.json").write_text(json.dumps({k: r[k] for k in KEYS + ("restarts",)}))


def main():
    c = C.load_case("E1S1")
    tests = [
        ("1 defaults, short t_end (expect stop_cause t_end, censored False)", dict(t_end=300.0)),
        ("2 CPU budget 5 s (expect cpu_budget, censored True)", dict(max_cpu_seconds=5.0)),
        ("3 post-peak stop, window 600 s, CPU budget 900 s (expect post_peak if it breaches)", PP),
    ]
    ref = None
    for name, kw in tests:
        print(f"\n=== test {name}", flush=True)
        t0 = time.time()
        r = C.run(c, FAC, grid_divisor=4, chunk_s=60.0, progress=True, **kw)
        for k in ("stop_cause", "censored", "capped", "breached", "t_end_phys_s", "t_switch_phys_s", "cpu_s", "wall_s",
                  "steps", "Qp", "Tp_h", "B", "lake_volume_end_m3"):
            print(f"    {k:20s} {r.get(k)}", flush=True)
        print(f"    (took {time.time() - t0:.0f} s)", flush=True)
        ref = r

    print("\n=== test 4 checkpoint / kill / resume (expect identical to test 3)", flush=True)
    shutil.rmtree(CK, ignore_errors=True)
    res_file = CK.parent / "_smoke_ck_result.json"
    if res_file.exists():
        res_file.unlink()
    cmd = [sys.executable, "-u", str(Path(__file__).resolve()), "--child"]
    for i, secs in enumerate((40, 45), 1):
        p = subprocess.Popen(cmd, cwd=str(HERE.parent))
        try:
            p.wait(timeout=secs)
            print(f"    child finished before kill {i}", flush=True)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()
            st = json.loads((CK / "runner.json").read_text()) if (CK / "runner.json").exists() else {}
            print(f"    killed after {secs} s: checkpoint at engine t = {st.get('engine_time')} s, "
                  f"{st.get('n_history')} history entries", flush=True)
    subprocess.run(cmd, cwd=str(HERE.parent), check=True)
    got = json.loads(res_file.read_text())
    ok = True
    for k in KEYS:
        same = got[k] == ref[k]
        ok &= same
        print(f"    {k:20s} test3 {ref[k]!s:24s} resumed {got[k]!s:24s} {'SAME' if same else 'DIFF'}", flush=True)
    print(f"    restarts: {got['restarts']}", flush=True)
    print("    CHECKPOINT TEST PASSED" if ok else "    CHECKPOINT TEST FAILED", flush=True)
    shutil.rmtree(CK, ignore_errors=True)
    print("\nsmoke tests finished", flush=True)


if __name__ == "__main__":
    child() if "--child" in sys.argv else main()
