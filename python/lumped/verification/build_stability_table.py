"""Build the pipe-roof stability table (Theory Part 5, §5.5b, (5.16a)).

For every grid point (C/b_p, a_p/b_p, gamma b_p/c_u0, rho b_p/c_u0), eight bound solves with fela_v2:
  collapse, single pressure:         static lower bound, kinematic upper bound   -> N_c0_lo, N_c0_hi
  blow-out, single pressure:         kinematic (lower end), static (upper end)   -> N_b0_lo, N_b0_hi
  the same two with the full-pipe hydrostatic profile at gw_ref = gamma_w b_p/c_u0 -> beta_* per bound
Every solve is audited (equilibrium, tractions, yield; incompressibility, recomputed bound); a point
whose audit exceeds AUD_TOL is written with status FAIL and reported.

Resumable: rows already in the output CSV are skipped. Runs points in parallel.
Usage:  python build_stability_table.py --grid full|pilot|tiny --out stability_table.csv [--workers N]
"""
import argparse, csv, itertools, os, sys, threading, time
from multiprocessing import Pool

GRIDS = {
    "full":  dict(C_b=[0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32], a_b=[0.5, 1, 2],
                  g_b=[0, 0.5, 1, 1.5, 2, 3], rho_b=[0, 0.25, 0.5, 1]),
    "pilot": dict(C_b=[0.5, 2, 8, 32], a_b=[0.5, 2], g_b=[0, 2], rho_b=[0, 1]),
    "tiny":  dict(C_b=[0.5, 1], a_b=[1], g_b=[1], rho_b=[0, 0.5]),
}
GW_REF = 0.5
AUD_TOL = 1e-5
H = 0.1
COLS = ["C_b", "a_b", "g_b", "rho_b", "N_c0_lo", "N_c0_hi", "N_b0_lo", "N_b0_hi",
        "beta_c_lo", "beta_c_hi", "beta_b_lo", "beta_b_hi", "N_cf_lo", "N_cf_hi", "N_bf_lo", "N_bf_hi",
        "ntri", "audit", "status", "seconds"]


def audit(lb, ub):
    a, b = lb["audit"], ub["audit"]
    return max(a["equilibrium"], a["traction_and_bc"], a["yield_excess"], a.get("side_excess", 0),
               a.get("bottom_excess", 0), b["incompressibility"], b["far_bc"],
               abs(b["recomputed"] - b["objective"]) / max(1.0, abs(b["objective"])))


def solve_point(p):
    try:
        return _solve_point(p)
    except MemoryError:
        import gc; gc.collect()
        C, a, g, r = p
        return dict(C_b=C, a_b=a, g_b=g, rho_b=r, status="MEMORY", seconds=0)


def _solve_point(p):
    import fela_v2 as f
    C, a, g, r = p
    t0 = time.time()
    m = f.rect_mesh(C, a, H, hfar=max(1.0, (C + a) / 8))
    full = f.hydrostatic(GW_REF, -C)
    res, aud = {}, 0.0
    for key, pr, passive in [("c0", f.no_pressure, False), ("b0", f.no_pressure, True),
                             ("cf", full, False), ("bf", full, True)]:
        lb = f.lower_bound(m, g, r, pr, passive=passive)
        ub = f.upper_bound(m, g, r, pr, passive=passive)
        aud = max(aud, audit(lb, ub))
        if passive:   # bracket [kinematic, static]
            res[key] = (ub["value"], lb["value"])
        else:         # bracket [static, kinematic]
            res[key] = (lb["value"], ub["value"])
    inc = GW_REF * a
    row = dict(C_b=C, a_b=a, g_b=g, rho_b=r,
               N_c0_lo=res["c0"][0], N_c0_hi=res["c0"][1], N_b0_lo=res["b0"][0], N_b0_hi=res["b0"][1],
               beta_c_lo=(res["cf"][0] - res["c0"][0]) / inc, beta_c_hi=(res["cf"][1] - res["c0"][1]) / inc,
               beta_b_lo=(res["bf"][0] - res["b0"][0]) / inc, beta_b_hi=(res["bf"][1] - res["b0"][1]) / inc,
               N_cf_lo=res["cf"][0], N_cf_hi=res["cf"][1], N_bf_lo=res["bf"][0], N_bf_hi=res["bf"][1],
               ntri=len(m.T), audit=aud, status="OK" if aud <= AUD_TOL else "FAIL",
               seconds=round(time.time() - t0, 1))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="full", choices=GRIDS)
    ap.add_argument("--out", default="stability_table.csv")
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()
    from memsafe import choose_workers
    args.workers, note = choose_workers(args.workers)
    print("Workers: " + note, flush=True)
    G = GRIDS[args.grid]
    pts = list(itertools.product(G["C_b"], G["a_b"], G["g_b"], G["rho_b"]))
    # deep points first is worse for the ETA; interleave so the estimate settles early
    pts.sort(key=lambda p: (p[0] * p[1]) % 7)
    done = set()
    if os.path.exists(args.out):
        with open(args.out, newline="") as fh:
            for r in csv.DictReader(l for l in fh if not l.startswith("#")):
                if r.get("status") == "OK":
                    done.add((float(r["C_b"]), float(r["a_b"]), float(r["g_b"]), float(r["rho_b"])))
    todo = [p for p in pts if tuple(map(float, p)) not in done]
    print(f"Stability table '{args.grid}': {len(pts)} grid points, {len(done)} already done, "
          f"{len(todo)} to solve, {args.workers} workers, 8 bound solves per point.", flush=True)
    new_file = not os.path.exists(args.out)
    with open(args.out, "a", newline="") as fh:
        if new_file:
            fh.write(f"# gw_ref = {GW_REF}\n# mesh_h = {H}\n# grid = {args.grid}\n# built by build_stability_table.py\n")
        w = csv.DictWriter(fh, fieldnames=COLS)
        if new_file:
            w.writeheader()
        t0, nfail = time.time(), 0
        state = {"k": 0, "busy": True}

        def heartbeat():
            while state["busy"]:
                time.sleep(60)
                if state["busy"]:
                    print(f"      ... working: {state['k']}/{len(todo)} points done, "
                          f"elapsed {(time.time() - t0) / 60:.1f} min", flush=True)
        threading.Thread(target=heartbeat, daemon=True).start()
        retry = []

        def report(k, n, row):
            el = time.time() - t0
            eta = el / k * (n - k)
            print(f"[{k}/{n}] C/b={row['C_b']:g} a/b={row['a_b']:g} gb/c={row['g_b']:g} "
                  f"rho b/c={row['rho_b']:g}: N_c [{row['N_c0_lo']:.3f}, {row['N_c0_hi']:.3f}] "
                  f"N_b [{row['N_b0_lo']:.3f}, {row['N_b0_hi']:.3f}] beta_c {row['beta_c_lo']:.3f} "
                  f"audit {row['audit']:.0e} {row['status']} {row['seconds']}s | elapsed {el/60:.1f} min, "
                  f"ETA {eta/60:.1f} min", flush=True)

        # maxtasksperchild=1: each point runs in a fresh process, so its memory is returned to the system
        with Pool(args.workers, maxtasksperchild=1) as pool:
            for k, row in enumerate(pool.imap_unordered(solve_point, todo), 1):
                state["k"] = k
                if row["status"] == "MEMORY":
                    retry.append((row["C_b"], row["a_b"], row["g_b"], row["rho_b"]))
                    print(f"[{k}/{len(todo)}] C/b={row['C_b']:g} a/b={row['a_b']:g} gb/c={row['g_b']:g} "
                          f"rho b/c={row['rho_b']:g}: out of memory, will be retried alone at the end", flush=True)
                    continue
                w.writerow(row); fh.flush()
                nfail += row["status"] != "OK"
                report(k, len(todo), row)
        for k, p in enumerate(retry, 1):          # one at a time, nothing else running
            print(f"Retrying alone ({k}/{len(retry)}): C/b={p[0]:g} a/b={p[1]:g} gb/c={p[2]:g} rho b/c={p[3]:g}", flush=True)
            row = solve_point(p)
            if row["status"] == "MEMORY":
                print("  still out of memory: close other programs and run the same command again", flush=True)
                nfail += 1
                continue
            w.writerow(row); fh.flush()
            nfail += row["status"] != "OK"
            report(k, len(retry), row)
        state["busy"] = False
    print(f"Done. {nfail} point(s) failed the audit or did not finish; run the same command again to retry them." if nfail else "Done. All points solved and audited.", flush=True)
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
