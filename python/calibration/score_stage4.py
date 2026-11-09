"""Stage 4 scoring (validation/calibration/STAGE4_PROTOCOL.md). Opens observed_validation.csv; run it once, after
run_stage4.py has written runs/stage4/MANIFEST.json and the runs are committed and tagged `stage4-runs`.

Refuses to score if any result file differs from its SHA-256 in the manifest, or if a manifest result is missing.
Writes runs/stage4/STAGE4_RESULTS.json and runs/stage4/STAGE4_RESULTS.md.

Usage (from the python folder):  python calibration\\score_stage4.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
OUT = ROOT / "runs" / "stage4"
OBS = ROOT / "validation" / "calibration" / "observed_validation.csv"

# acceptance limits (SPLIT.md, confirmed in STAGE4_PROTOCOL.md s.5)
LIM_QP = 1.5      # factor
LIM_TP = 2.0      # factor
LIM_B = 0.5       # relative
LIM_DD = 0.25     # relative (lake drawdown; no observations in this set)
LIM_BAL = 1e-6    # balance error / volume released
SHARE = 2.0 / 3.0  # a limit passes if it is met in at least 2 of 3 of the cases where it applies


def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s or "")
    return float(m.group(0)) if m else None


def load_obs():
    lines = [l for l in OBS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    rows = list(csv.DictReader(lines))
    out = {}
    for r in rows:
        text = " ".join(v for v in r.values() if v)
        nb = "no breach" in text.lower()
        st = r.get("obs_stage_times_min") or ""
        st_nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", st)]
        out[r["id"]] = {"Qp": None if nb else num(r.get("obs_Qp_m3s")), "B": num(r.get("obs_B_m")),
                        "Tp_h": num(r.get("obs_Tp_h")), "Tf_h": num(r.get("obs_Tf_h")), "no_breach": nb,
                        "duration_s": (sum(st_nums) * 60.0 if (nb and st_nums) else None), "raw": r}
    return out


def verify_manifest():
    m = json.loads((OUT / "MANIFEST.json").read_text())
    bad = []
    for name, h in m["results"].items():
        p = OUT / name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append(name)
    if bad:
        sys.exit(f"results differ from MANIFEST.json (or are missing): {bad}. Not scoring.")
    return m


def assess(r, o, case):
    """Per-run limits; None = not applicable (no observation)."""
    out = {"stop_cause": r.get("stop_cause"), "censored": bool(r.get("censored"))}
    if o["no_breach"]:
        dur = o["duration_s"] or r.get("t_end_phys_s")
        tb = r.get("t_breach_phys_s")
        out["model_breached_within_test"] = tb is not None and tb <= dur
        out["no_breach_ok"] = not out["model_breached_within_test"]
        out["test_duration_s"] = dur
    else:
        out["no_breach_ok"] = None
        if o["Qp"]:
            out["Qp_ratio"] = r["Qp"] / o["Qp"]
            out["Qp_ok"] = 1.0 / LIM_QP <= out["Qp_ratio"] <= LIM_QP
        if o["Tp_h"]:
            out["Tp_ratio"] = r["Tp_h"] / o["Tp_h"]
            out["Tp_ok"] = 1.0 / LIM_TP <= out["Tp_ratio"] <= LIM_TP
    if o["B"]:
        out["B_rel"] = (r["B"] - o["B"]) / o["B"]
        out["B_ok"] = abs(out["B_rel"]) <= LIM_B
    # balance relative to the water released (initial lake + inflow - final lake ~ outflow volume)
    try:
        import cases as C
        import numpy as np
        curve = C._stage_volume(case["reservoir"], float(case["H"]))
        L = np.array(sorted(curve)); V = np.array([curve[k] for k in L])
        v0 = float(np.interp(float(case.get("initial_level", case["H"])), L, V))
        released = max(v0 - float(r["lake_volume_end_m3"]), 1e-9)
        out["balance_rel"] = max(abs(x) for x in r["balances"]) / released
        out["balance_ok"] = out["balance_rel"] < LIM_BAL
    except Exception as exc:
        out["balance_note"] = repr(exc)
    keys = [k for k in ("no_breach_ok", "Qp_ok", "Tp_ok", "B_ok") if out.get(k) is not None]
    out["case_pass"] = all(out[k] for k in keys) if keys else None
    out["J"] = None
    try:
        cobs = {"B": o["B"]}
        if o["no_breach"]:
            cobs["breached"] = False
        else:
            cobs.update({"Qp": o["Qp"], "Tp_h": o["Tp_h"]})
        r2 = dict(r)
        if o["no_breach"]:
            r2["breached"] = out["model_breached_within_test"]
        out["J"] = C.score({**case, "obs": cobs}, r2, allow_validation=True)["J"]
    except Exception as exc:
        out["J_note"] = repr(exc)
    return out


def main():
    man = verify_manifest()
    import cases as C
    obs = load_obs()
    res = {"manifest_git_head": man.get("git_head"), "cases": {}, "walsh": {}}
    rows_md = []
    for name in sorted(man["results"]):
        r = json.loads((OUT / name).read_text())
        cid, set_ = name[:-5].split("__")
        if r.get("tier") == "seen-validation":
            res["walsh"][name] = r
            continue
        case = C.load_case(cid)
        o = obs.get(cid)
        if o is None:
            res["cases"].setdefault(cid, {})[set_] = {"note": "no observation row"}
            continue
        a = assess(r, o, case)
        a.update({"Qp": r.get("Qp"), "Tp_h": r.get("Tp_h"), "B": r.get("B"), "breached": r.get("breached"),
                  "t_breach_phys_s": r.get("t_breach_phys_s"), "obs": {k: v for k, v in o.items() if k != "raw"}})
        res["cases"].setdefault(cid, {})[set_] = a

    # primary: F_all (IMPACT_1-02 with the SP3 inflow)
    prim = {cid: d["F_all"] for cid, d in res["cases"].items() if "obs" in d.get("F_all", {})}
    missing = sorted(cid for cid, d in res["cases"].items() if "obs" not in d.get("F_all", {}))
    res["no_observation_row"] = missing
    limits = {}
    for key, label in (("Qp_ok", "peak within x1.5"), ("Tp_ok", "time to peak within x2"),
                       ("B_ok", "final width within +/-50 %"), ("no_breach_ok", "no breach reproduced"),
                       ("balance_ok", "balance < 1e-6 of volume released")):
        vals = [a[key] for a in prim.values() if a.get(key) is not None]
        limits[key] = {"label": label, "n": len(vals), "met": sum(vals),
                       "passes": (sum(vals) >= SHARE * len(vals)) if vals else None}
    limits["drawdown"] = {"label": "lake drawdown within +/-25 %", "n": 0, "met": 0, "passes": None,
                          "note": "no drawdown observations in observed_validation.csv"}
    n_case = [a["case_pass"] for a in prim.values() if a.get("case_pass") is not None]
    res["primary"] = {"limits": limits, "cases_passing": sum(n_case), "cases_scored": len(n_case),
                      "J_total": sum(a["J"] for a in prim.values() if a.get("J") is not None)}
    # envelope over the LOO factor sets
    env = {}
    for cid, d in res["cases"].items():
        if cid in missing:
            continue
        vals = {k: [a.get(k) for s, a in d.items() if s.startswith(("F_all", "LOO")) and s != "F_all_inflowWP2"
                    and a.get(k) is not None] for k in ("Qp_ratio", "Tp_ratio", "B_rel")}
        env[cid] = {k: ([min(v), max(v)] if v else None) for k, v in vals.items()}
    res["loo_envelope"] = env
    (OUT / "STAGE4_RESULTS.json").write_text(json.dumps(res, indent=1, default=str))

    md = ["# Stage 4 results (blind validation, frozen cal-2)", "", f"Results manifest: git {man.get('git_head')}", "",
          "| Case | Qp model / obs | ratio | Tp model / obs [h] | ratio | B model / obs [m] | rel. | No breach | Pass | J |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda x, p=3: "-" if x is None else (f"{x:.{p}g}" if isinstance(x, float) else str(x))
    for cid, a in sorted(prim.items()):
        o = a["obs"]
        md.append(f"| {cid} | {f(a['Qp'])} / {f(o['Qp'])} | {f(a.get('Qp_ratio'))} | {f(a['Tp_h'])} / {f(o['Tp_h'])} | "
                  f"{f(a.get('Tp_ratio'))} | {f(a['B'])} / {f(o['B'])} | {f(a.get('B_rel'), 2)} | "
                  f"{f(a.get('no_breach_ok'))} | {f(a.get('case_pass'))} | {f(a.get('J'))} |")
    md += ["", "| Limit | cases met / applicable | passes (>= 2/3) |", "|---|---|---|"]
    for k, l in limits.items():
        md.append(f"| {l['label']} | {l['met']} / {l['n']} | {f(l['passes'])} |")
    md += ["", f"Cases passing all their limits: {res['primary']['cases_passing']} of {res['primary']['cases_scored']}; "
           f"J total {res['primary']['J_total']:.3f}" + (f"; no observation row: {missing}" if missing else ""), "", "LOO envelope (min-max over F_all and LOO factor sets):", ""]
    for cid, e in sorted(env.items()):
        md.append(f"- {cid}: Qp ratio {e['Qp_ratio']}, Tp ratio {e['Tp_ratio']}, B rel {e['B_rel']}")
    if "IMPACT_1-02" in res["cases"] and "F_all_inflowWP2" in res["cases"]["IMPACT_1-02"]:
        a = res["cases"]["IMPACT_1-02"]["F_all_inflowWP2"]
        md.append(f"\nIMPACT_1-02 with the WP2 inflow: Qp ratio {f(a.get('Qp_ratio'))}, Tp ratio {f(a.get('Tp_ratio'))}, "
                  f"B rel {f(a.get('B_rel'), 2)}")
    md += ["", "## Walsh (seen validation, split-5; not in the pass rate)", "",
           "| Run | Qp model / obs [m3/s] | ratio | t peak from T=0 model / obs [s] | B* at peak model / obs [m] |",
           "|---|---|---|---|---|"]
    for name, r in sorted(res["walsh"].items()):
        cid = r["id"]; o = C.load_case(cid)["obs"]
        md.append(f"| {name[:-5]} | {f(r['Qp'])} / {o['Qp']} | {f(r['Qp'] / o['Qp'])} | {f(r['t_peak_from_start_s'])} / "
                  f"{o['Tp_h'] * 3600:.0f} | {f(r['B_at_peak'])} / {o['B_star_at_peak']} |")
    (OUT / "STAGE4_RESULTS.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
