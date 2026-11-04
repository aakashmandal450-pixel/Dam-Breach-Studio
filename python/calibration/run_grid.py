"""Calibration batch runner (stage 3): runs every calibration case over the pre-registered factor grid.

Usage (from the python folder, in PowerShell):
    python -u calibration\\run_grid.py --workers 6
    python -u calibration\\run_grid.py --workers 6 --only WalshS1,WalshS3      # subset
    python -u calibration\\run_grid.py --list                                   # show the run plan only
    python -u calibration\\run_grid.py --rerun-capped --list                    # amendment-1 re-run set (dry run)
    python -u calibration\\run_grid.py --rerun-capped --workers 7               # re-run it (post-peak stop, CPU budget)
Results: one JSON per run in ..\\runs\\calibration_grid\\ (re-running skips finished runs, so it can be stopped and resumed).
Validation cases are never run here.
"""
from __future__ import annotations

import os as _os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")   # one thread per worker (PROTOCOL_AMENDMENT_1 s.7); inherited by spawned workers

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
    cid, fac, out, opts = args
    path = out / run_name(cid, fac)
    if path.exists():
        return cid, "skip", 0.0
    import cases as C
    t0 = time.time()
    live = out / "_live"; live.mkdir(exist_ok=True)
    lf = live / (path.stem + ".txt")

    def cb(p):
        try:
            lf.write_text(json.dumps({"case": cid, "factors": fac, **p}))
        except OSError:
            pass
    cb({"t": 0.0, "t_end": 1.0, "Q": 0.0, "level": 0.0, "lowering": 0.0, "wall": 0.0, "accelerated": False})
    try:
        c = C.load_case(cid)
        o = dict(opts)
        ck_every = o.pop("checkpoint_every_cpu_s", None)
        if ck_every:
            o["checkpoint_dir"] = str(out / "_ckpt" / path.stem)
            o["checkpoint_every_cpu_s"] = ck_every
        r = C.run(c, fac, chunk_s=60.0, progress_cb=cb, **o)
        r["score"] = C.score(c, r)
        r["case_obs"] = c["obs"]
        if r.get("stop_cause") in ("wall_safety", "unknown"):
            r["error"] = f"stopped by {r['stop_cause']}"
    except Exception as exc:  # record the failure, keep the batch going
        r = {"id": cid, "factors": fac, "error": repr(exc), "traceback": traceback.format_exc()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(r, indent=1, default=str))
    os.replace(tmp, path)
    ckd = out / "_ckpt" / path.stem
    if ckd.exists() and "error" not in r:   # result written: the checkpoint is no longer needed
        import shutil
        shutil.rmtree(ckd, ignore_errors=True)
    try:
        lf.unlink()
    except OSError:
        pass
    return cid, ("error" if "error" in r else "ok"), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--only", type=str, default=None, help="comma-separated case ids")
    ap.add_argument("--out", type=str, default=str(HERE.parent.parent / "runs" / "calibration_grid"))
    ap.add_argument("--max-wall", type=float, default=5400.0,
                    help="original wall-clock cap per run [s] (counts sleep); ignored when --max-cpu is given")
    ap.add_argument("--max-cpu", type=float, default=None, help="CPU-time budget per run [s] (amendment 1: 28800)")
    ap.add_argument("--wall-safety", type=float, default=86400.0, help="hang guard with --max-cpu [s]; such runs are errors")
    ap.add_argument("--post-peak", action="store_true", help="stop breached runs after post-peak quiescence (amendment 1)")
    ap.add_argument("--checkpoint-every", type=float, default=None,
                    help="save a restart point every N s of CPU time per run (default 1800 with --rerun-capped); "
                         "an interrupted batch resumes runs from their last checkpoint")
    ap.add_argument("--rerun-capped", action="store_true",
                    help="amendment-1 re-run: select runs whose result is capped/censored or an error, move the old files "
                         "to _capped_v1/, and re-run them with --post-peak and --max-cpu 28800 unless given otherwise")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--heartbeat", type=float, default=60.0, help="seconds between status blocks")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    runs = plan(only)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.rerun_capped:
        a.post_peak = True
        if a.max_cpu is None:
            a.max_cpu = 28800.0
        if a.checkpoint_every is None:
            a.checkpoint_every = 1800.0
        sel = []
        for cid, fac in runs:
            f = out / run_name(cid, fac)
            if not f.exists():
                continue
            try:
                r0 = json.loads(f.read_text())
            except ValueError:
                sel.append((cid, fac)); continue
            if r0.get("runner"):          # already produced by the amendment-1 runner: keep it
                continue
            if r0.get("capped") or r0.get("censored") or "error" in r0:
                sel.append((cid, fac))
        print(f"amendment-1 re-run set: {len(sel)} runs " +
              str({c: sum(1 for x, _ in sel if x == c) for c in sorted({x for x, _ in sel})}))
        if not a.list:
            arch = out / "_capped_v1"; arch.mkdir(exist_ok=True)
            for cid, fac in sel:
                src = out / run_name(cid, fac)
                if not (arch / src.name).exists():
                    os.replace(src, arch / src.name)
                else:
                    src.unlink()
    if a.max_cpu is not None:
        opts = {"max_cpu_seconds": a.max_cpu, "max_wall_safety_seconds": a.wall_safety, "post_peak_stop": a.post_peak,
                "checkpoint_every_cpu_s": a.checkpoint_every}
    else:
        opts = {"max_wall_seconds": a.max_wall, "post_peak_stop": a.post_peak}
    print(f"runner options: {opts}; threads per worker: OMP={os.environ.get('OMP_NUM_THREADS')}")
    todo = [(cid, fac, out, opts) for cid, fac in runs if not (out / run_name(cid, fac)).exists()]
    by_case = {}
    for cid, _ in runs:
        by_case[cid] = by_case.get(cid, 0) + 1
    print(f"plan: {len(runs)} runs over {len(by_case)} cases {by_case}; {len(todo)} still to do; workers {a.workers}")
    if a.list or not todo:
        return
    t0 = time.time(); done = 0
    live = out / "_live"; live.mkdir(exist_ok=True)
    for f in live.glob("*.txt"):          # leftovers from an interrupted batch
        f.unlink()
    ctx = mp.get_context("spawn")
    print(f"started {time.strftime('%H:%M:%S')}. A status block of the runs in progress prints every {a.heartbeat:.0f} s; "
          f"a line prints whenever a run finishes. Ctrl+C stops; re-running resumes.", flush=True)
    with ctx.Pool(a.workers, maxtasksperchild=4) as pool:
        it = pool.imap_unordered(worker, todo)
        while done < len(todo):
            try:
                cid, status, wall = it.next(timeout=a.heartbeat)
            except mp.TimeoutError:
                el = time.time() - t0
                rows = []
                for f in sorted(live.glob("*.txt")):
                    try:
                        p = json.loads(f.read_text())
                    except (OSError, ValueError):
                        continue
                    fac = p["factors"]
                    rows.append(f"    {p['case']:11s} f_kd={fac['f_kd']:<7.3g} C_h={fac['C_h']:<7.3g} f_t={fac['f_t']:<7.3g} "
                                f"{100 * p['t'] / max(p['t_end'], 1e-9):5.1f} % of {p['t_end']:.0f} s   Q={p['Q']:9.3g} m3/s   "
                                f"max lowering={p['lowering']:6.3f} m   running {p['wall'] / 60:5.1f} min"
                                + ("   [accelerated initiation]" if p.get("accelerated") else ""))
                print(f"--- {time.strftime('%H:%M:%S')}  still running: {len(rows)} runs, {done}/{len(todo)} finished, "
                      f"elapsed {el / 3600:.2f} h", flush=True)
                for r_ in rows:
                    print(r_, flush=True)
                continue
            done += 1
            el = time.time() - t0
            eta = el / done * (len(todo) - done)
            print(f"[{done}/{len(todo)}] {time.strftime('%H:%M:%S')} {cid:11s} {status:5s} {wall/60:6.1f} min   "
                  f"elapsed {el/3600:5.2f} h   eta {eta/3600:5.2f} h", flush=True)
    print(f"all done in {(time.time() - t0) / 3600:.2f} h. Next: python calibration\\fit.py", flush=True)


if __name__ == "__main__":
    main()
