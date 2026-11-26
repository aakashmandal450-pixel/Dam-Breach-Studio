"""Validity checks of fela_v2 (lower/upper bounds for openings in Tresca clay).

1. Prandtl strip footing (weightless): exact N_c = 2 + pi must lie inside [LB, UB].
2. Circular tunnel vs Wilson et al. (2011, Can. Geotech. J. 48:1328, Table A1, rho = 0): two valid
   bound pairs must overlap, i.e. our LB <= their UB and our UB >= their LB. H taken as the cover.
3. Square opening (the pipe roof): rerun with the rigorous far field; rigid block compared.
For every solve the independent audit must show admissible fields (residuals < 1e-6).
Usage: python fela_benchmarks.py <output_txt>
"""
import math
import sys
import threading
import time

import fela_v2 as f

WILSON = {  # (H/D, gamma D/cu): (LB, UB)
    (1, 0): (2.43, 2.45), (2, 0): (3.45, 3.48), (3, 0): (4.12, 4.16),
    (1, 1): (1.25, 1.26), (2, 1): (1.17, 1.20), (3, 1): (0.79, 0.84),
    (1, 2): (0.01, 0.03), (2, 2): (-1.17, -1.15), (3, 2): (-2.62, -2.57),
}
AUD_TOL = 1e-6
out_lines, fails = [], []
N_CASES = 2 + len(WILSON) + 1 + 4 + 1
_state = {"case": 0, "stage": "", "t0": time.time(), "T0": time.time(), "busy": False}


def _heartbeat():
    """Every 15 s while a solve runs, print what is running and for how long."""
    while True:
        time.sleep(15)
        if _state["busy"]:
            print(f"      ... still {_state['stage']} ({time.time() - _state['t0']:.0f} s on this step, "
                  f"{time.time() - _state['T0']:.0f} s total)", flush=True)


def stage(text):
    _state["stage"], _state["t0"], _state["busy"] = text, time.time(), True
    print(f"   [{time.strftime('%H:%M:%S')}] {text} ...", flush=True)


def log(s):
    print(s, flush=True)
    out_lines.append(s)


def audit_ok(lb, ub):
    a, b = lb["audit"], ub["audit"]
    bad = [k for k in ("equilibrium", "traction_and_bc", "yield_excess", "load_bc", "side_excess", "bottom_excess")
           if a.get(k, 0.0) > AUD_TOL]
    bad += [k for k in ("incompressibility", "far_bc", "sym_bc") if b[k] > AUD_TOL]
    if abs(b["recomputed"] - b["objective"]) > 1e-3 * max(1.0, abs(b["objective"])):
        bad.append("UB recomputed != objective")
    return bad


def case(label, kind, C, D, gam, h):
    t0 = time.time()
    _state["case"] += 1
    print(f"\n>> Step {_state['case']}/{N_CASES}: {label}", flush=True)
    stage("building mesh")
    m = {"rect": lambda: f.rect_mesh(C, D, h), "circle": lambda: f.circle_mesh(C, h),
         "footing": lambda: f.footing_mesh(h)}[kind]()
    print(f"      mesh: {len(m.T)} triangles, {len(m.P)} nodes", flush=True)
    stage("solving LOWER bound (stress field)")
    lb = f.lower_bound(m, gam)
    print(f"      lower bound = {lb['value']:.4f}  ({time.time() - _state['t0']:.1f} s)", flush=True)
    stage("solving UPPER bound (velocity field)")
    ub = f.upper_bound(m, gam)
    print(f"      upper bound = {ub['value']:.4f}  ({time.time() - _state['t0']:.1f} s)", flush=True)
    _state["busy"] = False
    bad = audit_ok(lb, ub)
    if lb["value"] > ub["value"] + 1e-6:
        bad.append("LB > UB")
    a = lb["audit"]; b = ub["audit"]
    log(f"{label:34s} ntri={lb['ntri']:6d}  LB {lb['value']:8.4f} [{lb['status']}]  UB {ub['value']:8.4f} "
        f"[{ub['status']}]  {time.time() - t0:5.1f}s")
    log(f"{'':34s} LB audit: eq {a['equilibrium']:.1e} trac {a['traction_and_bc']:.1e} yield+ {a['yield_excess']:.1e}"
        f" side+ {a.get('side_excess', 0):.1e} bot+ {a.get('bottom_excess', 0):.1e} | UB audit: vol {b['incompressibility']:.1e}"
        f" bc {b['far_bc']:.1e} recomputed {b['recomputed']:.4f}")
    if bad:
        fails.append(f"{label}: audit {bad}")
        log(f"{'':34s} AUDIT FAIL: {bad}")
    return lb["value"], ub["value"]


def main(path):
    threading.Thread(target=_heartbeat, daemon=True).start()
    print(f"FELA v2 benchmarks: {N_CASES} steps, each = mesh + lower bound + upper bound", flush=True)
    log("== 1. Prandtl strip footing, exact 2+pi = %.4f" % (2 + math.pi))
    for h in (0.1, 0.05):
        lo, up = case(f"footing h={h}", "footing", 0, 0, 0.0, h)
        ok = lo <= 2 + math.pi + 1e-4 and up >= 2 + math.pi - 1e-4
        log(f"{'':34s} brackets exact: {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"footing h={h} does not bracket 2+pi")

    log("\n== 2. Circular tunnel vs Wilson et al. 2011 (rho = 0), H = cover")
    for (H, g), (wl, wu) in WILSON.items():
        lo, up = case(f"circle H/D={H} gD/c={g} h=0.1", "circle", float(H), 1.0, float(g), 0.1)
        ok = lo <= wu + 0.01 and up >= wl - 0.01
        log(f"{'':34s} Wilson [{wl:.2f}, {wu:.2f}]  overlap: {'PASS' if ok else 'FAIL'}  "
            f"(our LB {100 * (lo - wl) / max(abs(wl), 0.5):+.1f}%, UB {100 * (up - wu) / max(abs(wu), 0.5):+.1f}% vs theirs)")
        if not ok:
            fails.append(f"circle H/D={H} g={g}: no overlap with Wilson")
    lo, up = case("circle H/D=2 gD/c=1 h=0.05", "circle", 2.0, 1.0, 1.0, 0.05)
    log(f"{'':34s} mesh refinement of the case above (Wilson [1.17, 1.20])")

    log("\n== 3. Square opening (pipe roof), D/B = 1, gB/cu = 1, rigorous far field")
    for C in (0.5, 1.0, 2.0, 4.0):
        lo, up = case(f"square C/B={C} h=0.1", "rect", C, 1.0, 1.0, 0.1)
        log(f"{'':34s} rigid block {f.block(C, 1.0):.3f}")
    case("square C/B=2 h=0.05", "rect", 2.0, 1.0, 1.0, 0.05)

    log("\n== RESULT: " + ("ALL PASS" if not fails else f"{len(fails)} FAIL"))
    for s in fails:
        log("   " + s)
    with open(path, "w") as fh:
        fh.write("\n".join(out_lines) + "\n")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "fela_benchmarks.txt"))
