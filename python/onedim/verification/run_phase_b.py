"""Phase B first gates (Part 6 Appendix 6A): B1, B2, B3, B9, B12a, B12b, B12c, B13.

Usage (from the python folder):  python -B -u -m onedim.verification.run_phase_b [--quick]
Prints one line per case as it finishes and a PASS/FAIL table at the end.
B12a and B12c are run twice: with the reconstruction (6.14) as written ("velocity") and with the
experimental discharge-preserving variant ("discharge_width"), which is NOT adopted -- it is run
only to inform the decision.
"""
import sys
import time

import numpy as np

from . import riemann as R
from . import junctions as J

QUICK = "--quick" in sys.argv
summary = []
T0 = time.time()


def say(msg):
    print(f"[{time.time() - T0:7.1f} s] {msg}", flush=True)


def gate(name, ok, detail):
    summary.append((name, ok, detail))
    say(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


def b1():
    r = R.b1_lake_at_rest(steps=10_000 if QUICK else 100_000)
    gate("B1 lake at rest", r["max_U"] < 1e-12 and r["max_deta"] < 1e-12 and r["dry_cells_stay_dry"],
         f"steps={r['steps']} max|U|={r['max_U']:.1e} max|deta|={r['max_deta']:.1e} "
         f"dry stay dry={r['dry_cells_stay_dry']} water err={r['water_err']:.1e}")


def b2():
    Ns = (400, 800, 1600) if QUICK else (400, 800, 1600, 3200)
    rs = []
    for N in Ns:
        r = R.b2_ritter(N); rs.append(r)
        say(f"  B2 N={N}: L1h={r['L1_h']:.4f} L1u={r['L1_u']:.2f} front={r['front']:.1f} "
            f"(exact {r['front_exact']:.1f}, err {100 * r['front_err']:.2f}%) water={r['water_err']:.1e}")
    p = np.log2(rs[-2]["L1_h"] / rs[-1]["L1_h"])
    dec = all(a["L1_h"] > b["L1_h"] for a, b in zip(rs, rs[1:]))
    gate("B2 Ritter: L1(h) decreasing", dec, f"observed order (last pair) {p:.2f}")
    gate("B2 Ritter: front within 1% at finest", abs(rs[-1]["front_err"]) < 0.01,
         f"front error {100 * rs[-1]['front_err']:.2f}% (wet threshold 1e-6 m)")


def b3():
    Ns = (400, 800, 1600) if QUICK else (400, 800, 1600, 3200)
    rs = []
    for N in Ns:
        r = R.b3_stoker(N); rs.append(r)
        say(f"  B3 N={N}: L1h={r['L1_h']:.4f} shock err={100 * r['shock_err']:.2f}% "
            f"hm err={100 * r['hm_err']:.3f}% um err={100 * r['um_err']:.3f}%")
    f = rs[-1]
    gate("B3 Stoker", abs(f["shock_err"]) < 0.01 and abs(f["hm_err"]) < 0.01 and abs(f["um_err"]) < 0.01,
         f"finest: shock {100 * f['shock_err']:.2f}%, hm {100 * f['hm_err']:.3f}%, um {100 * f['um_err']:.3f}%")


def b9():
    r = R.b9_two_rarefactions()
    gate("B9 positivity", r["min_area"] >= 0 and not r["nan"] and r["water_err"] < 1e-12,
         f"min A={r['min_area']:.4f} NaN={r['nan']} water err={r['water_err']:.1e}; "
         f"centre h={r['h_centre']:.4f} vs exact {r['h_star']:.4f} (reported)")


def b12a(recon):
    res = []

    def rep(r):
        res.append(r)
        b = f" Borda={r['borda']:.4f} ({100 * r['err_borda']:+.1f}%)" if "borda" in r else ""
        say(f"  B12a[{recon}] {r['case']:26s} {r['direction']} loss={r['loss']:.4f} "
            f"relation={r['loss_rel']:.4f} ({100 * r['err_rel']:+.1f}%){b} conv={r['converged']}")

    J.b12a_cases(recon, rep)
    exp = [r for r in res if r["kind"] == "exp" and not r["case"].startswith("conduit")]
    ok_rel = all(abs(r["err_rel"]) < 0.01 for r in res if not r["case"].startswith("conduit") and r["kind"] == "exp")
    ok_borda = all(abs(r["err_borda"]) < 0.03 for r in exp)
    no_gain = all(r["loss"] > 0 for r in res)
    gate(f"B12a[{recon}] expansions vs relation (1%)", ok_rel,
         "max err " + f"{100 * max(abs(r['err_rel']) for r in exp):.1f}%")
    gate(f"B12a[{recon}] expansions vs Borda (3%)", ok_borda,
         "max err " + f"{100 * max(abs(r['err_borda']) for r in exp):.1f}%")
    con = [r for r in res if r["kind"] == "con"]
    gate(f"B12a[{recon}] contractions vs relation (1%)", all(abs(r["err_rel"]) < 0.01 for r in con),
         "errors " + ", ".join(f"{r['case']} {100 * r['err_rel']:+.0f}%" for r in con[::2]))
    cnd = [r for r in res if r["case"].startswith("conduit")]
    gate(f"B12a[{recon}] conduit->open vs relation (1%)", all(abs(r["err_rel"]) < 0.01 for r in cnd),
         ", ".join(f"{r['direction']} {100 * r['err_rel']:+.0f}% conv={r['converged']}" for r in cnd))
    gate(f"B12a[{recon}] no net energy gain at any junction", no_gain, "")


def b12b():
    for kind in ("rect", "trap"):
        rs = []
        for N in ((10, 20, 40) if QUICK else (10, 20, 40, 80)):
            r = J.b12b_case(kind, N); rs.append(r)
            say(f"  B12b {kind} N={N}: Q/Qc-1={r['err']:+.2e} Fr_brink={r['Fr_brink']:.4f} drift={r['drift']:.1e}")
        dec = all(abs(a["err"]) >= abs(b["err"]) for a, b in zip(rs, rs[1:]))
        gate(f"B12b free overfall [{kind}]", all(abs(r["err"]) < 0.01 for r in rs) and dec,
             "errors " + ", ".join("%+.1e" % r["err"] for r in rs) + f"; decreasing={dec}")


def b12c(recon):
    res = []

    def rep(r):
        res.append(r)
        say(f"  B12c[{recon}] {r['case']:11s} k={r['spread']:2d} {r['direction']} loss={r['loss']:.4f} "
            f"max cell gain={r['max_gain_flux']:.1e} conv={r['converged']}")

    J.b12c_cases(recon, spreads=(5, 20) if QUICK else (5, 10, 20, 50), report=rep)
    gain = max(r["max_gain_flux"] for r in res)
    gate(f"B12c[{recon}] no energy gain in any cell (1e-6 m)", gain < 1e-6, f"max cell gain {gain:.1e} m")
    falling = True
    for case in sorted({r["case"] for r in res}):
        L = [r["loss"] for r in res if r["case"] == case and r["direction"] == "L->R"]
        falling &= all(a >= b for a, b in zip(L, L[1:]))
    gate(f"B12c[{recon}] loss falls as the change is spread", falling, "")


def b13():
    out = R.b13_cases()
    for k, v in out.items():
        say(f"  B13 {k}: C in [{v['C_min']:.4f}, {v['C_max']:.4f}] (h>1mm: [{v['C_min_h_gt_1mm']:.4f}, "
            f"{v['C_max_h_gt_1mm']:.4f}]) AC_min={v['AC_min_before_drying']:.1e} solids err={v['solids_err']:.1e} "
            f"store={v['store']:.2e}")
    gate("B13 passive scalar bounded, solids exact",
         all(v["bounded"] and v["solids_err"] < 1e-12 for v in out.values()),
         "sub-case (e) (solids source) not run: no sources in phase B")


def main():
    say(f"Phase B first gates {'(quick)' if QUICK else '(full)'}")
    for f in (b1, b2, b3, b9, b13, b12b, lambda: b12a("velocity"), lambda: b12a("discharge_width"),
              lambda: b12c("velocity"), lambda: b12c("discharge_width")):
        try:
            f()
        except Exception as e:                      # report and continue
            import traceback
            traceback.print_exc()
            gate(getattr(f, "__name__", "case"), False, f"ERROR {e!r}")
    print("\n================ SUMMARY ================", flush=True)
    for name, ok, d in summary:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {d}")
    n_fail = sum(not ok for _, ok, _ in summary)
    print(f"\nRESULT: {len(summary) - n_fail} pass, {n_fail} fail  ({time.time() - T0:.0f} s)")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
