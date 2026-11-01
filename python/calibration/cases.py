"""Calibration case builder, runner and scorer (stage 3).

Builds an idealised embankment prism from a case JSON (cases/<id>.json), runs the V3.2.2 engine with the
cal-1 model choices (cal1_config.json) and a factor set {f_kd, C_h, f_t}, and scores the result against the
case observations using the objective in validation/calibration/CALIBRATION_PROTOCOL.md.

Validation cases must not be scored with this module before stage 4: score() refuses a case whose tier is
'validation' unless allow_validation=True.
"""
from __future__ import annotations

import json
import math
import time
import warnings
from pathlib import Path
from typing import Dict, Optional

import numpy as np

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE.parent))
import breach_engine_2d_v3_2 as E  # noqa: E402

DEFAULT_FACTORS = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}
HEADCUT_C0 = 0.05


def load_case(case_id: str) -> Dict:
    return json.loads((HERE / "cases" / f"{case_id}.json").read_text())


def _stage_volume(res: Dict, H: float) -> Dict[float, float]:
    """Return {level: volume} from area-height points or a power curve; extended above the crest."""
    if res["type"] == "area_height":
        pts = np.asarray(res["points"], dtype=float)
        h = np.concatenate([[0.0], pts[:, 0]])
        a = np.concatenate([[pts[0, 1]], pts[:, 1]])
        top = max(H + 2.0, h[-1] + 2.0)
        slope = (a[-1] - a[-2]) / max(h[-1] - h[-2], 1e-9)
        h_ext = np.linspace(h[-1], top, 9)[1:]
        a_ext = a[-1] + max(slope, 0.0) * (h_ext - h[-1])
        h, a = np.concatenate([h, h_ext]), np.concatenate([a, a_ext])
        vol = np.concatenate([[0.0], np.cumsum(0.5 * (a[1:] + a[:-1]) * np.diff(h))])
        return {float(L): float(V) for L, V in zip(h, vol)}
    if res["type"] == "power":
        Vf, Hf, ex = float(res["V_full"]), float(res.get("H_full", H)), float(res["exp"])
        levels = np.linspace(0.0, H + 0.5 * H, 61)
        return {float(L): float(Vf * (L / Hf) ** ex) for L in levels}
    if res["type"] == "prismatic":
        area = float(res["area"])
        levels = np.linspace(0.0, 2.0 * H, 41)
        return {float(L): float(area * L) for L in levels}
    raise ValueError(f"unknown reservoir type {res['type']}")


def build(case: Dict, factors: Optional[Dict] = None, grid_divisor: Optional[float] = None):
    """Return (mesh, reservoir, material, config, meta) for a case and factor set."""
    f = dict(DEFAULT_FACTORS, **(factors or {}))
    H, Wc, zu, zd = case["H"], case["crest_w"], case["zu"], case["zd"]
    div = grid_divisor or (8.0 if case["kind"] == "lab" else 6.0)
    dx = dy = H / div
    up, dn = zu * H, zd * H
    s0, apron = case.get("stub_up", 0.5 * H), case.get("apron", 2.0 * H)
    lx = s0 + up + Wc + dn + apron
    nx = int(math.ceil(lx / dx)); lx = nx * dx
    ny = max(int(round(case["section_width"] / dy)), 4); ly = ny * dy
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dy
    xc0 = s0 + up
    z1 = np.interp(x, [0.0, s0, xc0, xc0 + Wc, xc0 + Wc + dn, lx], [0.0, 0.0, H, H, 0.0, 0.0])
    zb = np.repeat(z1[:, None], ny, axis=1)
    n = case["notch"]
    yc = 0.5 * ly
    if n["shape"] == "trapezoid":
        zn = (H - n["depth"]) + np.maximum(np.abs(y - yc) - 0.5 * n["bottom_width"], 0.0) / n["side_hv"]
    elif n["shape"] == "v":
        zn = (H - n["depth"]) + np.abs(y - yc) * (2.0 * n["depth"] / n["top_width"])
    else:
        raise ValueError(n["shape"])
    zb = np.minimum(zb, np.minimum(zn[None, :], H))
    invert = H - n["depth"]
    curve = _stage_volume(case["reservoir"], H)
    level0 = case.get("initial_level", invert)
    res = E.Reservoir(curve, level0)
    eta = np.where(x[:, None] < xc0, level0, -1e9) * np.ones((nx, ny))
    mesh = E.create_prism_mesh(lx, ly, nx, ny, zb, eta, z_floor=0.0)

    m = case["material"]
    d50 = m.get("d50_mm", 0.1) / 1000.0
    if m["class"] == "cohesive":
        cohesion = (m["qu_kPa"] / 2.0 if "qu_kPa" in m else m.get("cohesion_kPa", 0.0)) * 1000.0
        mat = E.MaterialProps(material_class="cohesive", D50=d50, D90=max(4 * d50, d50), porosity=m.get("porosity", 0.35),
                              cohesion=cohesion, phi=math.degrees(math.atan(m.get("tan_phi", 0.55))),
                              tau_c=m["tauc_Pa"], kd=m["kd_cm3Ns"] * 1e-6 * f["f_kd"], n_exp=1.0)
        transport, shear = E.TransportFormula.HANSON, "total"
    else:
        mat = E.MaterialProps(material_class="noncohesive", D50=d50, D90=m.get("d90_mm", 2.5 * m.get("d50_mm", 0.1)) / 1000.0,
                              porosity=m.get("porosity", 0.35), cohesion=m.get("cohesion_kPa", 0.0) * 1000.0,
                              phi=math.degrees(math.atan(m.get("tan_phi", 0.7))), tau_c=m.get("tauc_Pa", 1.0))
        transport, shear = E.TransportFormula.WU, "grain"
    n_man = case.get("manning_n") or max(0.016, d50 ** (1 / 6) / 21.1)
    cfg = E.EngineConfig(transport=transport, bank_stability=E.BankStabilityMethod.CRITICAL_DEPTH,
                         friction_model="manning", manning_n=n_man, erosion_shear=shear,
                         dt_morpho_target=max(H / 20.0, 0.25), morph_accel=case.get("morph_accel", 1.0),
                         headcut_method="energy", headcut_C=HEADCUT_C0 * f["C_h"],
                         transport_capacity_factor=f["f_t"],
                         downstream_boundary=case.get("downstream", "outfall"))
    meta = dict(dx=dx, nx=nx, ny=ny, lx=lx, ly=ly, invert=invert, xc0=xc0, notch_y=yc, factors=f, manning_n=n_man)
    return mesh, res, mat, cfg, meta


def run(case: Dict, factors: Optional[Dict] = None, t_end: Optional[float] = None, verbose: bool = False,
        grid_divisor: Optional[float] = None, max_wall_seconds: Optional[float] = None) -> Dict:
    mesh, res, mat, cfg, meta = build(case, factors, grid_divisor)
    z0 = mesh.z_b.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        eng = E.UltimateBreachEngine(mesh, res, mat, cfg)
        q_in = case.get("inflow", 0.0)
        t0 = time.perf_counter()
        eng.run(t_end or case["t_end"], Qin=q_in, verbose=verbose, print_every=300.0,
                stop_when_drained_s=600.0, max_wall_seconds=max_wall_seconds)
    hist = eng.history
    t = np.array([h["time"] for h in hist]); qo = np.array([h["Q_prism_outlet"] for h in hist])
    k = int(np.argmax(qo)) if len(qo) else 0
    crest = eng._crest_rows
    low = np.maximum(z0 - mesh.z_b, 0.0)
    breached = bool(np.max(low[crest, :]) > 0.5 * case["notch"]["depth"]) if crest.any() else False
    bd = eng.breach_development()
    d = eng.diagnostics_summary()
    return {"id": case["id"], "factors": meta["factors"], "Qp": float(qo[k]) if len(qo) else 0.0,
            "Tp_h": float(t[k]) / 3600.0 if len(t) else 0.0, "B": float(bd["width_m"]), "breached": breached,
            "t_end_s": float(eng.time), "status": eng.run_status, "steps": eng.nsteps,
            "wall_s": time.perf_counter() - t0, "grid": [meta["nx"], meta["ny"], meta["dx"]],
            "balances": [d["water_balance_err_m3"], d["reservoir_balance_err_m3"], d["sediment_balance_err_m3"]],
            "max_lowering_m": float(np.max(low))}


def score(case: Dict, result: Dict, allow_validation: bool = False) -> Dict:
    """Objective terms per CALIBRATION_PROTOCOL.md (squared, summed)."""
    if case.get("tier") == "validation" and not allow_validation:
        raise PermissionError(f"{case['id']} is a validation case; scoring it before stage 4 is not allowed")
    o, terms = case["obs"], {}
    if o.get("breached") is False:
        terms["no_breach"] = 1.0 if result["breached"] else 0.0
    else:
        if o.get("Qp"):
            terms["Qp"] = math.log(max(result["Qp"], 1e-9) / o["Qp"]) ** 2
        if o.get("Tp_h"):
            terms["Tp"] = math.log(max(result["Tp_h"], 1e-6) / o["Tp_h"]) ** 2
    if o.get("B"):
        terms["B"] = ((result["B"] - o["B"]) / o["B"]) ** 2
    return {"id": case["id"], "terms": terms, "J": float(sum(terms.values()))}
