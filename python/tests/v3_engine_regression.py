"""Focused conservation and restart checks for the standalone V3 engine."""
from __future__ import annotations

import tempfile
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from breach_engine_2d_v3_2 import (
    BankStability,
    BankStabilityMethod,
    EngineConfig,
    Headcut,
    MaterialProps,
    ImpulseWave3D,
    LakeWaveBoundary,
    Reservoir,
    TransportFormula,
    UltimateBreachEngine,
    create_prism_mesh,
    make_demo_setup,
)


def build(order: int = 1, friction: str = "chezy") -> UltimateBreachEngine:
    mesh, reservoir, material, config = make_demo_setup()
    config.spatial_order = order
    config.friction_model = friction
    return UltimateBreachEngine(mesh, reservoir, material, config)


def assert_physical(engine: UltimateBreachEngine) -> None:
    assert np.all(np.isfinite(engine.mesh.h))
    assert np.all(np.isfinite(engine.mesh.z_b))
    assert np.all(engine.mesh.h >= 0.0)
    if engine.cfg.z_floor_enabled:
        assert np.all(engine.mesh.z_b >= engine.mesh.z_floor - 1e-12)
    assert engine.reservoir.volume >= 0.0
    assert abs(engine.water_balance_error()) < 1e-6
    assert abs(engine.reservoir_water_balance_error()) < 1e-6
    assert abs(engine.sediment_balance_error()) < 1e-6


def main() -> None:
    displaced = Reservoir({0.0: 0.0, 2.0: 100.0, 4.0: 400.0}, 2.0)
    water_before, stage_before = displaced.volume, displaced.level
    added_solid_volume = displaced.apply_displacement(10.0, 0.8)
    assert added_solid_volume == 8.0
    assert displaced.volume == water_before, "slide displacement must not create water mass"
    assert displaced.level > stage_before, "slide displacement should raise the lake stage"
    displaced.update(0.0, 1.0, 1.0)
    assert displaced.volume == water_before - 1.0

    for order, friction in ((1, "chezy"), (2, "chezy"), (1, "manning")):
        engine = build(order, friction)
        engine.run(4.0, Qin=0.5, verbose=False)
        assert_physical(engine)

    clip_engine = build()
    clip_engine.cfg.max_speed = 0.1
    clip_engine.run(0.5, Qin=0.5, verbose=False)
    assert clip_engine.hydro.speed_clip_events > 0
    assert clip_engine.hydro.speed_clip_locations

    # Bank screening comparison: steep, unsupported two-cell face; cohesion
    # increases resistance and lowers the computed collapse volume.
    collapse_volumes = []
    for cohesion in (0.0, 5_000.0):
        bank_mesh = create_prism_mesh(2.0, 2.0, 2, 2,
                                      np.asarray([[1.0, 1.0], [0.0, 0.0]]), 0.5,
                                      z_floor=-1.0)
        bank_mat = MaterialProps(cohesion=cohesion, phi=30.0)
        bank = BankStability(bank_mat, EngineConfig(bank_stability=BankStabilityMethod.CRITICAL_DEPTH))
        before = bank_mesh.solids_volume(bank_mat.porosity)
        moved = bank.check_and_collapse(bank_mesh)
        after = bank_mesh.solids_volume(bank_mat.porosity)
        assert abs(after - before) < 1e-10
        collapse_volumes.append(moved)
    assert collapse_volumes[0] > collapse_volumes[1]

    # Headcut laws retreat sub-cell faces and handle more than one scarp in a row.
    scarp_bed = np.asarray([[3.0, 3.0], [0.0, 0.0], [2.0, 2.0], [0.0, 0.0]])
    for law in ("energy", "temple", "sites"):
        scarp_mesh = create_prism_mesh(4.0, 2.0, 4, 2, scarp_bed.copy(), 3.5, z_floor=0.0)
        headcut_cfg = EngineConfig(headcut_method=law, headcut_C=0.1,
                                   headcut_threshold_A0=0.5, headcut_min_slope=0.1)
        headcut = Headcut(headcut_cfg, MaterialProps())
        lowered = headcut.migrate(scarp_mesh, np.ones_like(scarp_mesh.h), 1.0)
        assert lowered > 0.0
        assert scarp_mesh.z_b[0, 0] < scarp_bed[0, 0]
        assert scarp_mesh.z_b[2, 0] < scarp_bed[2, 0]
    kh_rates = [float(np.asarray(Headcut.sites_rate_from_Kh(np.asarray([1.0]), np.asarray([2.0]), kh))[0])
                for kh in (1.0, 100.0)]
    assert kh_rates[0] > 0.0 and kh_rates[1] > 0.0
    kh_mesh = create_prism_mesh(4.0, 2.0, 4, 2, scarp_bed.copy(), 3.5, z_floor=0.0)
    kh_headcut = Headcut(EngineConfig(headcut_method="sites", headcut_C=0.0,
                                      headcut_min_slope=0.1), MaterialProps(headcut_Kh=100.0))
    assert kh_headcut.migrate(kh_mesh, np.ones_like(kh_mesh.h), 1.0) > 0.0

    # BDI responds to depth, width and integrated area together.
    bdi_engine = build()
    baseline_bdi = bdi_engine.breach_development()["BDI"]
    crest_row = int(np.where(bdi_engine._crest_rows)[0][0])
    bdi_engine.mesh.z_b[crest_row, 9:11] -= 0.2
    narrow_bdi = bdi_engine.breach_development()["BDI"]
    bdi_engine.mesh.z_b[crest_row, 7:13] -= 0.2
    wide_bdi = bdi_engine.breach_development()["BDI"]
    assert baseline_bdi == 0.0 and narrow_bdi > baseline_bdi and wide_bdi > narrow_bdi

    # Compare the capacity laws and the 5/10 mm material cases on the same setup.
    formula_metrics = {}
    for formula in (TransportFormula.WU, TransportFormula.MPM, TransportFormula.VAN_RIJN):
        for d50 in (0.005, 0.010):
            mesh, reservoir, material, config = make_demo_setup(transport=formula)
            material.D50 = d50
            engine = UltimateBreachEngine(mesh, reservoir, material, config)
            initial_bed = mesh.z_b.copy()
            engine.run(20.0, Qin=0.5, verbose=False)
            assert_physical(engine)
            formula_metrics[f"{formula.value}_{d50:g}"] = {
                "max_lowering_m": float(np.max(initial_bed - engine.mesh.z_b)),
                "outlet_peak_m3s": engine.peak_Q_prism_outlet,
            }

    timestep_metrics = []
    for dt_max in (0.03, 0.015):
        dt_engine = build()
        dt_engine.cfg.dt_max_hydro = dt_max
        dt_engine.run(30.0, Qin=0.5, verbose=False)
        assert_physical(dt_engine)
        timestep_metrics.append(dt_engine.peak_Q_prism_outlet)
    dt_relative_change = abs(timestep_metrics[1] - timestep_metrics[0]) / max(timestep_metrics[1], 1e-12)
    assert dt_relative_change < 0.05, f"smaller-dt check did not converge within 5%: {dt_relative_change:.3%}"

    headcut_runs = []
    for enabled in (False, True):
        headcut_engine = build()
        headcut_engine.cfg.headcut_enabled = enabled
        headcut_engine.run(10.0, Qin=0.5, verbose=False)
        assert_physical(headcut_engine)
        headcut_runs.append(float(np.max(np.maximum(headcut_engine._initial_bed - headcut_engine.mesh.z_b, 0.0))))

    reference = build()
    reference.run(3.0, Qin=0.5, verbose=False)
    reference.run(6.0, Qin=0.5, verbose=False)

    split = build()
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        checkpoint = Path(folder) / "restart.npz"
        split.run(3.0, Qin=0.5, verbose=False,
                  checkpoint_path=str(checkpoint), checkpoint_interval_s=1.0)
        assert checkpoint.exists(), "periodic checkpoint was not written"
        resumed = build()
        resumed.load_checkpoint(str(checkpoint))
        resumed.run(6.0, Qin=0.5, verbose=False)
        assert_physical(resumed)
        assert np.allclose(resumed.mesh.h, reference.mesh.h, rtol=0.0, atol=1e-11)
        assert np.allclose(resumed.mesh.z_b, reference.mesh.z_b, rtol=0.0, atol=1e-11)
        assert np.allclose(resumed.mesh.S, reference.mesh.S, rtol=0.0, atol=1e-11)
        assert abs(resumed.cum_Q_left - reference.cum_Q_left) < 1e-9
        snapshots = Path(folder) / "snapshots"
        snap_engine = build()
        snap_engine.run(0.6, Qin=0.5, verbose=False, snapshot_dir=str(snapshots), snapshot_interval_s=0.2)
        assert list(snapshots.glob("field_*.npz")), "periodic field snapshots were not written"

    peak_case = build()
    peak_case.run(20.0, Qin=0.5, verbose=False, stop_at_peak=True, peak_confirm_steps=10)
    # A rising hydrograph at the end of the window must not be misreported as a peak.
    assert peak_case.stop_reason is None

    wave = LakeWaveBoundary(ImpulseWave3D(
        fall_height=10.0, slide_speed=14.0, slide_volume=1_000.0,
        thickness=2.0, slide_width=20.0, slide_density=1_200.0,
        porosity_percent=35.0, impact_angle_deg=45.0, lake_depth=3.0,
        distance_to_dam=40.0,
    ), depth_profile=np.asarray([3.0, 3.0]))
    y = np.linspace(0.5, 19.5, 20)
    assert np.max(wave.surface_displacement(0.0, y)) == 0.0
    ac1, at1, ac2, c1, c2, period, t1, t2 = wave._components(0.0)
    pulse_width = period / 3.0
    assert wave.surface_displacement(t1, np.asarray([10.0]))[0] > 0.0
    assert wave.surface_displacement(t1 + pulse_width, np.asarray([10.0]))[0] < 0.0
    assert wave.surface_displacement(t2 + 2.0 * pulse_width, np.asarray([10.0]))[0] > 0.0
    lateral_wave = wave.surface_displacement(t1, np.asarray([0.5, 10.0, 19.5]))
    assert lateral_wave[0] != lateral_wave[1] and lateral_wave[1] != lateral_wave[2]
    shallow_route = LakeWaveBoundary(wave.wave, depth_profile=np.asarray([3.0, 2.0]))
    assert shallow_route._components(0.0)[0] > ac1

    # Flat free surface over a sloping bed is a well-balanced still-water state.
    from breach_engine_2d_v3_2 import Hydrodynamics
    slope_bed = np.repeat(np.linspace(0.0, 1.0, 12)[:, None], 4, axis=1)
    still_mesh = create_prism_mesh(12.0, 4.0, 12, 4, slope_bed, 2.0)
    still_config = EngineConfig(spatial_order=2)
    still_hydro = Hydrodynamics(still_config)
    still_h0 = still_mesh.h.copy()
    still_hydro.step(still_mesh, 2.0, 0.01)
    assert np.max(np.abs(still_mesh.u)) < 1e-10 and np.max(np.abs(still_mesh.v)) < 1e-10
    assert np.max(np.abs(still_mesh.h - still_h0)) < 1e-10
    wave_mesh, wave_res, wave_mat, wave_cfg = make_demo_setup()
    wave_engine = UltimateBreachEngine(wave_mesh, wave_res, wave_mat, wave_cfg)
    wave_engine.run(15.0, Qin=0.5, verbose=False, wave_boundary=wave)
    assert_physical(wave_engine)
    print("V3 regression checks passed: conservation, Chezy/Manning, MUSCL, restart, snapshots, peak guard, wave-boundary mass accounting, speed clipping, cohesion screening, headcut laws, BDI progression, and transport formula cases")
    print("Transport law and D50 comparisons:", formula_metrics)
    print(f"Hydro time-step peak-flux change: {dt_relative_change:.3%} for dt_max 0.03 to 0.015 s")
    print("Headcut off/on maximum lowering [m]:", headcut_runs)
    print("Culmann screening collapsed bulk volumes [c=0, 5 kPa]:", collapse_volumes)


if __name__ == "__main__":
    main()
