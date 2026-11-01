"""Calibration batch runner (stage 3): runs every calibration case over the pre-registered factor grid.

Usage (from the python folder, in PowerShell):
    python -u calibration\\run_grid.py --workers 6
    python -u calibration\\run_grid.py --workers 6 --only WalshS1,WalshS3      # subset
    python -u calibration\\run_grid.py --list                                   # show the run plan only
Results: one JSON per run in ..\\runs\\calibration_grid\\ (re-running skips finished runs, so it can be stopped and resumed).
Validation cases are never run here.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LOG_GRID = {  # pre-registered coarse grid (log10 values), written before the first calibration run
    "f_kd": [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0],
    "C_h": [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0],
    "f_t": [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0],
}


def plan(only=None):
    import cases as C
    runs = []
    for f in sorted((HERE / "cases").glob("*.json")):
        c = json.loads(f.read_text())
        if c.get("tier") != "calibration" or (only and c["id"] not in only):
            continue
        m = c["material"]
        measured = m["class"] == "cohesive" and m.get("kd_status", "").startswith("measured")
        for ch in LOG_GRID["C_h"]:
            if m["class"] == "cohesive":
                for fk in (LOG_GRID["f_kd"] if measured else [0.0]):
                    runs.append((c["id"], {"f_kd": 10 ** fk, "C_h": 10 ** ch, "f_t": 1.0}))
            else:
                for ft in LOG_GRID["f_t"]:
                    runs.append((c["id"], {"f_kd": 1.0, "C_h": 10 ** ch, "f_t": 10 ** ft}))
    return runs


def run_name(cid, fac):
    return f"{cid}__fkd{fac['f_kd']:.4g}_Ch{fac['C_h']:.4g}_ft{fac['f_t']:.4g}.json"


def worker(args):
    cid, fac, out, max_wall = args
    path = out / run_name(cid, fac)
    if path.exists():
        return cid, "skip", 0.0
    import cases as C
    t0 = time.time()
    try:
        c = C.load_case(cid)
        r = C.run(c, fac, max_wall_seconds=max_wall)
        r["score"] = C.score(c, r)
        r["case_obs"] = c["obs"]
    except Exception as exc:  # record the failure, keep the batch going
        r = {"id": cid, "factors": fac, "error": repr(exc), "traceback": traceback.format_exc()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(r, indent=1, default=str))
    os.replace(tmp, path)
    return cid, ("error" if "error" in r else "ok"), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--only", type=str, default=None, help="comma-separated case ids")
    ap.add_argument("--out", type=str, default=str(HERE.parent.parent / "runs" / "calibration_grid"))
    ap.add_argument("--max-wall", type=float, default=5400.0, help="wall-time cap per run [s]; capped runs are flagged")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    runs = plan(only)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    todo = [(cid, fac, out, a.max_wall) for cid, fac in runs if not (out / run_name(cid, fac)).exists()]
    by_case = {}
    for cid, _ in runs:
        by_case[cid] = by_case.get(cid, 0) + 1
    print(f"plan: {len(runs)} runs over {len(by_case)} cases {by_case}; {len(todo)} still to do; workers {a.workers}")
    if a.list or not todo:
        return
    t0 = time.time(); done = 0
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.workers, maxtasksperchild=4) as pool:
        for cid, status, wall in pool.imap_unordered(worker, todo):
            done += 1
            el = time.time() - t0
            eta = el / done * (len(todo) - done)
            print(f"[{done}/{len(todo)}] {cid:11s} {status:5s} {wall/60:6.1f} min   elapsed {el/3600:5.2f} h   eta {eta/3600:5.2f} h", flush=True)


if __name__ == "__main__":
    main()
