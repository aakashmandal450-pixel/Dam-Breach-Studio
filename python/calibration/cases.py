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
        area, base = float(res["area"]), float(res.get("base", 0.0))
        levels = np.linspace(base, base + 2.0 * H, 41)
        return {float(L): float(area * (L - base)) for L in levels}
    if res["type"] == "stage_volume":
        pts = sorted((float(a), float(b)) for a, b in res["points"])
        h = np.array([p[0] for p in pts]); v = np.array([p[1] for p in pts])
        if h[0] > 0.0:
            h, v = np.concatenate([[0.0], h]), np.concatenate([[0.0], v])
        top = max(H + 1.0, h[-1] + 1.0)
        slope = (v[-1] - v[-2]) / (h[-1] - h[-2])
        h_ext = np.linspace(h[-1], top, 6)[1:]
        h, v = np.concatenate([h, h_ext]), np.concatenate([v, v[-1] + slope * (h_ext - h[-1])])
        return {float(L): float(V) for L, V in zip(h, v)}
    raise ValueError(f"unknown reservoir type {res['type']}")


def build(case: Dict, factors: Optional[Dict] = None, grid_divisor: Optional[float] = None,
          overrides: Optional[Dict] = None):
    """Return (mesh, reservoir, material, config, meta) for a case and factor set."""
    f = dict(DEFAULT_FACTORS, **(factors or {}))
    H, Wc, zu, zd = case["H"], case["crest_w"], case["zu"], case["zd"]
    div = grid_divisor or (8.0 if case["kind"] == "lab" else 6.0)
    dx = dy = H / div
    up, dn = zu * H, zd * H
    s0, apron = case.get("stub_up", 0.5 * H), case.get("apron", 2.0 * H)
    lx = s0 + up + Wc + dn + apron
    nx = int(math.ceil(lx / dx)); lx = nx * dx
    ny = max(int(round(case["section_width"] / dy)), 5)
    if ny % 2 == 0:          # odd cell count: one cell is centred on the notch (cal-1 notch rule)
        ny += 1
    dy = case["section_width"] / ny; ly = ny * dy
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dy
    xc0 = s0 + up
    z1 = np.interp(x, [0.0, s0, xc0, xc0 + Wc, xc0 + Wc + dn, lx], [0.0, 0.0, H, H, 0.0, 0.0])
    beach = case.get("beach")
    if beach:   # tailings beach: from the upstream end (cut-off wall) at h_wall rising at 'slope' to meet the dam face
        zb_beach = beach["h_wall"] + beach["slope"] * x
        z1 = np.where(x < xc0, np.maximum(z1, np.minimum(zb_beach, H)), z1)
    zb = np.repeat(z1[:, None], ny, axis=1)
    n = case["notch"]
    yc = 0.5 * ly
    notch_widened = False
    if n["shape"] == "trapezoid":
        zn = (H - n["depth"]) + np.maximum(np.abs(y - yc) - 0.5 * n["bottom_width"], 0.0) / n["side_hv"]
    elif n["shape"] == "v":
        zn = (H - n["depth"]) + np.abs(y - yc) * (2.0 * n["depth"] / n["top_width"])  # V-notch
    else:
        raise ValueError(n["shape"])
    jc = ny // 2
    if zn[jc] > H - n["depth"] + 1e-9 or (n["shape"] == "trapezoid" and n["bottom_width"] < dy) or n["shape"] == "v":
        # notch narrower than a cell: keep its depth, give the centred cell the invert (cal-1 notch rule, flagged)
        zn[jc] = H - n["depth"]
        notch_widened = n["shape"] == "v" or n.get("bottom_width", 0.0) < dy
    zb = np.minimum(zb, np.minimum(zn[None, :], H))
    invert = H - n["depth"]
    curve = _stage_volume(case["reservoir"], H)
    level0 = case.get("initial_level", invert + case.get("initial_head", 0.0))
    res = E.Reservoir(curve, level0)
    eta = np.where(x[:, None] < xc0, level0, -1e9) * np.ones((nx, ny))
    if beach:
        eta = np.where(x[:, None] < xc0, level0, -1e9) * np.ones((nx, ny))
    mesh = E.create_prism_mesh(lx, ly, nx, ny, zb, eta, z_floor=0.0)

    m = case["material"]
    d50 = m.get("d50_mm", 0.1) / 1000.0
    if m["class"] == "cohesive":
        phi_r = math.atan(m.get("tan_phi", 0.55))
        if "qu_kPa" in m:   # unconfined compression: qu = 2 c tan(45 + phi/2)
            cohesion = m["qu_kPa"] * 1000.0 / (2.0 * math.tan(math.pi / 4 + phi_r / 2))
        else:
            cohesion = m.get("cohesion_kPa", 0.0) * 1000.0
        mat = E.MaterialProps(material_class="cohesive", D50=d50, D90=max(4 * d50, d50), porosity=m.get("porosity", 0.35),
                              cohesion=cohesion, phi=math.degrees(math.atan(m.get("tan_phi", 0.55))),
                              tau_c=m["tauc_Pa"], n_exp=1.0,
                              kd=m["kd_cm3Ns"] * 1e-6 * (f["f_kd"] if m.get("kd_status", "").startswith("measured") else 1.0))
        transport, shear = E.TransportFormula.HANSON, "total"
        suspended = "none"
    else:
        mat = E.MaterialProps(material_class="noncohesive", D50=d50, D90=m.get("d90_mm", 2.5 * m.get("d50_mm", 0.1)) / 1000.0,
                              porosity=m.get("porosity", 0.35), cohesion=m.get("cohesion_kPa", 0.0) * 1000.0,
                              phi=math.degrees(math.atan(m.get("tan_phi", 0.7))), tau_c=m.get("tauc_Pa", 1.0))
        transport, shear = E.TransportFormula.WU, "grain"
        suspended = "wu2000"
    n_man = case.get("manning_n") or max(0.016, d50 ** (1 / 6) / 21.1)
    cfg = E.EngineConfig(transport=transport, bank_stability=E.BankStabilityMethod.CRITICAL_DEPTH,
                         friction_model="manning", manning_n=n_man, erosion_shear=shear,
                         dt_morpho_target=max(H / 20.0, 0.25), morph_accel=case.get("morph_accel", 1.0),
                         headcut_method="energy", headcut_C=HEADCUT_C0 * f["C_h"],
                         transport_capacity_factor=f["f_t"],
                         adaptation_length_mode="depth_scaled", adaptation_depth_factor=5.0,
                         suspended_load=suspended,
                         downstream_boundary=case.get("downstream", "outfall"))
    for k, v in (overrides or {}).items():   # diagnostics only; calibration runs use cal-1 as built
        setattr(cfg, k, v)
    meta = dict(notch_widened=notch_widened, dx=dx, nx=nx, ny=ny, lx=lx, ly=ly, invert=invert, xc0=xc0, notch_y=yc, factors=f, manning_n=n_man)
    return mesh, res, mat, cfg, meta


def run(case: Dict, factors: Optional[Dict] = None, t_end: Optional[float] = None, verbose: bool = False,
        grid_divisor: Optional[float] = None, max_wall_seconds: Optional[float] = None, chunk_s: float = 120.0,
        progress: bool = False, overrides: Optional[Dict] = None, progress_cb=None, *,
        max_cpu_seconds: Optional[float] = None, max_wall_safety_seconds: Optional[float] = None,
        post_peak_stop: bool = False, post_peak_window_s: float = 1800.0, post_peak_frac: float = 0.05,
        checkpoint_dir: Optional[str] = None, checkpoint_every_cpu_s: float = 1800.0) -> Dict:
    """Run a case. Times reported are physical (morphological) seconds.

    case['accel'] = A (> 1): morphology runs A times faster than the flow until breach initiation is detected
    in the model (notch invert lowered by 25 % of the notch depth), then at 1. This is the cal-1 rule for
    steady-inflow lab tests whose initiation lasts hours. Initiation is detected from the model, never from data.

    Stopping (PROTOCOL_AMENDMENT_1.md). All new options default to off, so the original cal-1 behaviour is unchanged.
      max_wall_seconds        original wall-clock cap (time.perf_counter; counts sleep) -> stop_cause 'wall_cap'
      max_cpu_seconds         CPU-time budget of this process (time.process_time)        -> 'cpu_budget'
      max_wall_safety_seconds hang guard only; a run stopped by it is an error run       -> 'wall_safety'
      post_peak_stop          stop as completed once the model has breached and, for the last post_peak_window_s of
                              physical time (and at least that long after the peak), Q <= Q_in + frac*(Q_max - Q_in)
                              -> 'post_peak'. Never applied to a case whose observation is 'no breach'.
    'censored' is True only for a budget stop (wall_cap or cpu_budget). 'capped' is kept equal to it for old readers.

    Checkpoints (checkpoint_dir): every checkpoint_every_cpu_s of CPU time, at a chunk boundary, the engine state is
    saved with UltimateBreachEngine.save_checkpoint (history left out), the new history entries are appended as a
    numbered .npz part, and the runner state (switch time, CPU/wall used, parts) is written last to runner.json.
    A later call with the same checkpoint_dir resumes from it; CPU and wall time are cumulative across restarts.
    The caller deletes the folder once the result is written.
    """
    mesh, res, mat, cfg, meta = build(case, factors, grid_divisor, overrides)
    z0 = mesh.z_b.copy()
    A = float(case.get("accel", 1.0))
    cfg.morph_accel = A
    t_phys_end = float(t_end or case["t_end"])
    dn = case["notch"]["depth"]
    t_switch_h: Optional[float] = None
    wall0 = time.perf_counter()
    cpu0 = time.process_time()
    stop_cause: Optional[str] = None
    pp_on = bool(post_peak_stop) and case.get("obs", {}).get("breached") is not False
    pp_key = "Q_in_prism" if case.get("q_measure") == "reservoir" else "Q_prism_outlet"
    pp_qin = float(case.get("inflow", 0.0)) if not callable(case.get("inflow", 0.0)) else 0.0
    pp = {"i": 0, "qmax": -np.inf, "t_peak": None, "t_last_exceed": None}
    cpu_prev = wall_prev = 0.0
    restarts = 0
    ck = Path(checkpoint_dir) if checkpoint_dir else None
    ck_state = None
    if ck is not None and (ck / "runner.json").exists():
        ck_state = json.loads((ck / "runner.json").read_text())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if ck_state is not None and ck_state.get("t_switch_h") is not None:
            cfg.morph_accel = 1.0          # the saved engine had acceleration switched off already
        eng = E.UltimateBreachEngine(mesh, res, mat, cfg)
        crest = eng._crest_rows
        q_in = case.get("inflow", 0.0)
        if ck_state is not None:
            eng.load_checkpoint(str(ck / ck_state["engine_file"]))
            hist = []
            for part in ck_state["parts"]:
                with np.load(ck / part, allow_pickle=False) as a_:
                    cols = {k: a_[k] for k in a_.files}
                n_ = len(next(iter(cols.values()))) if cols else 0
                keys_ = list(cols)
                hist.extend({k: float(cols[k][i]) for k in keys_} for i in range(n_))
            if len(hist) != ck_state["n_history"]:
                raise RuntimeError(f"checkpoint history has {len(hist)} entries, runner.json says {ck_state['n_history']}")
            eng.history = hist
            t_switch_h = ck_state["t_switch_h"]
            cpu_prev, wall_prev = ck_state["cpu_s"], ck_state["wall_s"]
            restarts = ck_state.get("restarts", 0) + 1
            pp.update({k: ck_state["pp"][k] for k in ("i", "t_peak", "t_last_exceed")})
            pp["qmax"] = -np.inf if ck_state["pp"]["qmax"] is None else ck_state["pp"]["qmax"]
            if progress:
                print(f"    resumed from checkpoint at engine t = {eng.time:.0f} s (restart {restarts})", flush=True)
        ck_saved_n = len(eng.history)
        ck_last_cpu = time.process_time()

        def save_ck():
            nonlocal ck_saved_n, ck_last_cpu
            k_ = (ck_state or {}).get("seq", 0) + 1 if not hasattr(save_ck, "seq") else save_ck.seq + 1
            save_ck.seq = k_
            ck.mkdir(parents=True, exist_ok=True)
            new_h = eng.history[ck_saved_n:]
            part = f"hist_{k_:05d}.npz"
            if new_h:
                keys_ = list(new_h[0].keys())
                tmp = ck / (part + ".tmp")
                with open(tmp, "wb") as fh:
                    np.savez(fh, **{k: np.array([h_[k] for h_ in new_h], dtype=float) for k in keys_})
                import os as _os
                _os.replace(tmp, ck / part)
            full = eng.history
            eng.history = []
            try:
                eng.save_checkpoint(str(ck / f"engine_{k_:05d}.npz"))
            finally:
                eng.history = full
            parts = list((ck_state or {}).get("parts", [])) if not hasattr(save_ck, "parts") else save_ck.parts
            if new_h:
                parts = parts + [part]
            save_ck.parts = parts
            state = {"seq": k_, "engine_file": f"engine_{k_:05d}.npz", "parts": parts, "n_history": len(full),
                     "engine_time": eng.time, "t_switch_h": t_switch_h, "A": A,
                     "cpu_s": cpu_prev + time.process_time() - cpu0, "wall_s": wall_prev + time.perf_counter() - wall0,
                     "restarts": restarts,
                     "pp": {"i": pp["i"], "t_peak": pp["t_peak"], "t_last_exceed": pp["t_last_exceed"],
                            "qmax": None if not np.isfinite(pp["qmax"]) else pp["qmax"]}}
            tmp = ck / "runner.json.tmp"
            tmp.write_text(json.dumps(state))
            import os as _os
            _os.replace(tmp, ck / "runner.json")
            for old_f in ck.glob("engine_*.npz"):      # keep only the engine file runner.json points to
                if old_f.name != state["engine_file"]:
                    try:
                        old_f.unlink()
                    except OSError:
                        pass
            ck_saved_n = len(full)
            ck_last_cpu = time.process_time()

        def phys(th):
            if A <= 1.0:
                return th
            if t_switch_h is None:
                return th * A
            return t_switch_h * A + (th - t_switch_h)

        def phys_h(th):   # for history entries, which may pre-date the switch
            if A <= 1.0:
                return th
            if t_switch_h is None or th <= t_switch_h:
                return th * A
            return t_switch_h * A + (th - t_switch_h)

        while phys(eng.time) < t_phys_end - 1e-9:
            if A > 1.0 and t_switch_h is None:
                step = min(chunk_s, (t_phys_end - phys(eng.time)) / A)
            else:
                step = min(chunk_s, t_phys_end - phys(eng.time))
            eng.run(eng.time + step, Qin=q_in, verbose=verbose, print_every=600.0,
                    stop_when_drained_s=600.0)
            if progress_cb is not None:
                hh = eng.history[-1] if eng.history else {}
                progress_cb({"t": phys(eng.time), "t_end": t_phys_end, "Q": hh.get("Q_prism_outlet", 0.0),
                             "level": res.level, "lowering": float(np.max(z0 - mesh.z_b)),
                             "wall": time.perf_counter() - wall0, "accelerated": A > 1.0 and t_switch_h is None})
            if progress:
                hh = eng.history[-1] if eng.history else {}
                lw = float(np.max(z0 - mesh.z_b))
                print(f"    t = {phys(eng.time):9.0f} s of {t_phys_end:.0f} s  ({100 * phys(eng.time) / t_phys_end:5.1f} %)   "
                      f"Q out = {hh.get('Q_prism_outlet', 0.0):9.4g} m3/s   lake level = {res.level:8.3f} m   "
                      f"max lowering = {lw:7.3f} m   wall {time.perf_counter() - wall0:7.0f} s"
                      + ("   [accelerated initiation]" if A > 1.0 and t_switch_h is None else ""), flush=True)
            if eng.stop_reason is not None:
                stop_cause = str(eng.stop_reason)
                if progress:
                    print(f"    stopped: {eng.stop_reason}", flush=True)
                break
            if A > 1.0 and t_switch_h is None:
                low_notch = np.max((z0 - mesh.z_b)[crest, :]) if crest.any() else 0.0
                if low_notch > 0.25 * dn:
                    t_switch_h = eng.time
                    eng.cfg.morph_accel = 1.0
                    if progress:
                        print(f"    breach initiation detected at t = {t_switch_h * A:.0f} s -> acceleration off", flush=True)
            if pp_on:   # post-peak quiescence, updated incrementally from the new history entries
                hist_ = eng.history
                for h_ in hist_[pp["i"]:]:
                    tq, qq = phys_h(h_["time"]), float(h_[pp_key])
                    if qq > pp["qmax"]:
                        pp["qmax"], pp["t_peak"] = qq, tq
                    if qq > pp_qin + post_peak_frac * (pp["qmax"] - pp_qin):
                        pp["t_last_exceed"] = tq
                pp["i"] = len(hist_)
                t_now = phys(eng.time)
                lowered = float(np.max((z0 - mesh.z_b)[crest, :])) if crest.any() else 0.0
                if (lowered > 0.5 * dn and pp["t_peak"] is not None and pp["t_last_exceed"] is not None
                        and t_now - pp["t_peak"] >= post_peak_window_s
                        and t_now - pp["t_last_exceed"] >= post_peak_window_s):
                    stop_cause = "post_peak"
                    if progress:
                        print(f"    stopped: post-peak quiescence (peak at {pp['t_peak']:.0f} s)", flush=True)
                    break
            if max_cpu_seconds is not None and cpu_prev + time.process_time() - cpu0 > max_cpu_seconds:
                stop_cause = "cpu_budget"
                break
            if max_wall_safety_seconds is not None and wall_prev + time.perf_counter() - wall0 > max_wall_safety_seconds:
                stop_cause = "wall_safety"
                break
            if ck is not None and time.process_time() - ck_last_cpu >= checkpoint_every_cpu_s:
                save_ck()
            if max_wall_seconds is not None and time.perf_counter() - wall0 > max_wall_seconds:
                stop_cause = "wall_cap"
                break
    censored = stop_cause in ("wall_cap", "cpu_budget")
    if stop_cause is None and phys(eng.time) < t_phys_end - 1e-6:   # left the loop early for no recorded reason
        stop_cause = "unknown"
    hist = eng.history
    th = np.array([h["time"] for h in hist])
    tp = np.array([phys(v) for v in th])
    key = "Q_in_prism" if case.get("q_measure") == "reservoir" else "Q_prism_outlet"
    q = np.array([h[key] for h in hist])
    k = int(np.argmax(q)) if len(q) else 0
    datum = 0.0
    if case.get("tp_datum") == "q_frac" and len(q):
        frac = float(case.get("tp_datum_frac", 0.05))
        datum = float(tp[int(np.argmax(q >= frac * q[k]))])
    low = np.maximum(z0 - mesh.z_b, 0.0)
    breached = bool(np.max(low[crest, :]) > 0.5 * dn) if crest.any() else False
    bd = eng.breach_development()
    d = eng.diagnostics_summary()
    return {"id": case["id"], "factors": meta["factors"], "Qp": float(q[k]) if len(q) else 0.0,
            "Tp_h": (float(tp[k]) - datum) / 3600.0 if len(tp) else 0.0, "B": float(bd["width_m"]),
            "breached": breached, "t_end_phys_s": float(phys(eng.time)),
            "capped": censored, "censored": censored,
            "stop_cause": stop_cause or "t_end",
            "t_switch_phys_s": (None if t_switch_h is None else t_switch_h * A),
            "status": eng.run_status, "stop_reason": eng.stop_reason, "steps": eng.nsteps,
            "wall_s": wall_prev + time.perf_counter() - wall0, "cpu_s": cpu_prev + time.process_time() - cpu0,
            "restarts": restarts,
            "lake_volume_end_m3": float(res.volume),
            "runner": {"post_peak_stop": pp_on, "post_peak_window_s": post_peak_window_s, "post_peak_frac": post_peak_frac,
                       "max_cpu_seconds": max_cpu_seconds, "max_wall_seconds": max_wall_seconds,
                       "max_wall_safety_seconds": max_wall_safety_seconds,
                       "checkpoint_every_cpu_s": checkpoint_every_cpu_s if ck is not None else None},
            "grid": [meta["nx"], meta["ny"], meta["dx"]],
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
