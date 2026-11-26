"""Phase B first gates (Part 6 Appendix 6A): B1, B2, B3, B9, B12a, B12b, B12c, B13.

Usage (from the python folder):
    python -B -u -m onedim.verification.run_phase_b [--quick] [--workers N]
Every case is an independent job; jobs run in parallel on all CPU cores (or N workers), the
slowest first. One line is printed per case as it finishes, then a PASS/FAIL table.
The solver uses (6.14a) at width changes (decision 6-19, "discharge_width"). B12a is also run with
the original velocity reconstruction (6.14) ("velocity") as a diagnostic only, for comparison with the
2026-11-26 baseline. Status words: PASS/FAIL are gates; KNOWN is a failed target accepted as a known
limitation (decision 6-20); INFO is a reported diagnostic. RESULT counts gates only.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from . import riemann as R
from . import junctions as J

RECONS = ("discharge_width", "velocity")     # the first is the solver default and is gated
GATED = "discharge_width"


def _arg(name, default):
    if name in sys.argv:
        return int(sys.argv[sys.argv.index(name) + 1])
    return default


# ------------------------------------------------------------------ job functions (top level: picklable)
def job_b1(steps):
    return R.b1_lake_at_rest(steps=steps)


def job_b2(N):
    return R.b2_ritter(N)


def job_b3(N):
    return R.b3_stoker(N)


def job_b9():
    return R.b9_two_rarefactions()


def job_b13():
    return R.b13_cases()


def job_b12b(kind, N):
    return J.b12b_case(kind, N)


def job_b12a(i, d, recon):
    name, a, b, kind, Q, h1 = J.b12a_specs()[i]
    return J.b12a_one(name, a, b, kind, Q, h1, d, recon)


def job_b12c(i, k, d, recon):
    name, a, b = J.b12c_specs()[i]
    return J.b12c_one(name, a, b, k, d, recon)


def job_b12c_ref(i, ds):
    return J.b12c_refine_one(i, ds)


def job_b12d(outlet, d):
    return J.b12d_one(outlet, d)


def build_jobs(quick):
    Ns = (400, 800, 1600) if quick else (400, 800, 1600, 3200)
    Nb = (10, 20, 40) if quick else (10, 20, 40, 80)
    spreads = (5, 20) if quick else (5, 10, 20, 50)
    jobs = []                                     # (cost estimate, key, fn, args)
    for k in spreads:
        for i in range(len(J.b12c_specs())):
            for d in (+1, -1):
                jobs.append((30 + k, ("B12c", GATED, i, k, d), job_b12c, (i, k, d, GATED)))
    for i in range(len(J.b12c_refine_specs())):
        for ds in (0.25, 0.125, 0.0625):
            jobs.append((20 / ds, ("B12cR", i, ds), job_b12c_ref, (i, ds)))
    for outlet in ("submerged", "free"):
        for d in (+1, -1):
            jobs.append((300, ("B12d", outlet, d), job_b12d, (outlet, d)))
    for recon in RECONS:
        for i in range(len(J.b12a_specs())):
            for d in (+1, -1):
                jobs.append((40 if i == 8 else 25, ("B12a", recon, i, d), job_b12a, (i, d, recon)))
    for kind in ("rect", "trap"):
        for N in Nb:
            jobs.append((N / 4, ("B12b", kind, N), job_b12b, (kind, N)))
    jobs.append((60 if not quick else 8, ("B1",), job_b1, (10_000 if quick else 100_000,)))
    for N in Ns:
        jobs.append((N / 400, ("B2", N), job_b2, (N,)))
        jobs.append((N / 400, ("B3", N), job_b3, (N,)))
    jobs.append((2, ("B9",), job_b9, ()))
    jobs.append((5, ("B13",), job_b13, ()))
    jobs.sort(key=lambda j: -j[0])                # longest first: better load balance
    return jobs, Ns, Nb, spreads


def describe(key, r):
    t = key[0]
    if t == "B1":
        return f"max|U|={r['max_U']:.1e} max|deta|={r['max_deta']:.1e} steps={r['steps']}"
    if t == "B2":
        return f"N={key[1]} L1h={r['L1_h']:.4f} front err={100 * r['front_err']:.2f}%"
    if t == "B3":
        return f"N={key[1]} shock {100 * r['shock_err']:.2f}% hm {100 * r['hm_err']:.3f}%"
    if t == "B9":
        return f"min A={r['min_area']:.4f} NaN={r['nan']}"
    if t == "B13":
        return ", ".join(f"{k} bounded={v['bounded']}" for k, v in r.items())
    if t == "B12b":
        return f"{key[1]} N={key[2]} Q/Qc-1={r['err']:+.2e} Fr_brink={r['Fr_brink']:.4f}"
    if t == "B12a":
        b = f" Borda {100 * r['err_borda']:+.1f}%" if "borda" in r else ""
        return (f"[{r['recon']}] {r['case']} {r['direction']} loss={r['loss']:.4f} "
                f"relation={r['loss_rel']:.4f} ({100 * r['err_rel']:+.1f}%){b}")
    if t == "B12cR":
        return (f"{r['case']} ds={r['ds']} ({r['cells']} cells) loss={r['loss']:.5f} "
                f"max cell gain={r['max_gain_flux']:.1e} conv={r['converged']}")
    if t == "B12d":
        if r["outlet"] == "submerged":
            return (f"{r['outlet']} {r['direction']} conv={r['converged']} t={r['t']:.0f} loss={r['loss']:.4f} "
                    f"relation={r['loss_rel']:.4f} ({100 * r['err_rel']:+.0f}%) Borda {100 * r['err_borda']:+.0f}%")
        return (f"{r['outlet']} {r['direction']} conv={r['converged']} t={r['t']:.0f} outlet Q={r['outlet_flux']:.5f} "
                f"range(last 10 x 100 s)={r['flux_range_last_10']:.1e}")
    if t == "B12c":
        return (f"[{r['recon']}] {r['case']} k={r['spread']} {r['direction']} loss={r['loss']:.4f} "
                f"max cell gain={r['max_gain_flux']:.1e}")
    return str(r)


# ------------------------------------------------------------------ gates
def gates(res, Ns, Nb, spreads):
    out = []

    def gate(name, ok, detail="", kind="gate"):
        if kind == "gate":
            st = "PASS" if ok else "FAIL"
        elif kind == "known":
            st = "PASS" if ok else "KNOWN"
        else:
            st = "INFO"
        out.append((name, st, detail))

    r = res.get(("B1",))
    if r:
        gate("B1 lake at rest", r["max_U"] < 1e-12 and r["max_deta"] < 1e-12 and r["dry_cells_stay_dry"],
             f"steps={r['steps']} max|U|={r['max_U']:.1e} max|deta|={r['max_deta']:.1e} water err={r['water_err']:.1e}")
    b2 = [res[("B2", N)] for N in Ns if ("B2", N) in res]
    if len(b2) == len(Ns):
        p = np.log2(b2[-2]["L1_h"] / b2[-1]["L1_h"])
        gate("B2 Ritter: L1(h) decreasing", all(a["L1_h"] > b["L1_h"] for a, b in zip(b2, b2[1:])),
             f"observed order (last pair) {p:.2f}")
        gate("B2 Ritter: exact front within 1% at finest (6-20)", abs(b2[-1]["front_err"]) < 0.01,
             "front error " + ", ".join(f"{100 * x['front_err']:.2f}%" for x in b2) + " (wet threshold 1e-6 m)",
             kind="known")
        th = [x["front_th_err"] for x in b2]
        gate("B2 Ritter: same-threshold front error falls with refinement (6-20)",
             all(abs(p_) > abs(q_) for p_, q_ in zip(th, th[1:])),
             "h_th = 1e-3 m: " + ", ".join(f"{100 * e:.2f}%" for e in th))
    b3 = [res[("B3", N)] for N in Ns if ("B3", N) in res]
    if len(b3) == len(Ns):
        f = b3[-1]
        gate("B3 Stoker", abs(f["shock_err"]) < 0.01 and abs(f["hm_err"]) < 0.01 and abs(f["um_err"]) < 0.01,
             f"finest: shock {100 * f['shock_err']:.2f}%, hm {100 * f['hm_err']:.3f}%, um {100 * f['um_err']:.3f}%")
    r = res.get(("B9",))
    if r:
        gate("B9 positivity", r["min_area"] >= 0 and not r["nan"] and r["water_err"] < 1e-12,
             f"min A={r['min_area']:.4f}; centre h={r['h_centre']:.4f} vs exact {r['h_star']:.4f} (reported)")
    r = res.get(("B13",))
    if r:
        gate("B13 passive scalar bounded, solids exact",
             all(v["bounded"] and v["solids_err"] < 1e-12 for v in r.values()),
             "sub-case (e) not run: no solids sources in phase B")
    for kind in ("rect", "trap"):
        rs = [res[("B12b", kind, N)] for N in Nb if ("B12b", kind, N) in res]
        if len(rs) == len(Nb):
            dec = all(abs(a["err"]) >= abs(b["err"]) for a, b in zip(rs, rs[1:]))
            gate(f"B12b free overfall [{kind}]", all(abs(x["err"]) < 0.01 for x in rs) and dec,
                 "errors " + ", ".join("%+.1e" % x["err"] for x in rs) + f"; decreasing={dec}")
    for recon in RECONS:
        a = [v for k, v in res.items() if k[0] == "B12a" and k[1] == recon]
        kd = "gate" if recon == GATED else "info"
        if a:
            exp = [x for x in a if x["kind"] == "exp" and not x["case"].startswith("conduit")]
            con = [x for x in a if x["kind"] == "con"]
            cnd = [x for x in a if x["case"].startswith("conduit")]
            gate(f"B12a[{recon}] expansions vs relation (1%)", all(abs(x["err_rel"]) < 0.01 for x in exp),
                 f"max err {100 * max(abs(x['err_rel']) for x in exp):.1f}%", kind=kd)
            gate(f"B12a[{recon}] expansions vs Borda (3%)", all(abs(x["err_borda"]) < 0.03 for x in exp),
                 f"max err {100 * max(abs(x['err_borda']) for x in exp):.1f}%", kind=kd)
            gate(f"B12a[{recon}] contractions vs relation (1%)", all(abs(x["err_rel"]) < 0.01 for x in con),
                 ", ".join(f"{x['case']} {100 * x['err_rel']:+.0f}%" for x in con if x["direction"] == "L->R")
                 + " (6-16 open: relation is not a validated contraction reference)", kind=kd)
            gate(f"B12a[{recon}] conduit->open vs relation (1%)", all(abs(x["err_rel"]) < 0.01 for x in cnd),
                 ", ".join(f"{x['direction']} {100 * x['err_rel']:+.0f}% conv={x['converged']}" for x in cnd), kind=kd)
            gate(f"B12a[{recon}] no net energy gain at any junction", all(x["loss"] > 0 for x in a), kind=kd)
        c = [v for k, v in res.items() if k[0] == "B12c" and k[1] == recon]
        if c:
            gain = max(x["max_gain_flux"] for x in c)
            gate(f"B12c[{recon}] strict: no energy gain in any cell (1e-6 m)", gain < 1e-6,
                 f"max cell gain {gain:.1e} m (diagnostic, 6-21)", kind="info")
            falling = True
            for case in sorted({x["case"] for x in c}):
                L = [x["loss"] for x in sorted(c, key=lambda y: y["spread"])
                     if x["case"] == case and x["direction"] == "L->R"]
                falling &= all(p >= q for p, q in zip(L, L[1:]))
            gate(f"B12c[{recon}] loss falls as the change is spread", falling, "(diagnostic, 6-21)", kind="info")
    # B12c refinement gate (6-21)
    names = [n for n, _, _ in J.b12c_refine_specs()]
    for i, nm in enumerate(names):
        rs = [res.get(("B12cR", i, ds)) for ds in (0.25, 0.125, 0.0625)]
        if all(rs):
            g = [x["max_gain_flux"] for x in rs]; L = [x["loss"] for x in rs]
            gate(f"B12c refine {nm}: (1) max local gain falls with refinement", g[0] > g[1] > g[2],
                 ", ".join(f"{v:.1e}" for v in g) + " m")
            gate(f"B12c refine {nm}: (2) no persistent gain (finest <= 0.5 x coarsest)", g[2] <= 0.5 * g[0])
            gate(f"B12c refine {nm}: (3) net head change is a loss at every grid", all(v > 0 for v in L),
                 ", ".join(f"{v:.5f}" for v in L) + " m")
            gate(f"B12c refine {nm}: (4) total loss converges", abs(L[2] - L[1]) < abs(L[1] - L[0]),
                 f"differences {abs(L[1] - L[0]):.1e}, {abs(L[2] - L[1]):.1e} m")
    d = [v for k, v in res.items() if k[0] == "B12d"]
    if d:
        gate("B12d conduit outlet: steady state reached", all(x["converged"] for x in d),
             ", ".join(f"{x['outlet']} {x['direction']} {x['converged']}" for x in d))
        sub = [x for x in d if x["outlet"] == "submerged"]
        if sub:
            gate("B12d submerged outlet: head change vs relation and Borda", True,
                 ", ".join(f"{x['direction']} rel {100 * x['err_rel']:+.0f}% Borda {100 * x['err_borda']:+.0f}%" for x in sub),
                 kind="info")
    return out


def main():
    quick = "--quick" in sys.argv
    workers = _arg("--workers", os.cpu_count() or 1)
    jobs, Ns, Nb, spreads = build_jobs(quick)
    T0 = time.time()
    print(f"Phase B first gates {'(quick)' if quick else '(full)'}: {len(jobs)} cases on {workers} workers", flush=True)
    res, errors = {}, []
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, *args): key for _, key, fn, args in jobs}
        for f in as_completed(futs):
            key = futs[f]; done += 1
            try:
                res[key] = f.result()
                print(f"[{time.time() - T0:7.1f} s] {done:3d}/{len(jobs)} {key[0]:5s} {describe(key, res[key])}", flush=True)
            except Exception as e:
                errors.append((key, repr(e)))
                print(f"[{time.time() - T0:7.1f} s] {done:3d}/{len(jobs)} ERROR {key}: {e!r}", flush=True)
    summary = gates(res, Ns, Nb, spreads)
    for key, e in errors:
        summary.append((f"{key}", "FAIL", f"ERROR {e}"))
    print("\n================ SUMMARY ================", flush=True)
    for name, st, d in summary:
        print(f"{st:5s} {name}  {d}")
    n_pass = sum(st == "PASS" for _, st, _ in summary)
    n_fail = sum(st == "FAIL" for _, st, _ in summary)
    n_known = sum(st == "KNOWN" for _, st, _ in summary)
    print(f"\nRESULT: {n_pass} pass, {n_fail} fail, {n_known} known limitation  ({time.time() - T0:.0f} s)")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
