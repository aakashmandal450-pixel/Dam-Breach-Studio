"""Walsh S3 initiation diagnostic (read-only: nothing is scored, fitted or changed in the engine).

Question: why does the cal-1 model of Walsh (2019) S3 not breach, and why does a 3x finer grid pass no water?
Every --log-every seconds it records, along the notch centre line (crest -> downstream face -> toe):
  lake level and head over the current notch invert, discharge into the prism / over the crest / out,
  depth, speed, grain bed shear and shear / critical shear, notch lowering, and where the bed is lowering.
At the end it writes a CSV time series, a CSV bed profile, a JSON summary and a plain-language verdict.

Usage (from the python folder):
  python -u calibration\\diag_walsh.py --grid 8  --t-end 1800 --log-every 10
  python -u calibration\\diag_walsh.py --grid 24 --t-end 120  --log-every 5
  python -u calibration\\diag_walsh.py --grid 16 --t-end 900 --log-every 10 --pilot-channel     # stage-3 start

Cross-section snapshots (--section-every, default 30 s) record the full-width bed and flow at two rows:
  control  the breach control section: the row whose lowest bed point is highest along the flow path from the
           lake to the toe (the breach lip; it moves upstream as the lip erodes)
  midcrest the middle row of the original crest
and print, per snapshot, the control row position, its invert, the eroded top width, the flowing width and Q.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases as C  # noqa: E402

E = C.E

ap = argparse.ArgumentParser()
ap.add_argument("--case", default="WalshS3")
ap.add_argument("--grid", type=float, default=8.0, help="cells per dam height (cal-1 lab grid = 8)")
ap.add_argument("--t-end", type=float, default=1800.0, help="simulated seconds")
ap.add_argument("--log-every", type=float, default=10.0, help="simulated seconds between log lines")
ap.add_argument("--max-wall", type=float, default=3600.0, help="stop after this many wall-clock seconds")
ap.add_argument("--cohesion-kpa", type=float, default=None,
                help="override material cohesion [kPa] (apparent cohesion of damp sand; Walsh case file has 0)")
ap.add_argument("--h-dry-mm", type=float, default=None, help="override the wet/dry depth threshold [mm] (cal-1: 1 mm)")
ap.add_argument("--pilot-channel", action="store_true",
                help="start at Walsh's stage 3: V channel cut from the upstream crest edge down the face to the toe")
ap.add_argument("--pilot-width", type=float, default=0.37,
                help="pilot channel top width [m]; 0.37 m = B* at T=0 for S3 (30 deg), Walsh 2019 Fig. 2.7a")
ap.add_argument("--pilot-depth", type=float, default=None,
                help="pilot channel depth [m]; default: sides at the friction angle, depth = width/2 * tan(phi)")
ap.add_argument("--section-every", type=float, default=30.0,
                help="simulated seconds between cross-section snapshots at the breach control section and mid-crest "
                     "(0 = off)")
ap.add_argument("--cfg", action="append", default=[], metavar="KEY=VALUE",
                help="diagnostic override of an EngineConfig field, e.g. --cfg headcut_min_slope=0.1 (repeatable)")
ap.add_argument("--uphill-floor", type=float, default=None,
                help="lower clip of the bed-slope factor on transport capacity (engine: 0.3). 1.0 = no reduction "
                     "where flow runs uphill (upstream face / breach lip); downhill enhancement unchanged")
ap.add_argument("--suffix", default="", help="appended to the output file names (keeps earlier results)")
ap.add_argument("--out", default=str(HERE.parent.parent / "runs" / "diag_walsh"))
a = ap.parse_args()

case = C.load_case(a.case)
mesh, res, mat, cfg, meta = C.build(case, {"f_t": 1.0}, a.grid)
cfg.morph_accel = 1.0
tag = f"{a.case}_H{int(a.grid)}"
overrides = {}
for kv in a.cfg:                        # diagnostic EngineConfig overrides (engine file unchanged)
    k, v = kv.split("=", 1)
    if not hasattr(cfg, k):
        sys.exit(f"--cfg: EngineConfig has no field '{k}'")
    old_v = getattr(cfg, k)
    new_v = (v.lower() in ("1", "true", "yes")) if isinstance(old_v, bool) else type(old_v)(v) if old_v is not None else float(v)
    setattr(cfg, k, new_v)
    overrides[k] = {"default": old_v, "set": new_v}
if a.uphill_floor is not None:          # diagnostic patch of the slope factor, this process only
    _floor = float(a.uphill_floor)

    def _slope_factor_patched(self, mesh_, ux, uy, speed):
        if not self.cfg.use_slope_effect:
            return 1.0
        dzdx = np.gradient(mesh_.z_b, mesh_.dx, axis=0)
        dzdy = np.gradient(mesh_.z_b, mesh_.dy, axis=1)
        dzds = (dzdx * ux + dzdy * uy) / (speed + 1e-9)
        return np.clip(1.0 - self.cfg.slope_beta * dzds, _floor, 3.0)
    E.Morphology._slope_factor = _slope_factor_patched
    overrides["slope_factor_lower_clip"] = {"default": 0.3, "set": _floor}
if a.cohesion_kpa is not None:          # diagnostic override only (engine and case files unchanged)
    mat.cohesion = a.cohesion_kpa * 1000.0
    tag += f"_c{a.cohesion_kpa:g}kPa"
if a.h_dry_mm is not None:
    cfg.h_dry = a.h_dry_mm / 1000.0
    tag += f"_hdry{a.h_dry_mm:g}mm"
pilot = None
if a.pilot_channel:      # diagnostic start condition only (case file and engine unchanged)
    tan_phi = math.tan(math.radians(mat.phi))
    pw = a.pilot_width
    pd = a.pilot_depth if a.pilot_depth is not None else 0.5 * pw * tan_phi
    surf = mesh.z_b[:, 0].copy()                      # dam surface away from the notch
    x_up, x_toe = meta["xc0"], meta["xc0"] + case["crest_w"] + case["zd"] * case["H"]
    yc_ = meta["notch_y"]
    cut = np.maximum(pd - np.abs(mesh.y - yc_) * (pd / (0.5 * pw)), 0.0)    # V section
    along = ((mesh.x >= x_up - 1e-9) & (mesh.x <= x_toe + 1e-9)).astype(float)
    target = surf[:, None] - along[:, None] * cut[None, :]
    # carry the channel floor upstream at crest level until it daylights on the upstream slope (breach crest lip)
    upface = (mesh.x < x_up)[:, None]
    target = np.where(upface, np.minimum(surf[:, None], case["H"] - cut[None, :]), target)
    mesh.z_b[:] = np.maximum(np.minimum(mesh.z_b, target), mesh.z_floor)
    pilot = {"width_m": pw, "depth_m": pd, "x_from_m": x_up - pd * case["zu"], "x_to_m": x_toe,
             "source": "width = B* at T=0, Walsh (2019) Fig. 2.7a (30 deg, S3); depth: sides at friction angle"
                       if a.pilot_depth is None else "width Fig. 2.7a; depth user-set"}
    tag += f"_pilot{pw:g}m"
    meta["invert"] = float(np.min(mesh.z_b[(mesh.x >= x_up) & (mesh.x <= x_up + case["crest_w"]), :]))
tag += a.suffix
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)

g, rho = cfg.g, mat.rho_w
H, dn = case["H"], case["notch"]["depth"]
nx, ny, dx, dy = mesh.nx, mesh.ny, mesh.dx, mesh.dy
jc = int(np.argmin(np.abs(mesh.y - meta["notch_y"])))
z0 = mesh.z_b.copy()

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    eng = E.UltimateBreachEngine(mesh, res, mat, cfg)

# true crest = rows at full dam height away from the notch (the engine's _crest_rows also take in parts of both slopes)
crest = z0[:, 0] >= H - 1e-9
crest_idx = np.flatnonzero(crest)
ic_last = int(crest_idx[-1])
apron_z = float(z0[-1, jc])
toe = next((i for i in range(ic_last + 1, nx) if z0[i, jc] <= apron_z + 1e-6), nx - 1)
mid = (ic_last + toe) // 2
probes = {"crest": ic_last, "face_mid": mid, "toe": toe}

theta_c = float(np.max(eng.morpho.transport.critical_shields_field()))
tau_c = theta_c * (mat.rho_s - mat.rho_w) * g * mat.D50
n_tot, n_gr = cfg.manning_n, eng.grain_n
h_dry = cfg.h_dry


def grain_shear(h, sp):
    hs = np.maximum(h, h_dry)
    tot = rho * g * n_tot**2 * sp**2 / hs ** (1 / 3)
    gr = rho * g * (n_gr or n_tot) ** 2 * sp**2 / hs ** (1 / 3)
    return np.where(h > h_dry, np.minimum(tot, gr) if cfg.erosion_shear == "grain" else tot, 0.0)


# ---- setup report ---------------------------------------------------------------------------------------
invert0 = meta["invert"]
head0 = res.level - invert0
tan_half = case["notch"]["top_width"] / (2 * dn)
q_vnotch = 8 / 15 * 0.6 * math.sqrt(2 * g) * tan_half * max(head0, 0) ** 2.5
q_cell = 1.7 * dy * max(head0, 0) ** 1.5
print(f"\n=== {a.case}  grid H/{a.grid:g}: {nx} x {ny} cells, dx = {dx*100:.1f} cm, dy = {dy*100:.1f} cm", flush=True)
print(f"    real notch: V, {case['notch']['top_width']*100:.0f} cm wide x {dn*100:.0f} cm deep;"
      f" model notch: one cell {dy*100:.1f} cm wide at the invert (notch_widened = {meta['notch_widened']})")
print(f"    lake level {res.level:.3f} m, notch invert {invert0:.3f} m -> head {head0*100:.1f} cm;"
      f" stored above invert {res.volume - float(np.interp(invert0, res.elevs, res.vols)):.2f} m3, inflow 0")
print(f"    hand check at this head: real V-notch Q = {q_vnotch*1000:.3f} L/s, one-cell weir Q = {q_cell*1000:.3f} L/s")
print(f"    wet/dry threshold h_dry = {h_dry*1000:.1f} mm;  D50 = {mat.D50*1000:.2f} mm,"
      f" theta_c = {theta_c:.3f} -> tau_c = {tau_c:.3f} Pa;  n = {n_tot:.4f}, grain n' = {n_gr}")
print(f"    true crest rows {crest_idx[0]}-{ic_last} (engine crest rows: {np.flatnonzero(eng._crest_rows)[0]}-{np.flatnonzero(eng._crest_rows)[-1]})")
print(f"    probes on the centre line (column {jc}): crest row {ic_last} (x={mesh.x[ic_last]:.2f} m),"
      f" face mid row {mid} (x={mesh.x[mid]:.2f}), toe row {toe} (x={mesh.x[toe]:.2f})")
print(f"    overrides: cohesion = {mat.cohesion/1000:g} kPa, h_dry = {cfg.h_dry*1000:g} mm"
      f"  (Culmann critical height of a 63 deg notch wall: {float(eng.morpho.bank.critical_height(np.array([math.atan(2*dn/case['notch']['top_width'])]))[0]) if hasattr(eng.morpho, 'bank') else float('nan'):.3f} m)")
if pilot:
    print(f"    PILOT CHANNEL (stage 3 start): V {pilot['width_m']:.2f} m wide x {pilot['depth_m']*100:.1f} cm deep,"
          f" x = {pilot['x_from_m']:.2f}-{pilot['x_to_m']:.2f} m; {pilot['source']}")
if overrides:
    print(f"    DIAGNOSTIC OVERRIDES: {overrides}")
print(f"    simulating {a.t_end:.0f} s, a line every {a.log_every:.0f} s; started {time.strftime('%H:%M:%S')}\n", flush=True)
print("      t[s]   head[cm]  Qin[L/s] Qcrest[L/s] Qout[L/s] | h[mm] crest/mid/toe | tau/tau_c crest/mid/toe |"
      " notch low[mm] max low[mm] @  | wall[s]", flush=True)

sec_rows, sec_lines = [], []
i_dam0 = int(np.argmax(z0[:, 0] > float(np.min(z0[:, 0])) + 1e-9))    # first row on the upstream face
mid_crest = int(crest_idx[len(crest_idx) // 2])
next_sec = 0.0 if a.section_every > 0 else float("inf")


def snapshot():
    """Full-width bed and flow at the control section and mid-crest; returns a one-line summary dict."""
    zb, h = mesh.z_b, mesh.h
    rmin = zb[i_dam0:toe + 1, :].min(axis=1)
    ictl = i_dam0 + int(np.argmax(rmin))          # highest lowest-point along the path = breach control section
    sp_ = np.hypot(mesh.u, mesh.v)
    tau_ = grain_shear(h, sp_)
    out_ = {"t": eng.time}
    for name, i in (("control", ictl), ("midcrest", mid_crest)):
        eroded = zb[i, :] < z0[i, 0] - 0.01        # channel: >1 cm below the undisturbed dam surface (edge column)
        wet = h[i, :] > 2 * h_dry
        q_row = float(np.sum(h[i, :] * mesh.u[i, :]) * dy)
        jj = int(np.argmin(zb[i, :]))
        fr = float(sp_[i, jj] / math.sqrt(g * max(h[i, jj], 1e-9))) if h[i, jj] > h_dry else 0.0
        out_.update({f"{name}_row": i, f"{name}_x": float(mesh.x[i]), f"{name}_invert": float(zb[i, :].min()),
                     f"{name}_top_width": float(eroded.sum() * dy), f"{name}_wet_width": float(wet.sum() * dy),
                     f"{name}_Q": q_row, f"{name}_hmax": float(h[i, :].max()), f"{name}_Fr_centre": fr,
                     f"{name}_tau_ratio_max": float(tau_[i, :].max() / tau_c)})
        for j in range(ny):
            sec_rows.append({"t": eng.time, "section": name, "row": i, "x_m": float(mesh.x[i]), "j": j,
                             "y_m": float(mesh.y[j]), "z0_m": float(z0[i, j]), "zb_m": float(zb[i, j]),
                             "h_m": float(h[i, j]), "u_ms": float(mesh.u[i, j]), "v_ms": float(mesh.v[i, j]),
                             "tau_ratio": float(tau_[i, j] / tau_c)})
    return out_


rows = []
wall0 = time.perf_counter()
first_flow_t = None
min_head_seen = head0
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    while eng.time < a.t_end - 1e-9:
        eng.run(min(eng.time + a.log_every, a.t_end), Qin=0.0, verbose=False, print_every=1e9,
                stop_when_drained_s=None)
        hh = eng.history[-1] if eng.history else {}
        h, sp = mesh.h, np.hypot(mesh.u, mesh.v)
        tau = grain_shear(h, sp)
        low = z0 - mesh.z_b
        q_crest = float(np.sum(h[ic_last, :] * mesh.u[ic_last, :]) * dy)
        inv_now = float(np.min(mesh.z_b[crest, :]))       # lowest point on the true crest = current notch invert
        notch_low = invert0 - inv_now                      # > 0 notch deepened, < 0 notch filled in
        head = res.level - inv_now
        min_head_seen = min(min_head_seen, head)
        k = np.unravel_index(int(np.argmax(low)), low.shape)
        zone = "upstream" if mesh.x[k[0]] < meta["xc0"] else ("crest" if crest[k[0]] else
                                                              ("face" if k[0] < toe else "apron"))
        r = {"t": eng.time, "level": res.level, "head_m": head, "res_volume": res.volume,
             "Q_in_prism": hh.get("Q_in_prism", 0.0), "Q_crest": q_crest, "Q_out": hh.get("Q_prism_outlet", 0.0),
             "notch_lowering_m": notch_low, "notch_invert_m": inv_now,
             "crest_side_lowering_m": float(np.max(low[crest, :])), "max_lowering_m": float(low[k]), "max_lowering_zone": zone,
             "max_lowering_x": float(mesh.x[k[0]]), "headcut_i": int(getattr(mesh, "headcut_i", 0)),
             "wet_cells_downstream": int(np.sum(h[ic_last + 1:, :] > h_dry)),
             "max_tau_ratio_face": float(np.max(tau[ic_last:toe + 1, :]) / tau_c),
             "wall_s": time.perf_counter() - wall0}
        for name, i in probes.items():
            r[f"h_{name}_m"] = float(h[i, jc])
            r[f"u_{name}_ms"] = float(sp[i, jc])
            r[f"tau_{name}_Pa"] = float(tau[i, jc])
            r[f"ratio_{name}"] = float(tau[i, jc] / tau_c)
        rows.append(r)
        if first_flow_t is None and q_crest > 1e-7:
            first_flow_t = eng.time
        print(f"    {r['t']:6.0f}  {head*100:8.2f}  {r['Q_in_prism']*1000:8.3f}  {q_crest*1000:9.3f}  {r['Q_out']*1000:8.3f} |"
              f" {r['h_crest_m']*1000:5.1f} {r['h_face_mid_m']*1000:5.1f} {r['h_toe_m']*1000:5.1f} |"
              f" {r['ratio_crest']:6.2f} {r['ratio_face_mid']:6.2f} {r['ratio_toe']:6.2f} |"
              f" {notch_low*1000:9.2f} {r['max_lowering_m']*1000:9.2f} {zone:>8s} | {r['wall_s']:6.0f}", flush=True)
        if eng.time >= next_sec - 1e-9:
            sl = snapshot()
            sec_lines.append(sl)
            print(f"      [section t={sl['t']:5.0f} s] control row {sl['control_row']} x={sl['control_x']:.2f} m"
                  f" invert {sl['control_invert']:.3f} m | top width {sl['control_top_width']:.2f} m,"
                  f" flowing {sl['control_wet_width']:.2f} m, Q {sl['control_Q']*1000:.2f} L/s,"
                  f" h max {sl['control_hmax']*1000:.0f} mm, Fr {sl['control_Fr_centre']:.2f},"
                  f" tau/tau_c max {sl['control_tau_ratio_max']:.1f} || mid-crest: invert {sl['midcrest_invert']:.3f} m,"
                  f" top width {sl['midcrest_top_width']:.2f} m, flowing {sl['midcrest_wet_width']:.2f} m", flush=True)
            while next_sec <= eng.time + 1e-9:
                next_sec += a.section_every
        if eng.stop_reason is not None:
            print(f"    engine stopped: {eng.stop_reason}")
            break
        if time.perf_counter() - wall0 > a.max_wall:
            print(f"    wall-clock limit {a.max_wall:.0f} s reached, stopping")
            break

# ---- outputs ----------------------------------------------------------------------------------------------
ts = out / f"{tag}_timeseries.csv"
with ts.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
if sec_rows:
    for fname, data in ((f"{tag}_sections.csv", sec_rows), (f"{tag}_sections_summary.csv", sec_lines)):
        with (out / fname).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
h, sp = mesh.h, np.hypot(mesh.u, mesh.v)
tau = grain_shear(h, sp)
pf = out / f"{tag}_profile.csv"
with pf.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["x_m", "z_initial_m", "z_final_m", "h_m", "speed_ms", "tau_grain_Pa", "tau_ratio"])
    for i in range(nx):
        w.writerow([f"{mesh.x[i]:.4f}", f"{z0[i, jc]:.5f}", f"{mesh.z_b[i, jc]:.5f}", f"{h[i, jc]:.5f}",
                    f"{sp[i, jc]:.4f}", f"{tau[i, jc]:.4f}", f"{tau[i, jc] / tau_c:.3f}"])

arr = {k: np.array([r[k] for r in rows]) for k in ("Q_in_prism", "Q_crest", "h_face_mid_m", "h_toe_m",
                                                     "max_tau_ratio_face", "notch_lowering_m", "head_m")}
verdict = []
if arr["Q_crest"].max() <= 1e-7 and arr["Q_in_prism"].max() <= 1e-7:
    verdict.append("NO FLOW: no water ever crosses the crest. The trickle is lost before the notch "
                   "(check the wet/dry threshold, the upstream boundary and the initial water surface).")
elif arr["Q_crest"].max() <= 1e-7:
    verdict.append("Water enters the prism but never crosses the crest row.")
if max(arr["h_face_mid_m"].max(), arr["h_toe_m"].max()) <= 2 * h_dry:
    verdict.append(f"TRICKLE AT THE WET/DRY LIMIT: depth on the downstream face never exceeds 2 x h_dry "
                   f"({2*h_dry*1000:.0f} mm), so shear there is set to zero or near zero.")
if arr["max_tau_ratio_face"].max() < 1.0:
    verdict.append(f"BELOW THRESHOLD: grain shear on the crest/face never reaches critical "
                   f"(max tau/tau_c = {arr['max_tau_ratio_face'].max():.2f}).")
elif 0.0 <= arr["notch_lowering_m"].max() < 0.25 * dn:
    verdict.append(f"ERODES BUT TOO SLOWLY: shear exceeds critical (max ratio {arr['max_tau_ratio_face'].max():.1f}) "
                   f"but the notch lowered only {arr['notch_lowering_m'].max()*1000:.1f} mm (initiation needs "
                   f"{0.25*dn*1000:.0f} mm).")
if min_head_seen < 0.002 and arr["notch_lowering_m"].max() < 0.25 * dn:
    verdict.append(f"SUPPLY RUNS OUT: lake head over the notch fell to {min_head_seen*1000:.1f} mm before the notch "
                   f"deepened, so the feedback (deeper notch -> more flow) never starts.")
if arr["notch_lowering_m"].min() < -0.005:
    verdict.append(f"NOTCH FILLED IN: the notch invert rose by up to {-arr['notch_lowering_m'].min()*1000:.0f} mm "
                   f"(sediment or collapsed notch walls), which can block the trickle.")
if arr["notch_lowering_m"].max() >= 0.5 * dn:
    verdict.append("BREACH: notch lowered by more than half its depth.")
if not verdict:
    verdict.append("No single cause flagged; read the time series.")

qin = np.array([r["Q_in_prism"] for r in rows]); tt = np.array([r["t"] for r in rows])
kp = int(np.argmax(qin)); qp = float(qin[kp]); tp = float(tt[kp])
t5 = float(tt[int(np.argmax(qin >= 0.05 * qp))]) if qp > 0 else 0.0
bd = eng.breach_development()
obs = case.get("obs", {})
stage3 = {"Qp_model_m3s": qp, "Qp_obs_m3s": obs.get("Qp"), "t_peak_model_s": tp,
          "t_peak_from_5pct_s": tp - t5, "Tp_obs_s_from_T0": (obs.get("Tp_h") or 0) * 3600.0,
          "breach_width_model_m": float(bd["width_m"])}
summary = {"case": a.case, "overrides": overrides, "pilot": pilot, "stage3": stage3, "grid_divisor": a.grid, "nx": nx, "ny": ny, "dx": dx, "dy": dy,
           "notch_cell_width_m": dy, "real_notch_top_width_m": case["notch"]["top_width"],
           "cohesion_Pa": mat.cohesion,
           "initial_head_m": head0, "h_dry_m": h_dry, "tau_c_Pa": tau_c, "theta_c": theta_c,
           "manning_n": n_tot, "grain_n": n_gr, "hand_Q_vnotch_m3s": q_vnotch, "hand_Q_onecell_m3s": q_cell,
           "first_flow_over_crest_s": first_flow_t, "max_Q_crest_m3s": float(arr["Q_crest"].max()),
           "max_Q_in_prism_m3s": float(arr["Q_in_prism"].max()), "min_head_m": min_head_seen,
           "max_tau_ratio_face": float(arr["max_tau_ratio_face"].max()),
           "max_notch_lowering_m": float(arr["notch_lowering_m"].max()),
           "simulated_s": rows[-1]["t"], "wall_s": rows[-1]["wall_s"], "verdict": verdict}
(out / f"{tag}_summary.json").write_text(json.dumps(summary, indent=1))

if pilot:
    print(f"\n    STAGE 3 vs WALSH: peak Q {qp:.4f} m3/s (observed {obs.get('Qp')}) at t = {tp:.0f} s "
          f"({tp - t5:.0f} s after Q first reached 5 % of peak; observed {stage3['Tp_obs_s_from_T0']:.0f} s after T=0); "
          f"breach width {bd['width_m']:.2f} m")
print("\n    VERDICT:")
for v in verdict:
    print("     - " + v)
print(f"\n    wrote {ts.name}, {pf.name}, {tag}_summary.json"
      + (f", {tag}_sections.csv, {tag}_sections_summary.csv" if sec_rows else "") + f" in {out}", flush=True)
