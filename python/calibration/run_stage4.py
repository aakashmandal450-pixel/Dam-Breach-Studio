"""Stage 4: blind validation runs on the frozen cal-2 model (validation/calibration/STAGE4_PROTOCOL.md).

Runs, and nothing else: this script never opens observed_validation.csv and never scores a validation case.
  * every validation-tier case (cases/*.json, tier "validation") with the frozen cal-2 factors (primary, "F_all")
  * the same cases with each distinct leave-one-out factor set of cal-2.json (secondary: LOO envelope)
  * IMPACT_1-02 with the alternative (IMPACT WP2) inflow hydrograph (secondary: inflow sensitivity)
  * Walsh S1 / S3 / S5 (tier "seen-validation", split-5) through diag_walsh.py at H/16 (primary) and H/24 (grid check)
When every run has a result it writes runs/stage4/MANIFEST.json (SHA-256 of each result file, engine and config files).
Commit and tag `stage4-runs` before running score_stage4.py.

Usage (from the python folder):
    python -u calibration\\run_stage4.py --list
    python -u calibration\\run_stage4.py --workers 5          # re-running skips finished runs and resumes checkpoints
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
OUT = ROOT / "runs" / "stage4"
MAX_CPU = 28800.0          # 8 h CPU per run (as the cal-2 grid)
CK_EVERY = 1800.0
WALSH = {"WalshS1": 0.54, "WalshS3": 0.37, "WalshS5": 0.46}   # pilot width = B* at T = 0 (case files, split-5)
WALSH_T_END = 600.0


def factor_sets():
    cal2 = json.loads((HERE / "cal-2.json").read_text())
    sets = {"F_all": dict(cal2["factors"])}
    seen = {tuple(round(v, 6) for v in cal2["factors"].values())}
    for r in cal2["loo"]:
        f = {"f_kd": r["f_kd"], "C_h": r["C_h"], "f_t": r["f_t"]}
        key = tuple(round(v, 6) for v in f.values())
        if key not in seen:
            seen.add(key)
            sets[f"LOO_{len(sets)}"] = f
    return sets


def plan():
    sets = factor_sets()
    tasks = []
    for f in sorted((HERE / "cases").glob("*.json")):
        c = json.loads(f.read_text())
        if c.get("tier") != "validation":
            continue
        for name, fac in sets.items():
            tasks.append(("case", c["id"], name, fac, None))
        if "inflow_wp2" in c:
            tasks.append(("case", c["id"], "F_all_inflowWP2", sets["F_all"], "inflow_wp2"))
    for cid in WALSH:
        for grid in (16, 24):
            tasks.append(("walsh", cid, f"H{grid}", None, grid))
    return tasks, sets


def run_name(task):
    kind, cid, name, _, _ = task
    return f"{cid}__{name}.json"


def worker(task):
    kind, cid, name, fac, extra = task
    path = OUT / run_name(task)
    if path.exists():
        return cid, name, "skip", 0.0
    t0 = time.time()
    try:
        if kind == "walsh":
            r = run_walsh(cid, extra)
        else:
            sys.path.insert(0, str(HERE.parent))
            import fast_hydro
            if not fast_hydro.enable():
                raise RuntimeError("numba is not installed")
            import cases as C
            c = C.load_case(cid)
            if extra == "inflow_wp2":
                c = dict(c)
                c["inflow"] = c["inflow_wp2"]
            r = C.run(c, fac, chunk_s=60.0, model="cal-2", post_peak_stop=True, max_cpu_seconds=MAX_CPU,
                      checkpoint_dir=str(OUT / "_ckpt" / path.stem), checkpoint_every_cpu_s=CK_EVERY)
            r["set"] = name
            r["variant"] = extra
            # derived output for the drawdown limit: lake level at the end, from the case stage-volume curve
            try:
                import numpy as np
                curve = C._stage_volume(c["reservoir"], float(c["H"]))
                L = np.array(sorted(curve)); V = np.array([curve[k] for k in L])
                r["lake_level_end_m"] = float(np.interp(r["lake_volume_end_m3"], V, L))
                r["lake_level_start_m"] = float(c.get("initial_level", c["H"]))
            except Exception as exc:          # informative only
                r["lake_level_note"] = repr(exc)
            if r.get("stop_cause") in ("wall_safety", "unknown"):
                r["error"] = f"stopped by {r['stop_cause']}"
    except Exception as exc:
        r = {"id": cid, "set": name, "error": repr(exc), "traceback": traceback.format_exc()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(r, indent=1, default=str))
    os.replace(tmp, path)
    if "error" not in r:
        import shutil
        shutil.rmtree(OUT / "_ckpt" / path.stem, ignore_errors=True)
    return cid, name, ("error" if "error" in r else "ok"), time.time() - t0


def run_walsh(cid, grid):
    out = OUT / "_walsh"
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"_stage4_H{grid}"
    cmd = [sys.executable, "-u", str(HERE / "diag_walsh.py"), "--case", cid, "--model", "cal-2", "--fast",
           "--grid", str(grid), "--t-end", str(WALSH_T_END), "--log-every", "1", "--section-every", "600",
           "--pilot-channel", "--pilot-width", str(WALSH[cid]), "--max-wall", "86400", "--out", str(out),
           "--suffix", suffix]
    t0 = time.process_time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    (out / f"{cid}{suffix}_log.txt").write_text(p.stdout + "\n" + p.stderr)
    if p.returncode != 0:
        raise RuntimeError(f"diag_walsh exit {p.returncode}: {p.stderr[-1500:]}")
    summ = sorted(out.glob(f"{cid}*{suffix}_summary.json"))
    if not summ:
        raise RuntimeError("diag_walsh wrote no summary")
    s = json.loads(summ[-1].read_text())
    st = s["stage3"]
    return {"id": cid, "set": f"H{grid}", "tier": "seen-validation", "grid_divisor": grid,
            "Qp": st["Qp_model_m3s"], "t_peak_from_start_s": st["t_peak_model_s"],
            "t_peak_from_5pct_s": st["t_peak_from_5pct_s"], "B_at_peak": st["breach_width_at_peak_m"],
            "B_final": st["breach_width_model_m"], "balances": list(s["balances"].values()),
            "simulated_s": s["simulated_s"], "summary_file": summ[-1].name, "cmd": cmd[2:]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_manifest(tasks):
    files = {run_name(t): sha(OUT / run_name(t)) for t in tasks}
    code = {str(p.relative_to(ROOT)): sha(p) for p in
            [HERE / "cases.py", HERE / "run_stage4.py", HERE / "diag_walsh.py", HERE / "cal-2.json",
             HERE / "cal2_config.json", HERE.parent / "breach_engine_2d_v3_2.py", HERE.parent / "fast_hydro.py",
             HERE.parent / "fast_morph.py"] + sorted((HERE / "cases").glob("*.json"))}
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    m = {"written": time.strftime("%Y-%m-%dT%H:%M:%S"), "git_head": commit, "results": files, "inputs": code,
         "note": "observed_validation.csv not opened by run_stage4.py"}
    (OUT / "MANIFEST.json").write_text(json.dumps(m, indent=1))
    print(f"MANIFEST.json written: {len(files)} results. Next: commit + tag stage4-runs, then calibration\\score_stage4.py")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    tasks, sets = plan()
    OUT.mkdir(parents=True, exist_ok=True)
    print("factor sets:", json.dumps(sets))
    todo = [t for t in tasks if not (OUT / run_name(t)).exists()]
    print(f"plan: {len(tasks)} runs ({sum(t[0] == 'case' for t in tasks)} blind-case runs, "
          f"{sum(t[0] == 'walsh' for t in tasks)} Walsh runs); {len(todo)} still to do; workers {a.workers}")
    for t in tasks:
        print(f"   {run_name(t):40s} {'done' if (OUT / run_name(t)).exists() else ''}")
    if a.list:
        return
    t0 = time.time()
    if todo:
        ctx = mp.get_context("spawn")
        with ctx.Pool(a.workers, maxtasksperchild=2) as pool:
            for i, (cid, name, status, wall) in enumerate(pool.imap_unordered(worker, todo), 1):
                print(f"[{i}/{len(todo)}] {time.strftime('%H:%M:%S')} {cid:12s} {name:16s} {status:5s} "
                      f"{wall / 60:6.1f} min   elapsed {(time.time() - t0) / 3600:.2f} h", flush=True)
    errors = []
    for t in tasks:
        r = json.loads((OUT / run_name(t)).read_text())
        if "error" in r:
            errors.append(run_name(t))
        elif t[0] == "case" and r.get("censored"):
            print(f"   note: {run_name(t)} censored by the CPU budget (re-run resumes it)")
    if errors:
        print(f"{len(errors)} runs ended with an error: {errors}. Delete those files and re-run to retry.")
        sys.exit(1)
    write_manifest(tasks)
    print(f"stage-4 runs complete in {(time.time() - t0) / 3600:.2f} h")


if __name__ == "__main__":
    main()
