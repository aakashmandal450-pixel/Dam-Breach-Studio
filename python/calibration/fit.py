"""Fit the calibration factors on the grid results and run leave-one-out (CALIBRATION_PROTOCOL.md,
PROTOCOL_AMENDMENT_1.md).

Usage: python calibration\\fit.py            -> prints the fit and LOO table, writes calibration\\cal-1_candidate.json
The objective separates by case type: measured-kd cohesive cases depend on (f_kd, C_h); other cohesive cases on C_h;
non-cohesive cases on (f_t, C_h). The total is minimised over the full grid.

Run classes (amendment 1):
  completed  reached t_end, the post-peak stop, or 'reservoir_drained'          -> J from score()
  censored   stopped by the compute budget (old wall cap or CPU budget)        -> J = PENALTY_MISSING (primary rule)
  error      exception, missing result, wall-safety stop                        -> J = PENALTY_MISSING
Sensitivity fit (amendment 1 s.6, as clarified in amendment 1a): factor sets for which any included case is censored
are removed from the search, and the fit is repeated. A factor whose chosen grid value differs from the primary fit is
flagged 'censoring_sensitive'.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_grid import LOG_GRID  # noqa: E402

PENALTY_MISSING = 25.0   # a run that failed or was censored counts as a very poor fit (primary rule)


def classify(r):
    if "error" in r or "score" not in r:
        return "error"
    if r.get("censored", r.get("capped")):
        return "censored"
    return "completed"


def load(out):
    res = {}
    for f in Path(out).glob("*.json"):
        r = json.loads(f.read_text())
        fac = r["factors"]
        key = (round(math.log10(fac["f_kd"]), 2), round(math.log10(fac["C_h"]), 2), round(math.log10(fac["f_t"]), 2))
        cls = classify(r)
        J = r["score"]["J"] if cls == "completed" else PENALTY_MISSING
        res[(r["id"], key)] = (J, r, cls)
    return res


def _key(kind, fk, ch, ft):
    return {"kd": (fk, ch, 0.0), "ch": (0.0, ch, 0.0), "t": (0.0, ch, ft)}[kind]


def case_J(res, cid, kind, fk, ch, ft):
    v = res.get((cid, _key(kind, fk, ch, ft)))
    return PENALTY_MISSING if v is None else v[0]


def case_cls(res, cid, kind, fk, ch, ft):
    v = res.get((cid, _key(kind, fk, ch, ft)))
    return "error" if v is None else v[2]


def fit(res, kinds, include, drop_censored=False):
    best = None
    for fk, ch, ft in itertools.product(LOG_GRID["f_kd"], LOG_GRID["C_h"], LOG_GRID["f_t"]):
        if drop_censored and any(case_cls(res, cid, kinds[cid], fk, ch, ft) == "censored" for cid in include):
            continue
        J = sum(case_J(res, cid, kinds[cid], fk, ch, ft) for cid in include)
        if best is None or J < best[0]:
            best = (J, fk, ch, ft)
    return best


def main(out=None):
    out = out or HERE.parent.parent / "runs" / "calibration_grid"
    res = load(out)
    kinds = {}
    for f in sorted((HERE / "cases").glob("*.json")):
        c = json.loads(f.read_text())
        if c.get("tier") != "calibration":
            continue
        m = c["material"]
        kinds[c["id"]] = ("kd" if m["class"] == "cohesive" and m.get("kd_status", "").startswith("measured")
                          else "ch" if m["class"] == "cohesive" else "t")
    ids = sorted(kinds)

    counts = {}
    for cid in ids:
        keys = {_key(kinds[cid], fk, ch, ft) for fk, ch, ft in
                itertools.product(LOG_GRID["f_kd"], LOG_GRID["C_h"], LOG_GRID["f_t"])}
        n = {"completed": 0, "censored": 0, "error": 0}
        for k in keys:
            v = res.get((cid, k))
            n["error" if v is None else v[2]] += 1
        counts[cid] = n
        print(f"  {cid:11s} completed {n['completed']:3d}  censored {n['censored']:3d}  error/missing {n['error']:3d}")

    J, fk, ch, ft = fit(res, kinds, ids)
    print(f"full fit: J={J:.3f}  f_kd=10^{fk} ({10**fk:.3g})  C_h=10^{ch} ({10**ch:.3g})  f_t=10^{ft} ({10**ft:.3g})")
    loo = []
    for leave in ids:
        Jl, a, b, c_ = fit(res, kinds, [i for i in ids if i != leave])
        held = case_J(res, leave, kinds[leave], a, b, c_)
        loo.append({"left_out": leave, "f_kd": 10 ** a, "C_h": 10 ** b, "f_t": 10 ** c_, "held_out_J": held})
        print(f"  LOO -{leave:11s}: f_kd {10**a:8.3g}  C_h {10**b:8.3g}  f_t {10**c_:8.3g}   held-out J {held:.3f}")
    stab = {}
    for k in ("f_kd", "C_h", "f_t"):
        vals = [r[k] for r in loo]
        ratio = max(vals) / min(vals)
        stab[k] = {"min": min(vals), "max": max(vals), "max_over_min": ratio, "stable": ratio <= 3.0}
        print(f"  {k}: LOO range {min(vals):.3g}-{max(vals):.3g} (x{ratio:.1f}) -> {'stable' if ratio <= 3.0 else 'UNSTABLE'}")

    sens = fit(res, kinds, ids, drop_censored=True)
    if sens is None:
        print("censoring sensitivity: every factor set has a censored case; no sensitivity fit possible")
        sens_out, flags = None, {k: True for k in ("f_kd", "C_h", "f_t")}
    else:
        Js, sfk, sch, sft = sens
        sens_out = {"J": Js, "f_kd": 10 ** sfk, "C_h": 10 ** sch, "f_t": 10 ** sft}
        flags = {"f_kd": sfk != fk, "C_h": sch != ch, "f_t": sft != ft}
        print(f"censoring sensitivity fit: J={Js:.3f}  f_kd {10**sfk:.3g}  C_h {10**sch:.3g}  f_t {10**sft:.3g}  -> "
              + ", ".join(f"{k} {'SENSITIVE' if v else 'same'}" for k, v in flags.items()))

    per_case = {cid: {"J": case_J(res, cid, kinds[cid], fk, ch, ft), "class": case_cls(res, cid, kinds[cid], fk, ch, ft)}
                for cid in ids}
    cand = {"factors": {"f_kd": 10 ** fk, "C_h": 10 ** ch, "f_t": 10 ** ft}, "J_total": J, "J_per_case": per_case,
            "loo": loo, "stability": stab, "censoring_sensitivity": sens_out, "censoring_sensitive": flags,
            "run_counts": counts, "grid": LOG_GRID, "n_results": len(res)}
    (HERE / "cal-1_candidate.json").write_text(json.dumps(cand, indent=1))
    print("written calibration/cal-1_candidate.json (freeze as cal-1 only after review)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
