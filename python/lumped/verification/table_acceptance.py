"""Acceptance test of the stability table (Theory Part 5, §5.5b, (5.16a)).

A. Table mechanics (fast): grid nodes reproduce the stored values; every axis below/above its range,
   and gamma_w b_p/c_u0 outside [0, 2], raises TableRangeError naming the parameter; an incomplete
   table is refused.
B. Accuracy (direct solves): at off-grid points (interpolation error) and at grid nodes far from the
   reference water weight (support-factor error), the table prediction of each bound is compared with
   a direct fela_v2 solve, for collapse and blow-out, single pressure and full pipe at
   gamma_w b_p/c_u0 = 0.2, 1.0 and 2.0.
   Criterion (project-specific acceptance criterion chosen for this model, not a published standard):
       |prediction - direct| <= 0.5 * (direct upper - direct lower) for each bound.
   Where it fails, the report says whether the reduced 4-D form (support factor) or the interpolation
   is at fault, i.e. where the fifth dimension must be kept or the grid refined.
Passing verifies the numerical approximation of the stability bounds only; it does not validate the
physical piping model.
Usage: python table_acceptance.py --table stability_table.csv --out acceptance.csv [--workers N]
"""
import argparse, csv, os, sys, time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))          # .../python
from lumped.stability_table import StabilityTable, TableRangeError, AXES, FIELDS   # noqa: E402

OFF_GRID = [(0.35, 0.7, 0.25, 0.1), (0.7, 1.4, 1.25, 0.4), (1.75, 0.7, 2.5, 0.75), (2.5, 1.4, 0.75, 0.1),
            (5.0, 0.7, 1.75, 0.4), (7.0, 1.4, 2.5, 0.75), (10.0, 0.7, 0.25, 0.1), (14.0, 1.4, 1.25, 0.4),
            (20.0, 0.7, 2.5, 0.75), (28.0, 1.4, 0.75, 0.1)]
ON_GRID = [(0.25, 0.5, 0.0, 0.0), (32.0, 2.0, 3.0, 0.0), (32.0, 0.5, 0.5, 1.0), (0.25, 2.0, 3.0, 1.0),
           (8.0, 2.0, 2.0, 0.0), (4.0, 1.0, 1.0, 0.25)]
GWS = (0.2, 1.0, 2.0)
H = 0.1


def direct(p):
    import fela_v2 as f
    C, a, g, r = p
    m = f.rect_mesh(C, a, H, hfar=max(1.0, (C + a) / 8))
    out = []
    for gw in (None,) + GWS:
        pr = f.no_pressure if gw is None else f.hydrostatic(gw, -C)
        for mech, passive in (("collapse", False), ("blowout", True)):
            lb = f.lower_bound(m, g, r, pr, passive=passive)
            ub = f.upper_bound(m, g, r, pr, passive=passive)
            lo, hi = (ub["value"], lb["value"]) if passive else (lb["value"], ub["value"])
            out.append(dict(C_b=C, a_b=a, g_b=g, rho_b=r, gw_b=0.0 if gw is None else gw,
                            full=gw is not None, mechanism=mech, lo=lo, hi=hi))
    return out


def mechanics(tab, fails):
    print("== A. Table mechanics", flush=True)
    ok = True
    for i in range(len(tab.grid["C_b"])):
        for j in range(len(tab.grid["a_b"])):
            q = {a: tab.grid[a][k] for a, k in zip(AXES, (i, j, len(tab.grid["g_b"]) // 2, len(tab.grid["rho_b"]) - 1))}
            idx = (i, j, len(tab.grid["g_b"]) // 2, len(tab.grid["rho_b"]) - 1)
            for fld in FIELDS:
                if abs(tab._interp(fld, q) - tab.data[fld][idx]) > 1e-12:
                    ok = False
    print(f"  {'PASS' if ok else 'FAIL'}  grid nodes reproduce stored values (all fields, C/b x a/b slice)", flush=True)
    if not ok: fails.append("node reproduction")
    base = {a: float(tab.grid[a][len(tab.grid[a]) // 2]) for a in AXES}
    for a in AXES:
        for v, side in ((tab.grid[a][0] * (0.5 if a in ("C_b", "a_b") else 1) - (0 if a in ("C_b", "a_b") else 0.5), "below"),
                        (tab.grid[a][-1] * 1.5 + 0.1, "above")):
            q = dict(base); q[a] = v
            try:
                tab.query(**q); res = False; msg = "no error"
            except TableRangeError as e:
                res = a in str(e); msg = str(e)
            print(f"  {'PASS' if res else 'FAIL'}  {a} {side} range raises an error naming it   ({msg})", flush=True)
            if not res: fails.append(f"range {a} {side}")
    for gw in (-0.1, 2.5):
        try:
            tab.query(**base, gw_b=gw, full=True); res = False; msg = "no error"
        except TableRangeError as e:
            res = "gw_b" in str(e); msg = str(e)
        print(f"  {'PASS' if res else 'FAIL'}  gw_b = {gw} raises an error   ({msg})", flush=True)
        if not res: fails.append(f"range gw {gw}")
    r = tab.query(**base)
    ok = abs(r["mid"] - 0.5 * (r["lo"] + r["hi"])) < 1e-15 and r["lo"] <= r["hi"]
    print(f"  {'PASS' if ok else 'FAIL'}  both bounds and the midpoint returned (lo <= mid <= hi)", flush=True)
    if not ok: fails.append("bounds/midpoint")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="stability_table.csv")
    ap.add_argument("--out", default="table_acceptance.csv")
    ap.add_argument("--workers", type=int, default=0)
    args = ap.parse_args()
    if args.workers <= 0:
        args.workers = max(1, min((os.cpu_count() or 2) - 1, 6))
    fails = []
    tab = StabilityTable.from_csv(args.table)
    mechanics(tab, fails)
    print("== B. Accuracy against direct solves (criterion: error <= half the bracket width)", flush=True)
    def inside(p):
        return all(tab.grid[a][0] <= v <= tab.grid[a][-1] for a, v in zip(AXES, p))
    pts = [p for p in ON_GRID + OFF_GRID if inside(p)]
    skipped = len(ON_GRID) + len(OFF_GRID) - len(pts)
    if skipped:
        print(f"  note: {skipped} test point(s) lie outside this table's grid and are skipped", flush=True)
    if not pts:   # a small table (e.g. the 'tiny' build): test the centre of each grid cell along the C axis
        mid = lambda a: float(sum(tab.grid[a][:2]) / 2) if len(tab.grid[a]) > 1 else float(tab.grid[a][0])
        pts = [tuple(mid(a) for a in AXES)]
        ON_GRID.append(tuple(float(tab.grid[a][0]) for a in AXES)); pts.append(ON_GRID[-1])
    rows, n_ok, n_bad, t0 = [], 0, 0, time.time()
    with Pool(args.workers) as pool:
        for k, res in enumerate(pool.imap_unordered(direct, pts), 1):
            for d in res:
                q = {a: d[a] for a in AXES}
                try:
                    pr = tab.query(**q, gw_b=d["gw_b"], full=d["full"], mechanism=d["mechanism"])
                except TableRangeError as e:
                    print(f"  FAIL  {q}: {e}", flush=True); fails.append(str(e)); continue
                tol = 0.5 * (d["hi"] - d["lo"])
                e_lo, e_hi = abs(pr["lo"] - d["lo"]), abs(pr["hi"] - d["hi"])
                ok = e_lo <= tol and e_hi <= tol
                ongrid = (d["C_b"], d["a_b"], d["g_b"], d["rho_b"]) in ON_GRID
                cause = "" if ok else ("support factor (reduced 4-D form): keep the fifth dimension here"
                                       if (ongrid and d["full"]) else "interpolation: refine the grid here")
                n_ok += ok; n_bad += (not ok)
                rows.append(dict(d, pred_lo=pr["lo"], pred_hi=pr["hi"], err_lo=e_lo, err_hi=e_hi, tol=tol,
                                 ok=ok, on_grid=ongrid, cause=cause))
                if not ok:
                    fails.append(f"{q} {d['mechanism']} full={d['full']} gw={d['gw_b']}")
            p = res[0]
            print(f"[{k}/{len(pts)}] C/b={p['C_b']:g} a/b={p['a_b']:g} gb/c={p['g_b']:g} rho b/c={p['rho_b']:g}: "
                  f"{sum(r_['ok'] for r_ in rows[-8:])}/8 comparisons pass | elapsed {(time.time()-t0)/60:.1f} min",
                  flush=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nAccuracy: {n_ok} of {n_ok + n_bad} comparisons within the criterion.", flush=True)
    for r_ in rows:
        if not r_["ok"]:
            print(f"  outside: C/b={r_['C_b']:g} a/b={r_['a_b']:g} gb/c={r_['g_b']:g} rho={r_['rho_b']:g} "
                  f"{r_['mechanism']} gw={r_['gw_b']:g}: err lo {r_['err_lo']:.3f}, hi {r_['err_hi']:.3f}, "
                  f"tol {r_['tol']:.3f} -> {r_['cause']}", flush=True)
    worst = max(rows, key=lambda r_: max(r_["err_lo"], r_["err_hi"]) / max(r_["tol"], 1e-12))
    print(f"Largest error / tolerance: {max(worst['err_lo'], worst['err_hi']) / max(worst['tol'], 1e-12):.2f} "
          f"at C/b={worst['C_b']:g} a/b={worst['a_b']:g} {worst['mechanism']} gw={worst['gw_b']:g}", flush=True)
    print(f"\n== RESULT: {'ALL PASS' if not fails else str(len(fails)) + ' FAIL'}", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
