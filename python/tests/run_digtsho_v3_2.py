#!/usr/bin/env python
"""Dig Tsho 1985 — impulse wave -> overtopping -> breach with the V3.2 2-D prism engine.

Written from scratch from the parameters in the TypeScript chain script (run_digtsho_impulse_breach.ts),
because the earlier run_digtsho_2d.py was not available. Grid, material presets and criteria below are
my choices, not the old script's. This is a SCREENING run, not a validation: slide thickness, fall height,
erodibility and grain size are screening values, and the published numbers are printed as context only.

Published context (Vuichard & Zimmermann 1987): wave height about 4.4-5 m; peak discharge about 1600 m3/s
(range 1375-2000).

Usage (from the folder containing breach_engine_2d_v3_2.py):
    python validation\\run_digtsho_v3_2.py --t-end 1800 --stop-at-peak
    python validation\\run_digtsho_v3_2.py --material wu5 --t-end 3600
    python validation\\run_digtsho_v3_2.py --no-wave --t-end 600          # still-water control
    python validation\\run_digtsho_v3_2.py --resume out\\run.npz --t-end 7200

Pre-registered initiation criterion: fixed from the command line and written to the output JSON BEFORE the
run starts. Seeded runs (--notch > 0) can never count as natural initiation.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import breach_engine_2d_v3_2 as E

# ---------------------------------------------------------------- Dig Tsho parameters (from the TypeScript chain)
H_DAM = 18.0            # m, active water column = dam height above base
Z_UP, Z_DOWN = 1.8, 2.5  # H:V
CREST_WIDTH = 25.0       # m, along flow
CREST_LENGTH = 220.0     # m, transverse
LAKE_VOLUME = 5.5e6      # m3 at the rim
STORAGE_EXP = 1.8
INFLOW = 5.0             # m3/s
FALL_HEIGHT = 60.0       # m (screening, not published)
SLIDE = dict(slide_volume=150_000.0, thickness=10.0, slide_width=200.0, slide_density=950.0,
             porosity_percent=38.0, impact_angle_deg=30.0, lake_depth=18.0, distance_to_dam=1200.0)
KD_TS = 10.0 ** (-1.17) / 1900.0   # TypeScript erosion index I = 1.17, rho_d = 1900 -> m/s per Pa
LAKE_BED = 0.0          # m above the dam foundation (z = 0)

# Geometry sets. 'ts18' = the TypeScript chain values used by every run up to V3.2.1.
# 'westoby2015' = Westoby et al. (2015) Table 1 (SfM DTM): crest 4356 m, foundation 4316 m (z = 0),
# crest 250 x 30 m, distal face 1:3.1, proximal face 1:15.2, released volume about 7.3e6 m3.
# LAKE_BED = 24 m (4340 m) is the lower end of their hypsometry (Fig. 2, digitized in
# validation/calibration/digtsho_westoby2015_fig2_digitized.csv); about 0.3e6 m3 lies below 4340 m and is not modelled. It caps lake lowering at 16 m by
# construction; read Fig. 2 and set --lake-bed / --lake-volume / --storage-exp when better values are known.
GEOMETRIES = {
    "ts18": dict(H_DAM=18.0, LAKE_BED=0.0, Z_UP=1.8, Z_DOWN=2.5, CREST_WIDTH=25.0, CREST_LENGTH=220.0,
                 LAKE_VOLUME=5.5e6, STORAGE_EXP=1.8),
    "westoby2015": dict(H_DAM=40.0, LAKE_BED=24.0, Z_UP=15.2, Z_DOWN=3.1, CREST_WIDTH=30.0, CREST_LENGTH=250.0,
                        LAKE_VOLUME=6.9e6, STORAGE_EXP=1.3),   # Fig. 2 read by eye: 6.9e6 m3 between 4340 and 4356 m, exponent about 1.3
}


def set_geometry(args) -> None:
    """Install the selected geometry as module constants (CLI overrides applied)."""
    g = dict(GEOMETRIES[args.geometry])
    for key, val in (("LAKE_BED", args.lake_bed), ("LAKE_VOLUME", args.lake_volume), ("STORAGE_EXP", args.storage_exp)):
        if val is not None:
            g[key] = float(val)
    globals().update(g)
    SLIDE["lake_depth"] = g["H_DAM"] - g["LAKE_BED"]


PUBLISHED = {"wave_height_m": (4.4, 5.0), "peak_discharge_m3s": (1375.0, 2000.0, 1600.0)}

PRESETS = {
    "hanson_ts": (E.TransportFormula.HANSON, dict(D50=0.03, D90=0.12, tau_c=4.0, kd=KD_TS, phi=34.0)),
    "wu30": (E.TransportFormula.WU, dict(D50=0.03, D90=0.12, tau_c=4.0, phi=34.0)),
    "wu5": (E.TransportFormula.WU, dict(D50=0.005, D90=0.05, tau_c=4.0, phi=34.0)),
    "mpm5": (E.TransportFormula.MPM, dict(D50=0.005, D90=0.05, tau_c=4.0, phi=34.0)),
    "vanrijn5": (E.TransportFormula.VAN_RIJN, dict(D50=0.005, D90=0.05, tau_c=4.0, phi=34.0)),
}


def parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--material", choices=sorted(PRESETS), default="hanson_ts")
    p.add_argument("--geometry", choices=sorted(GEOMETRIES), default="westoby2015",
                   help="dam and lake geometry; ts18 reproduces every run up to V3.2.1")
    p.add_argument("--lake-bed", type=float, default=None, help="override lake bed height above the foundation [m]")
    p.add_argument("--lake-volume", type=float, default=None, help="override lake volume between lake bed and crest [m3]")
    p.add_argument("--storage-exp", type=float, default=None, help="override stage-volume exponent")
    p.add_argument("--erosion-shear", choices=("total", "grain"), default="grain",
                   help="shear that drives erosion: grain (skin friction, default from V3.2.2) or total (V3.2.1)")
    p.add_argument("--stop-drained-after", type=float, default=600.0,
                   help="stop this many seconds after the lake holds < 1000 m3 (negative = never; default 600)")
    p.add_argument("--floor", type=float, default=0.0, help="non-erodible floor height above the foundation [m]")
    p.add_argument("--manning-n", type=float, default=0.035, help="Manning roughness for hydraulics and bed shear (sensitivity)")
    p.add_argument("--kd-scale", type=float, default=1.0, help="multiplier on the preset erodibility kd (Hanson preset only; kd is uncalibrated)")
    p.add_argument("--cohesion", type=float, default=0.0, help="bank cohesion [Pa] (default 0, cohesionless moraine)")
    p.add_argument("--dx", type=float, default=2.5, help="grid size along flow [m]")
    p.add_argument("--dy", type=float, default=5.0, help="grid size across flow [m]")
    p.add_argument("--apron", type=float, default=40.0, help="flat downstream apron length [m]")
    p.add_argument("--downstream", choices=("transmissive", "wall", "outfall"), default="transmissive",
                   help="downstream boundary. 'transmissive' cannot drain a still pond (the released lake fills the prism and stalls); 'outfall' is a free overfall (untested option)")
    p.add_argument("--t-end", type=float, default=1800.0, help="simulated seconds")
    p.add_argument("--no-wave", action="store_true", help="still-water control (no incident wave)")
    p.add_argument("--no-displacement", action="store_true", help="skip the one-time displaced-volume bump")
    p.add_argument("--notch", type=float, default=0.0, help="numerical seed notch depth [m]; 0 = none (natural initiation)")
    p.add_argument("--crest-noise", type=float, default=0.0, help="Gaussian crest-bed perturbation sigma [m]; breaks transverse symmetry (natural, unseeded)")
    p.add_argument("--seed", type=int, default=0, help="random seed for --crest-noise")
    p.add_argument("--crest-dip", type=float, default=0.0, help="depth [m] of a smooth low point in the crest top (surveyed crest relief); 0 = flat crest")
    p.add_argument("--crest-dip-width", type=float, default=15.0, help="Gaussian sigma [m] of the crest low point")
    p.add_argument("--crest-dip-y", type=float, default=None, help="transverse position [m] of the low point (default mid-width)")
    p.add_argument("--spatial-order", type=int, choices=(1, 2), default=1)
    p.add_argument("--ls-mode", choices=("fixed", "depth_scaled"), default="fixed")
    p.add_argument("--morph-accel", type=float, default=1.0)
    p.add_argument("--no-headcut", action="store_true")
    p.add_argument("--hold-level", action="store_true", help="hold the reservoir stage at its initial value (diagnostic)")
    p.add_argument("--stop-at-peak", action="store_true",
                   help="stop at the first confirmed outlet peak AFTER the wave window (the wave's own sheet-flow spike is ignored)")
    p.add_argument("--peak-settle", type=float, default=60.0, help="seconds after the wave window before peak-stop is armed")
    p.add_argument("--wall-seconds", type=float, default=None, help="pause with a checkpoint after this much wall time")
    p.add_argument("--checkpoint-interval", type=float, default=300.0, help="simulated seconds between checkpoints")
    p.add_argument("--resume", type=str, default=None, help="checkpoint (.npz) to resume from; same options required")
    p.add_argument("--print-every", type=float, default=30.0)
    p.add_argument("--history-stride", type=int, default=20, help="write every Nth history row to the CSV")
    p.add_argument("--out", type=str, default="digtsho_out")
    # pre-registered criterion
    p.add_argument("--crit-lowering", type=float, default=1.0, help="min max-lowering [m]")
    p.add_argument("--crit-channelization", type=float, default=1.5)
    p.add_argument("--crit-time", type=float, default=3600.0, help="criterion window [s]")
    args = p.parse_args()
    set_geometry(args)
    return args


def build(args):
    s0 = 20.0                                   # lake stub upstream of the dam toe
    up, dn = Z_UP * (H_DAM - LAKE_BED), Z_DOWN * H_DAM
    x_crest_start = s0 + up
    lx = s0 + up + CREST_WIDTH + dn + args.apron
    nx = int(math.ceil(lx / args.dx))
    lx = nx * args.dx
    ny = int(round(CREST_LENGTH / args.dy))
    ly = ny * args.dy
    x = (np.arange(nx) + 0.5) * args.dx
    knots = [0.0, s0, x_crest_start, x_crest_start + CREST_WIDTH, x_crest_start + CREST_WIDTH + dn, lx]
    zb1d = np.interp(x, knots, [LAKE_BED, LAKE_BED, H_DAM, H_DAM, 0.0, 0.0])
    zb = np.repeat(zb1d[:, None], ny, axis=1)
    if args.crest_dip > 0.0:
        yy = (np.arange(ny) + 0.5) * args.dy
        yc = 0.5 * ny * args.dy if args.crest_dip_y is None else args.crest_dip_y
        plateau = (x >= x_crest_start) & (x <= x_crest_start + CREST_WIDTH)
        zb[plateau, :] -= (args.crest_dip * np.exp(-0.5 * ((yy - yc) / max(args.crest_dip_width, 1e-6)) ** 2))[None, :]

    levels = np.arange(LAKE_BED, H_DAM + 6.01, 0.5)
    curve = {float(L): float(LAKE_VOLUME * (max(L - LAKE_BED, 0.0) / (H_DAM - LAKE_BED)) ** STORAGE_EXP) for L in levels}
    res = E.Reservoir(curve, H_DAM)
    displaced = 0.0
    if not args.no_displacement:
        displaced = res.apply_displacement(SLIDE["slide_volume"], 1.0)
    level0 = res.level
    eta = np.where(x[:, None] < x_crest_start, level0, -1e9) * np.ones((nx, ny))
    mesh = E.create_prism_mesh(lx, ly, nx, ny, zb, eta, z_floor=np.minimum(args.floor, zb))
    mesh.headcut_i = 0

    if args.crest_noise > 0.0:
        E.perturb_crest(mesh, args.crest_noise, seed=args.seed)
    seeded = args.notch > 0.0
    if seeded:
        E.auto_seed_notch(mesh, x_crest_start, CREST_WIDTH, depth=args.notch)

    transport, mat_over = PRESETS[args.material]
    mat_over = dict(mat_over)
    if "kd" in mat_over:
        mat_over["kd"] = mat_over["kd"] * args.kd_scale
    mat = E.MaterialProps(material_class="noncohesive", cohesion=args.cohesion, **mat_over)
    cfg = E.EngineConfig(
        transport=transport, bank_stability=E.BankStabilityMethod.CRITICAL_DEPTH,
        friction_model="manning", manning_n=args.manning_n, erosion_shear=args.erosion_shear, spatial_order=args.spatial_order,
        dt_morpho_target=2.0, morph_accel=args.morph_accel, headcut_enabled=not args.no_headcut,
        adaptation_length_mode=args.ls_mode, downstream_boundary=args.downstream,
    )
    wave = None
    if not args.no_wave:
        wave = E.LakeWaveBoundary(E.ImpulseWave3D(
            fall_height=FALL_HEIGHT, slide_speed=math.sqrt(2.0 * 9.81 * FALL_HEIGHT), **SLIDE),
            lake=E.LakeGeometry(length_m=1200.0, width_m=ly, depth_at_dam_m=H_DAM - LAKE_BED, n_segments=1))
    return dict(mesh=mesh, res=res, mat=mat, cfg=cfg, wave=wave, seeded=seeded, displaced=displaced,
                level0=level0, grid=(nx, ny, lx, ly))


def main() -> int:
    args = parse()
    warnings.filterwarnings("ignore")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    case = build(args)
    mesh, res, mat, cfg, wave = case["mesh"], case["res"], case["mat"], case["cfg"], case["wave"]
    nx, ny, lx, ly = case["grid"]

    criterion = E.InitiationCriterion(min_lowering_m=args.crit_lowering, min_channelization=args.crit_channelization,
                                      min_bdi=0.0, t_max_s=args.crit_time, require_unseeded=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    prereg = {"registered_at": stamp, "criterion": criterion.__dict__, "seeded_run": case["seeded"], "args": vars(args)}
    (out / "preregistered_criterion.json").write_text(json.dumps(prereg, indent=2), encoding="utf-8")

    print("=" * 72)
    print(" Dig Tsho 1985 -- V3.2 2-D prism (screening, not validation)")
    print("=" * 72)
    print(f" geometry '{args.geometry}': dam {H_DAM:.0f} m, lake bed {LAKE_BED:.0f} m, crest {CREST_LENGTH:.0f} x {CREST_WIDTH:.0f} m, "
          f"faces 1:{Z_UP} / 1:{Z_DOWN}, lake {LAKE_VOLUME:.2e} m3 (exp {STORAGE_EXP}); erosion shear '{args.erosion_shear}'")
    print(f" grid {nx} x {ny} cells, dx={args.dx} m, dy={args.dy} m, domain {lx:.1f} x {ly:.1f} m")
    print(f" material preset '{args.material}': {PRESETS[args.material][0].value}, cohesion {args.cohesion} Pa")
    print(f" displaced volume {case['displaced']:.0f} m3 -> lake level {case['level0']:.3f} m (crest {H_DAM:.1f} m)")
    print(f" crest low point: {'depth ' + str(args.crest_dip) + ' m, sigma ' + str(args.crest_dip_width) + ' m' if args.crest_dip > 0 else 'none (flat crest)'}")
    print(f" crest perturbation: {'sigma=' + str(args.crest_noise) + ' m, seed ' + str(args.seed) if args.crest_noise > 0 else 'none (perfectly uniform across the dam width)'}")
    print(f" seeded notch: {'YES (' + str(args.notch) + ' m) -- cannot count as natural initiation' if case['seeded'] else 'no'}")
    print(f" pre-registered criterion: {criterion}")
    wave_summary = None
    wave_end = 0.0
    if wave is not None:
        wave_summary = E.impulse3d(wave.wave, 0.0)
        _a1, _t1, _a2, _c1, _c2, _per, _ts1, _ts2 = wave._components(0.0)
        wave_end = float(_ts2 + _per)      # end of the crest-trough-crest train on the axis
        print(f" wave window ends at about t = {wave_end:.0f} s (first crest arrives about {_ts1:.0f} s)")
        lo, hi = PUBLISHED["wave_height_m"]
        print(f" wave (3-D screening) HM={wave_summary['HM']:.2f} m, P={wave_summary['P']:.2f}, TM={wave_summary['TM']:.1f} s "
              f"(published context {lo}-{hi} m)")
    print("-" * 72)

    engine = E.UltimateBreachEngine(mesh, res, mat, cfg)
    monitor = E.InitiationMonitor(tau_threshold=None, lowering_threshold_m=0.5 * args.crit_lowering)
    ckpt = out / "run.npz"
    if args.resume:
        engine.load_checkpoint(args.resume)
        print(f" resumed from {args.resume} at t = {engine.time:.1f} s")
    hold = res.level if args.hold_level else None
    wall0 = time.time()
    def go(t_end, stop):
        engine.run(t_end, Qin=INFLOW, verbose=True, print_every=args.print_every,
                   stop_at_peak=stop, peak_confirm_steps=200,
                   checkpoint_path=str(ckpt), checkpoint_interval_s=args.checkpoint_interval,
                   wave_boundary=wave, hold_reservoir_level=hold, max_wall_seconds=args.wall_seconds,
                   monitor=monitor,
                   stop_when_drained_s=(None if args.stop_drained_after < 0 else args.stop_drained_after))

    if args.stop_at_peak and wave_end + args.peak_settle < args.t_end:
        go(wave_end + args.peak_settle, False)
        if engine.stop_reason is None:
            engine.peak_Q_prism_outlet, engine.peak_time, engine.peak_decline_steps = 0.0, engine.time, 0
            print(f" peak-stop armed at t = {engine.time:.0f} s (wave transient excluded)")
            go(args.t_end, True)
    else:
        go(args.t_end, False)
    wall = time.time() - wall0

    hist = engine.history
    t = np.array([r["time"] for r in hist])
    q = np.array([r["Q_prism_outlet"] for r in hist])
    t_init = monitor.t_first_lowering
    def peak(mask):
        return (float(q[mask].max()), float(t[mask][np.argmax(q[mask])])) if np.any(mask) else (None, None)
    p_all = peak(np.ones_like(t, dtype=bool))
    post_start = wave_end + args.peak_settle if wave_end > 0 else 0.0
    p_wave = peak(t < post_start) if wave_end > 0 else (None, None)
    p_post = peak(t >= post_start) if t.size and t.max() >= post_start else (None, None)
    last_rec = monitor.records[-1] if monitor.records else {}
    outflow = float(np.sum(0.5 * (q[1:] + q[:-1]) * np.diff(t))) if t.size > 1 else 0.0   # trapezoid rule (np.trapz is gone in NumPy 2)
    verdict = E.initiation_success(monitor, criterion, seeded=case["seeded"])
    md = engine.breach_development()
    z0 = engine._initial_bed
    summary = {
        "run_status": engine.run_status, "t_reached_s": engine.time, "wall_seconds": wall,
        "wave": wave_summary, "peak_outlet_all": p_all, "wave_window_end_s": wave_end, "post_wave_start_s": post_start, "peak_outlet_during_wave_window": p_wave,
        "peak_outlet_after_wave_window": p_post, "final_channelization_index": last_rec.get("channelization_index"), "t_first_lowering_s": t_init,
        "t_first_tau_exceed_s": monitor.t_first_tau_exceed, "outflow_volume_m3": outflow,
        "max_lowering_m": float(np.max(np.maximum(z0 - mesh.z_b, 0.0))), "breach": md,
        "initiation": verdict, "diagnostics": engine.diagnostics_summary(),
        "published_context_only": PUBLISHED,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    with open(out / "history_thinned.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hist[0].keys()))
        w.writeheader()
        w.writerows(hist[::max(args.history_stride, 1)])
    final_bed = out / "final_bed.npz"
    np.savez(final_bed, z_b=mesh.z_b, z0=z0, h=mesh.h, x=mesh.x, y=mesh.y)

    print("-" * 72)
    print(f" status: {engine.run_status}   t = {engine.time:.0f} s   wall = {wall:.0f} s")
    print(f" max lowering {summary['max_lowering_m']:.2f} m; breach depth {md['depth_m']:.2f} m, width {md['width_m']:.1f} m, BDI {md['BDI']:.3f}")
    print(f" peak outlet flux: overall {p_all[0]:.1f} m3/s at {p_all[1]:.0f} s" if p_all[0] is not None else " no flux recorded")
    if t_init is None:
        print(" lowering never reached the monitor threshold (no initiation)")
    else:
        print(f" lowering reached {0.5 * args.crit_lowering:.2f} m at t = {t_init:.0f} s"
              + ("  (inside the wave window: this is wave-driven stripping)" if t_init < wave_end else ""))
    if wave_end > 0:
        if p_wave[0] is not None:
            print(f" peak during the wave window (t < {post_start:.0f} s, wave plus settling): {p_wave[0]:.1f} m3/s at {p_wave[1]:.0f} s")
        if p_post[0] is not None:
            print(f" peak after the wave window (t >= {post_start:.0f} s, the breach-relevant number): {p_post[0]:.1f} m3/s at {p_post[1]:.0f} s")
        else:
            print(" the run ended before the wave window did")
    if last_rec:
        print(f" final channelization index {last_rec['channelization_index']:.2f} (criterion {args.crit_channelization}); "
              f"final max lowering {last_rec['max_lowering_m']:.2f} m")
    print(f" outflow volume {outflow:.3e} m3 of {LAKE_VOLUME:.2e} m3")
    print(f" pre-registered criterion met: {verdict['success']}  checks={verdict['checks']}")
    print(f" published context only: Qpeak ~{PUBLISHED['peak_discharge_m3s'][2]:.0f} m3/s (range "
          f"{PUBLISHED['peak_discharge_m3s'][0]:.0f}-{PUBLISHED['peak_discharge_m3s'][1]:.0f}); numeric proximity is not validation")
    d = summary["diagnostics"]
    print(f" balances: water {d['water_balance_err_m3']:+.2e}, reservoir {d['reservoir_balance_err_m3']:+.2e}, solids {d['sediment_balance_err_m3']:+.2e} m3")
    print(f" sediment sources [m3]: {d['sediment_sources_m3']}")
    print(f" speed clips: {d['speed_clip_events']} events, max uncapped {d['speed_clip_max_uncapped_ms']:.1f} m/s")
    print(f" outputs written to {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
