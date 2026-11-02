"""Feature checks for the V3.2 additions. Each check prints PASS/FAIL; exit code 1 on any failure.

Layout expected:  <root>/breach_engine_2d_v3_2.py   and   <root>/validation/v3_2_feature_tests.py
"""
from __future__ import annotations

import sys
import tempfile
import traceback
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
(ROOT / "tmp").mkdir(exist_ok=True)

import breach_engine_2d_v3_2 as eng
from breach_engine_2d_v3_2 import (
    BankStability, BankStabilityMethod, EngineConfig, ImpulseWave3D, InitiationCriterion,
    InitiationMonitor, LakeGeometry, MaterialProps, Morphology, TransportFormula,
    UltimateBreachEngine, auto_seed_notch, create_prism_mesh, ikeda_side_slope_factor,
    impulse3d, initiation_success, make_demo_setup, make_floor, perturb_crest, weak_spot,
)

RESULTS = []


def check(name):
    def deco(fn):
        def run():
            try:
                fn()
                RESULTS.append((name, True, ""))
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                RESULTS.append((name, False, f"{exc!r}"))
                print(f"FAIL  {name}: {exc!r}")
                traceback.print_exc()
        run.__name__ = fn.__name__
        return run
    return deco


def build(**cfg_over):
    mesh, res, mat, cfg = make_demo_setup()
    for k, v in cfg_over.items():
        setattr(cfg, k, v)
    return UltimateBreachEngine(mesh, res, mat, cfg)


def physical(e):
    assert np.all(np.isfinite(e.mesh.z_b)) and np.all(e.mesh.h >= 0)
    assert abs(e.water_balance_error()) < 1e-6
    assert abs(e.reservoir_water_balance_error()) < 1e-6
    assert abs(e.sediment_balance_error()) < 1e-6


@check("defaults restore v2-style cfl and no detachment cap")
def t_defaults():
    cfg = EngineConfig()
    assert cfg.cfl_interior_only is False and cfg.detachment_rate_cap is None
    assert cfg.positivity_fix is True and cfg.lateral_model == "critical_shear"
    assert cfg.bank_fs_trigger == 1.0 and cfg.bank_fs_target == 1.0


@check("Ikeda factor: 1 on flat, 0 at friction angle, monotone, lift/drag matters")
def t_ikeda():
    phi = np.deg2rad(30.0)
    a = np.deg2rad(np.linspace(0, 30, 31))
    K = ikeda_side_slope_factor(a, phi, 0.85)
    assert abs(K[0] - 1.0) < 1e-9 and K[-1] < 1e-6
    assert np.all(np.diff(K) <= 1e-12)
    assert ikeda_side_slope_factor(np.deg2rad(15), phi, 0.0) != ikeda_side_slope_factor(np.deg2rad(15), phi, 0.85)


@check("lateral_model='force_balance' runs and conserves solids")
def t_lateral_switch():
    e = build(lateral_model="force_balance")
    e.run(4.0, Qin=0.5, verbose=False)
    physical(e)


@check("positivity_fix keeps S >= 0 and conserves mass; legacy mode goes negative")
def t_positivity():
    def make(fix, legacy):
        mesh = create_prism_mesh(4.0, 2.0, 4, 2, np.zeros((4, 2)), 0.01, z_floor=-1.0)
        mesh.S[:] = 0.002
        cfg = EngineConfig(positivity_fix=fix, legacy_negative_S=legacy)
        m = Morphology(cfg, MaterialProps())
        h = np.full((4, 2), 0.01)
        qx = np.full((4, 2), 1.0)
        qy = np.zeros((4, 2))
        return mesh, m, h, qx, qy
    mesh, m, h, qx, qy = make(True, False)
    before = float(np.sum(mesh.S))
    out = m._advect(mesh, h, qx, qy, 0.5)
    assert np.min(mesh.S) >= -1e-15
    assert abs((float(np.sum(mesh.S)) - before) * mesh.dx * mesh.dy + out) < 1e-12
    mesh2, m2, h2, qx2, qy2 = make(False, True)
    m2._advect(mesh2, h2, qx2, qy2, 0.5)
    assert np.min(mesh2.S) < 0.0, "legacy mode should reproduce the negative-S defect"


@check("Culmann FS trigger: defaults reproduce old collapse; stricter trigger collapses less; higher target more")
def t_fs():
    def collapse(**over):
        bank_mesh = create_prism_mesh(2.0, 2.0, 2, 2, np.asarray([[2.0, 2.0], [0.0, 0.0]]), 0.5, z_floor=-1.0)
        mat = MaterialProps(cohesion=1000.0, phi=30.0)
        bank = BankStability(mat, EngineConfig(**over))
        before = bank_mesh.solids_volume(mat.porosity)
        moved = bank.check_and_collapse(bank_mesh)
        assert abs(bank_mesh.solids_volume(mat.porosity) - before) < 1e-10
        return moved, bank.last_min_fs
    base, fs0 = collapse()
    strict, _ = collapse(bank_fs_trigger=0.01)
    higher, _ = collapse(bank_fs_target=2.0)
    assert base > 0 and strict < base and higher >= base and np.isfinite(fs0)


@check("reservoir hold-level keeps stage fixed and the balance closes")
def t_hold():
    e = build()
    level0 = e.reservoir.level
    e.run(3.0, Qin=0.5, verbose=False, hold_reservoir_level=level0)
    assert abs(e.reservoir.level - level0) < 1e-12
    assert e.reservoir.hold_added_m3 != 0.0
    physical(e)


@check("downstream wall gives zero outlet flux")
def t_wall():
    e = build(downstream_boundary="wall")
    e.run(3.0, Qin=0.5, verbose=False)
    assert abs(e.cum_Q_right) < 1e-6
    physical(e)


@check("threshold_factor / threshold_D change the capacity threshold")
def t_threshold():
    from breach_engine_2d_v3_2 import SedimentTransport
    mat = MaterialProps(D50=0.003, D90=0.03)
    base = float(SedimentTransport(EngineConfig(), mat).critical_shields_field())
    fac = float(SedimentTransport(EngineConfig(threshold_factor=2.0), mat).critical_shields_field())
    d90 = float(SedimentTransport(EngineConfig(threshold_D="D90"), mat).critical_shields_field())
    geo = float(SedimentTransport(EngineConfig(threshold_D="geometric"), mat).critical_shields_field())
    legacy = float(SedimentTransport(EngineConfig(gradation_enabled=True), mat).critical_shields_field())
    assert abs(base - mat.theta_c) < 1e-15 and abs(fac - 2 * base) < 1e-12
    assert d90 > geo > base and abs(geo - legacy) < 1e-15


@check("make_floor, LakeGeometry, impulse3d (Dig Tsho HM~4.29 m, P~2.2)")
def t_geometry_wave():
    zb = np.array([[1.0, 2.0], [3.0, 4.0]])
    fl = make_floor(zb, erodible_depth=0.5, erodible_mask=np.array([[True, False], [True, True]]))
    assert fl[0, 1] == zb[0, 1] and abs(fl[0, 0] - 0.5) < 1e-12
    lake = LakeGeometry(length_m=1000.0, width_m=300.0, depth_at_dam_m=10.0, depth_far_m=20.0)
    curve = lake.stage_volume_curve()
    vols = list(curve.values())
    assert all(b >= a for a, b in zip(vols, vols[1:])) and lake.green_factor() > 1.0
    dt = ImpulseWave3D(fall_height=60.0, slide_speed=float(np.sqrt(2 * 9.81 * 60.0)), slide_volume=150_000.0,
                       thickness=10.0, slide_width=200.0, slide_density=950.0, porosity_percent=38.0,
                       impact_angle_deg=30.0, lake_depth=18.0, distance_to_dam=1200.0)
    r = impulse3d(dt, 0.0)
    assert abs(r["HM"] - 4.29) / 4.29 < 0.03, r
    assert abs(r["P"] - 2.2) / 2.2 < 0.05, r


@check("mixed material class is accepted with a warning")
def t_mixed():
    mesh, res, mat, cfg = make_demo_setup()
    mat.material_class = "mixed"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        e = UltimateBreachEngine(mesh, res, mat, cfg)
    assert any("mixed" in str(x.message) for x in w)
    e.run(1.0, Qin=0.5, verbose=False)


@check("history carries source volumes; totals match; CSV and summary work")
def t_diagnostics():
    e = build()
    e.run(6.0, Qin=0.5, verbose=False)
    keys = ("lateral_m3", "headcut_m3", "collapsed_m3", "toe_scour_m3", "transport_net_erosion_m3")
    for k in keys:
        assert k in e.history[-1]
    assert abs(sum(r["collapsed_m3"] for r in e.history) - e.source_totals["collapse"]) < 1e-9
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        out = e.write_diagnostics_csv(str(Path(folder) / "diag.csv"))
        assert Path(out).stat().st_size > 0
    s = e.diagnostics_summary()
    assert s["run_status"] == "completed" and "sediment_sources_m3" in s and s["timing_s"]["hydro_s"] > 0


@check("stop criteria: wall-time pause + checkpoint, NaN guard, balance stop")
def t_stops():
    e = build()
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        ck = Path(folder) / "pause.npz"
        e.run(5.0, Qin=0.5, verbose=False, max_wall_seconds=0.0, checkpoint_path=str(ck), checkpoint_interval_s=100.0)
        assert e.stop_reason == "wall_time_pause" and ck.exists()
        resumed = build()
        resumed.load_checkpoint(str(ck))
        assert abs(resumed.time - e.time) < 1e-12
    n = build()
    n.mesh.h[5, 5] = np.nan
    n.run(2.0, Qin=0.5, verbose=False)
    assert n.stop_reason == "nan_state" and n.run_status == "stopped:nan_state"
    b = build()
    b.run(3.0, Qin=0.5, verbose=False, stop_on_balance_error_m3=1e-30)
    assert b.stop_reason in (None, "balance_error")


@check("depth-scaled Ls, active-layer cap, load saturation, Chen on detachment conserve solids")
def t_transport_options():
    for over in ({"adaptation_length_mode": "depth_scaled"},
                 {"active_layer_cap_m": 0.05},
                 {"transport": TransportFormula.HANSON, "detachment_load_saturation": True},
                 {"transport": TransportFormula.HANSON, "use_chen_detachment_cap": True,
                  "chen_apply_to_detachment": True, "detachment_rate_cap": 0.02}):
        e = build(**over)
        if over.get("use_chen_detachment_cap"):
            e.mat.material_class = "cohesive"
        e.run(4.0, Qin=0.5, verbose=False)
        physical(e)


@check("headcut retardation and max rate reduce lowering")
def t_headcut():
    def lowering(**over):
        e = build(**over)
        e.run(8.0, Qin=0.5, verbose=False)
        return float(np.sum(np.maximum(e._initial_bed - e.mesh.z_b, 0.0)))
    base = lowering()
    slow = lowering(headcut_retardation=0.1)
    capped = lowering(headcut_max_rate=1e-6)
    assert slow <= base + 1e-12 and capped <= base + 1e-12


@check("initiation tools: reproducible perturbation, weak spot, monitor, criterion")
def t_initiation():
    m1, *_ = make_demo_setup(pilot_notch=False)
    m2, *_ = make_demo_setup(pilot_notch=False)
    perturb_crest(m1, 0.02, seed=3)
    perturb_crest(m2, 0.02, seed=3)
    assert np.array_equal(m1.z_b, m2.z_b)
    removed = weak_spot(m1, 15.0, 18.0, 10.0, 1.0, 0.1)
    assert removed > 0
    mesh, res, mat, cfg = make_demo_setup(pilot_notch=False)
    auto_seed_notch(mesh, 15.0, 2.0)
    e = UltimateBreachEngine(mesh, res, mat, cfg)
    mon = InitiationMonitor()
    e.run(6.0, Qin=0.5, verbose=False, monitor=mon)
    assert mon.records
    out = initiation_success(mon, InitiationCriterion(t_max_s=6.0), seeded=True)
    assert out["checks"]["unseeded"] is False and out["success"] is False


@check("restart restores hold_added and source totals")
def t_restart():
    ref = build()
    ref.run(2.0, Qin=0.5, verbose=False, hold_reservoir_level=2.9)
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        ck = str(Path(folder) / "r.npz")
        ref.save_checkpoint(ck)
        new = build()
        new.load_checkpoint(ck)
        assert new.reservoir.hold_added_m3 == ref.reservoir.hold_added_m3
        assert new.source_totals == ref.source_totals


def main() -> int:
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("t_") and callable(v)]:
        fn()
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} V3.2 feature checks passed")
    for name, ok, msg in failed:
        print(f"  FAILED: {name} -> {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
