"""
Dam Breach Studio — V3.2 numerical engine
=========================================

Current architecture: 2-D hydrostatic shallow-water prism with a 0-D reservoir,
quasi-steady sediment transport/Exner updates, and optional reduced incident
impulse-wave boundary. The upstream boundary flux updates reservoir storage.

Implemented in this V3 file
---------------------------
* Hydrostatic finite-volume SWE (hydrostatic reconstruction + HLL), wet/dry
  handling, adaptive CFL, Chezy or Manning friction, first-order or MUSCL.
* Water and solids balance diagnostics; reservoir-curve overflow/dry-ghost
  warnings; clearly named prism outlet flux.
* Wu, MPM, van Rijn capacity laws and Partheniades/Hanson detachment options;
  Exner exchange with bed-floor limiting, optional Chen cap and rate ceiling.
* Optional VAW-style 3-D crest/trough/crest impulse boundary, transverse angle
  variation, reduced 1-D lake travel-time/shoaling correction and outgoing
  characteristic absorption. Wave forcing and avalanche displacement are
  separate: boundary flux is charged to reservoir storage, displacement is a
  one-time initial storage change supplied by the caller.
* Time-based morphology cadence, diagnostics, field snapshots, atomic restart,
  peak-stop guard, breach depth/width/area index and speed-clip location logs.
* Optional pilot/auto-seeded notches, reproducible crest perturbations and
  variable grid dimensions for sensitivity studies.

V3.2 additions (defaults keep v2-style behaviour except the positivity fix)
--------------------------------------------------------------------------
* positivity_fix (default on) limits advective outflow to the solids present,
  so S cannot go negative; legacy_negative_S=True reproduces the old defect.
* Reservoir hold-level, stop criteria (wall-time pause with checkpoint,
  mass-balance stop, NaN guard), run_status, timing split, per-morph source
  volumes in history, diagnostics_summary() and write_diagnostics_csv().
* threshold_D / threshold_factor for the capacity threshold, bank threshold
  factor and bank exponent, depth-scaled Ls, active-layer cap (numerical),
  detachment load saturation, optional Chen cap on the detachment branch.
* lateral_model='force_balance': Ikeda-type grain force balance (lift/drag).
* bank_fs_trigger / bank_fs_target: factor-of-safety collapse trigger and
  target around the Culmann critical height (defaults equal the old rule).
* headcut_retardation / headcut_max_rate, downstream_boundary='wall'.
* material_class 'mixed' is reserved (accepted with a warning, behaves as
  noncohesive). make_floor, LakeGeometry, impulse3d, InitiationMonitor,
  initiation_success, perturb_crest, weak_spot, auto_seed_notch.

Known limits; these are not completed physical modules
------------------------------------------------------
* The lake routing is a reduced travel-time/energy correction, not a full 1-D
  shallow-water lake solver. VAW near-field output is a screening fallback.
* The prism uses hydrostatic SWE; non-hydrostatic correction and local VOF are
  not implemented. No downstream flood routing is included.
* Material is spatially uniform. Layered moraine/ice-rich zones, thermal
  effects, ice melt, collapse and explicit active-layer hiding/exposure are
  not implemented. D50–D90 threshold spread is screening only.
* Lateral erosion defaults to a critical-shear reduction (Lane/Julien) with
  fractional bed retreat; lateral_model='force_balance' selects an Ikeda-type
  grain force balance. Neither resolves sub-cell wall retreat. Bank collapse
  uses a local Culmann screening proxy
  only at dry unsupported banks beside wet toes; pore-pressure loading and
  true unsupported-bank limit-equilibrium are not implemented. Bishop and
  Spencer are not implemented and do not silently claim to be.
* Headcut advance supports Temple/Hanson energy, Temple (1992), and SITES
  forms, but their coefficients remain user-calibrated; mesh convergence still
  requires case testing.
* The breach-development index is a geometric diagnostic for this prism, not
  an empirically validated maturity law. No published case agreement is claimed.

Run `validation/v3_engine_regression.py` for the focused conservation/restart
checks. Calibration and field-scale validation remain required.
"""

from __future__ import annotations
import csv
import hashlib
import json
import os
import time
import warnings
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np


# =============================================================================
# 1. ENUMS & CONFIGURATION
# =============================================================================

class TransportFormula(str, Enum):
    WU = "wu"                      # capacity (bed load)
    VAN_RIJN = "vanRijn"           # capacity (bed load)
    MPM = "mpm"                    # capacity (bed load)
    PARTHENIADES = "partheniades"  # detachment-limited (cohesive)
    HANSON = "hanson"              # detachment-limited (excess shear, JET)


class BankStabilityMethod(str, Enum):
    CRITICAL_DEPTH = "criticalDepth"
    SIMPLIFIED_BISHOP = "simplifiedBishop"
    FULL_SPENCER = "fullSpencer"


class FreeSurfaceMethod(str, Enum):
    HEIGHT_FUNCTION = "heightFunction"
    LOCAL_VOF = "localVOF"


@dataclass
class MaterialProps:
    """Geotechnical & sediment properties of one uniform material.

    ``theta_c`` is the sole mobility threshold for capacity formulas; ``tau_c``
    is the detachment threshold for Partheniades/Hanson and the default bank
    threshold. ``bank_tau_c`` can override the bank threshold explicitly.
    """
    rho_s: float = 2650.0       # grain density [kg/m3]
    rho_w: float = 1000.0       # water density [kg/m3]
    material_class: str = "noncohesive"  # cohesive or noncohesive; selects applicable erosion limits
    porosity: float = 0.35      # bed porosity p [-]
    D50: float = 0.005          # median grain size [m]
    D90: float = 0.02           # [m]
    cohesion: float = 5000.0    # c [Pa]
    phi: float = 30.0           # friction angle [deg]
    theta_c: float = 0.047      # critical Shields number (non-cohesive)
    tau_c: float = 2.0          # critical shear for detachment laws / banks [Pa]
    # Chen-type hyperbolic detachment law: E = scale * k*ex / (a + b*ex)
    chen_k: float = 100.0
    chen_a: float = 1.0
    chen_b: float = 0.5
    chen_scale: float = 1e-3    # calibration scale (units -> m/s)
    # Hanson / Partheniades / bank erodibility
    kd: float = 1e-4            # erodibility [m/s per Pa^n]
    n_exp: float = 1.0
    headcut_Kh: Optional[float] = None  # NRCS SITES dimensionless headcut erodibility index


@dataclass
class EngineConfig:
    """User-selectable switches and numerical controls."""
    transport: TransportFormula = TransportFormula.WU
    bank_stability: BankStabilityMethod = BankStabilityMethod.CRITICAL_DEPTH
    free_surface: FreeSurfaceMethod = FreeSurfaceMethod.HEIGHT_FUNCTION
    use_non_hydrostatic: bool = False
    use_slope_effect: bool = True
    slope_beta: float = 1.0               # slope-enhancement strength (screening)
    use_chen_detachment_cap: bool = False  # cap entrainment by Chen rate (cohesive)

    g: float = 9.81
    # --- hydrodynamics
    CFL: float = 0.4
    dt_max_hydro: float = 0.2
    h_dry: float = 1e-3
    max_speed: float = 25.0               # safety clip [m/s]
    chezy_C: float = 40.0
    friction_model: str = "chezy"         # "chezy" or "manning"
    manning_n: float = 0.035
    spatial_order: int = 1                # 1 or MUSCL 2 (minmod)
    cfl_interior_only: bool = False       # True excludes imposed ghost states from the CFL estimate (v2 includes them)
    # --- morphology (quasi-steady coupling)
    dt_morpho_factor: int = 5             # morph update every N flow steps
    dt_morpho_target: Optional[float] = None  # seconds; overrides step-count cadence
    morph_accel: float = 1.0              # morphological acceleration factor
    adaptation_length: float = 5.0        # non-equilibrium length Ls [m]
    sed_CFL: float = 0.5
    max_dz_per_substep: float = 0.02      # [m]
    # --- switches for sub-processes
    lateral_erosion_enabled: bool = True
    headcut_enabled: bool = True
    bank_collapse_enabled: bool = True
    collapse_iterations: int = 3
    # --- headcut
    headcut_C: float = 0.05               # m/s per (m3/s)^(1/3)
    headcut_method: str = "energy"       # energy, temple, sites
    headcut_threshold_A0: float = 0.0     # SITES threshold [m/s]
    headcut_min_slope: float = 0.5        # dimensionless scarp threshold, not a grid-dependent drop [m/m]
    log_speed_clip_limit: int = 100
    chen_cap_materials: Tuple[str, ...] = ("cohesive",)
    detachment_rate_cap: Optional[float] = None  # [m/s]; None = no ceiling (v2). 0.02 is a placeholder, not calibrated
    bed_shear_average: str = "time_average"     # time_average or instantaneous
    gradation_enabled: bool = False
    z_floor_enabled: bool = True
    near_bank_shear_factor: float = 1.0
    bank_tau_c: Optional[float] = None
    bank_kd: Optional[float] = None
    toe_scour_factor: float = 0.0
    # ---- V3.2 additions
    positivity_fix: bool = True            # limit advective outflow to available solids
    legacy_negative_S: bool = False        # True reproduces the old negative-S defect
    downstream_boundary: str = "transmissive"   # "transmissive" (edge copy), "wall", or "outfall" (dry ghost, free overfall)
    threshold_D: str = "D50"               # capacity threshold grain: D50, geometric, D90
    threshold_factor: float = 1.0          # multiplier on theta_c (capacity laws)
    bank_threshold_factor: float = 1.0     # multiplier on bank critical shear
    bank_n_exp: Optional[float] = None     # bank erosion exponent (None -> material n_exp)
    adaptation_length_mode: str = "fixed"  # fixed or depth_scaled
    adaptation_depth_factor: float = 5.0   # Ls = max(factor*h, dx) when depth_scaled
    active_layer_cap_m: Optional[float] = None  # numerical cap on solids in transport (bulk m); not a physical active layer
    detachment_load_saturation: bool = False    # entrainment scaled by (1 - S / (c_max h))
    detachment_max_concentration: float = 0.05  # solids volume fraction for the saturation law
    chen_apply_to_detachment: bool = False      # also cap the detachment branch by Chen
    lateral_model: str = "critical_shear"  # or "force_balance" (Ikeda-type)
    lateral_lift_drag: float = 0.85        # lift/drag ratio for the force balance
    bank_fs_trigger: float = 1.0           # collapse when Culmann FS = Zc/H is below this
    bank_fs_target: float = 1.0            # collapse to height Zc/target (floored at friction angle)
    headcut_retardation: float = 1.0       # multiplier on headcut advance rate
    headcut_max_rate: Optional[float] = None    # [m/s] ceiling on headcut advance rate
    initiation_diagnostics: bool = True
    # ---- V3.2.2 (Step 0)
    erosion_shear: str = "total"          # "total" (v3.2.1) or "grain": erosion driven by skin-friction shear
    grain_manning_n: Optional[float] = None  # n' for grain shear; None -> Strickler D50^(1/6)/21.1 (D50 in m)
    breach_width_fraction: float = 0.5    # breach width counts columns lowered >= this fraction of the max (0 = legacy)
    transport_capacity_factor: float = 1.0  # calibration multiplier on capacity-law transport (Wu, MPM, van Rijn)
    eps: float = 1e-12


# =============================================================================
# 2. STRUCTURED MULTI-COLUMN MESH
# =============================================================================

@dataclass
class MeshState:
    """
    Structured Cartesian prism.  i = longitudinal (flow, +x), j = transverse.
    Water depth h is the prognostic variable (eta = z_b + h is derived).
    S is the sediment field: volume of SOLIDS in transport per unit bed area [m].
    """
    nx: int
    ny: int
    dx: float
    dy: float
    x: np.ndarray
    y: np.ndarray
    z_b: np.ndarray
    z_floor: np.ndarray            # non-erodible base [m]
    h: np.ndarray
    u: np.ndarray
    v: np.ndarray
    S: np.ndarray
    tau_b: np.ndarray
    headcut_i: int = 0

    @property
    def eta(self) -> np.ndarray:
        return self.z_b + self.h

    @property
    def wet(self) -> np.ndarray:
        return self.h > 1e-3

    def water_volume(self) -> float:
        return float(np.sum(self.h) * self.dx * self.dy)

    def solids_volume(self, porosity: float) -> float:
        """Solids in bed + solids in transport [m3]."""
        return float((np.sum((1.0 - porosity) * self.z_b) + np.sum(self.S))
                     * self.dx * self.dy)


def create_prism_mesh(
    Lx: float, Ly: float, nx: int, ny: int,
    zb_init: np.ndarray,
    eta_init: Union[float, np.ndarray],
    z_floor: Optional[Union[float, np.ndarray]] = None,
) -> MeshState:
    """Create the prism. Water exists only where eta_init > z_b."""
    dx, dy = Lx / nx, Ly / ny
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dy
    z = zb_init.astype(float).copy()
    eta = np.broadcast_to(np.asarray(eta_init, dtype=float), z.shape)
    h = np.maximum(eta - z, 0.0)
    if z_floor is None:
        zf = np.full_like(z, float(np.min(z)))
    else:
        zf = np.broadcast_to(np.asarray(z_floor, dtype=float), z.shape).copy()
    return MeshState(nx=nx, ny=ny, dx=dx, dy=dy, x=x, y=y, z_b=z,
                     z_floor=zf, h=h, u=np.zeros_like(z), v=np.zeros_like(z),
                     S=np.zeros_like(z), tau_b=np.zeros_like(z))


# =============================================================================
# 3. RESERVOIR (0-D)
# =============================================================================

def make_floor(zb_init: np.ndarray, *, erodible_depth: Optional[Union[float, np.ndarray]] = None,
               erodible_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Build the non-erodible base for ``create_prism_mesh(z_floor=...)``.

    ``erodible_depth``: thickness of erodible material below the initial bed
    (None -> floor at the global minimum bed). ``erodible_mask``: True where
    erodible; False cells become rigid (floor equals the bed).
    """
    zb = np.asarray(zb_init, dtype=float)
    if erodible_depth is None:
        floor = np.full_like(zb, float(np.min(zb)))
    else:
        floor = zb - np.broadcast_to(np.asarray(erodible_depth, dtype=float), zb.shape)
    if erodible_mask is not None:
        mask = np.broadcast_to(np.asarray(erodible_mask, dtype=bool), zb.shape)
        floor = np.where(mask, floor, zb)
    return np.minimum(floor, zb)


@dataclass
class LakeGeometry:
    """Configurable idealised lake: length, width and a linear depth profile.

    Depth varies linearly from ``depth_far_m`` (impact end) to
    ``depth_at_dam_m``. Used for the wave travel path (Green's law shoaling)
    and for a stage-volume curve. Idealised; not bathymetry.
    """
    length_m: float
    width_m: float
    depth_at_dam_m: float
    depth_far_m: Optional[float] = None
    bed_elev_at_dam: float = 0.0
    n_segments: int = 20

    def depth_profile(self) -> np.ndarray:
        far = self.depth_at_dam_m if self.depth_far_m is None else self.depth_far_m
        return np.linspace(far, self.depth_at_dam_m, max(self.n_segments, 1) + 1)

    def surface_area(self) -> float:
        return self.length_m * self.width_m

    def green_factor(self) -> float:
        """Green's-law depth amplification (h_far/h_dam)^(1/4)."""
        prof = self.depth_profile()
        return float((prof[0] / prof[-1]) ** 0.25)

    def stage_volume_curve(self, levels: Optional[np.ndarray] = None) -> Dict[float, float]:
        prof = self.depth_profile()
        full_level = self.bed_elev_at_dam + self.depth_at_dam_m
        beds = full_level - 0.5 * (prof[:-1] + prof[1:])
        seg_area = self.length_m / (prof.size - 1) * self.width_m
        if levels is None:
            levels = np.linspace(float(np.min(beds)), full_level + 1.0, 25)
        return {float(L): float(np.sum(np.maximum(L - beds, 0.0)) * seg_area) for L in levels}


class Reservoir:
    """Upstream storage. Its stage is the left boundary condition of the prism."""

    def __init__(self, volume_curve: Dict[float, float], initial_level: float):
        self.elevs = np.array(sorted(volume_curve.keys()), dtype=float)
        self.vols = np.array([volume_curve[e] for e in self.elevs], dtype=float)
        self.level = float(initial_level)
        self.volume = float(np.interp(self.level, self.elevs, self.vols))
        self.displaced_volume = 0.0
        self.curve_overflow_m3 = 0.0
        self._overflow_warned = False
        self._dry_warning_emitted = False
        self.hold_level: Optional[float] = None   # fixed stage for diagnostics
        self.hold_added_m3 = 0.0                  # water added/removed to hold it
        # V3.2.1: the prism may not draw more water in a step than the lake holds
        # (positivity limit on the upstream face). legacy_unlimited_draw=True restores the
        # old behaviour: with a displaced (slide) volume the empty lake kept the debris-top
        # stage and kept feeding the prism, and the deficit was clipped (phantom water).
        self.legacy_unlimited_draw = False
        self.empty_tol_m3 = 1e-6
        self.clipped_m3 = 0.0                     # water demanded beyond storage

    @property
    def empty(self) -> bool:
        return self.volume <= self.empty_tol_m3

    def level_from_volume(self, V: float) -> float:
        """Convert actual water storage to level, accounting for displaced basin volume."""
        return float(np.interp(V + self.displaced_volume, self.vols, self.elevs))

    def apply_displacement(self, slide_volume: float, submerged_fraction: float) -> float:
        """Apply slide displacement without adding non-water volume to storage.

        The stage-volume curve represents basin capacity. Submerged slide
        volume offsets that curve; ``self.volume`` remains actual lake water.
        Returns the added submerged displacement [m3].
        """
        added = max(slide_volume, 0.0) * float(np.clip(submerged_fraction, 0.0, 1.0))
        self.displaced_volume += added
        self.level = self.level_from_volume(self.volume)
        self.curve_overflow_m3 = max(self.volume + self.displaced_volume - self.vols[-1], 0.0)
        if self.curve_overflow_m3 > 0.0 and not self._overflow_warned:
            warnings.warn("reservoir plus displaced volume exceeds the supplied stage-volume curve; stage is clamped at its upper bound", stacklevel=2)
            self._overflow_warned = True
        return added

    def update(self, Qin: float, Qout: float, dt: float) -> float:
        """Qout = water that actually enters the prism through its upstream face."""
        proposed = self.volume + (Qin - Qout) * dt
        if proposed < 0.0:
            if -proposed > 1e-6 * max(abs(Qout) * dt, 1.0):   # round-off from the face limiter is not a clip
                warnings.warn("reservoir storage would become negative; water balance is being clipped", stacklevel=2)
            self.clipped_m3 += -proposed
        self.volume = max(0.0, proposed)
        if self.hold_level is not None:
            target = max(float(np.interp(self.hold_level, self.elevs, self.vols)) - self.displaced_volume, 0.0)
            self.hold_added_m3 += target - self.volume
            self.volume = target
            self.level = float(self.hold_level)
            self.curve_overflow_m3 = 0.0
            return self.level
        equivalent_volume = self.volume + self.displaced_volume
        if equivalent_volume > self.vols[-1]:
            self.curve_overflow_m3 = equivalent_volume - self.vols[-1]
            if not self._overflow_warned:
                warnings.warn("reservoir plus displaced volume exceeds the supplied stage-volume curve; stage is clamped at its upper bound", stacklevel=2)
                self._overflow_warned = True
        else:
            self.curve_overflow_m3 = 0.0
            self.level = float(np.interp(min(equivalent_volume, self.vols[-1]), self.vols, self.elevs))
        return self.level


# =============================================================================
# 3A. INCIDENT IMPULSE WAVE + 1-D LAKE-TO-DAM ROUTING
# =============================================================================

@dataclass
class ImpulseWave3D:
    """Inputs for the VAW/Heller-Hager style 3-D impulse-wave screening model."""
    fall_height: float
    slide_speed: float
    slide_volume: float
    thickness: float
    slide_width: float
    slide_density: float
    porosity_percent: float
    impact_angle_deg: float
    lake_depth: float
    distance_to_dam: float
    axis_y: Optional[float] = None


class LakeWaveBoundary:
    """Transient incident wave boundary routed across a reduced 1-D lake transect.

    VAW 3-D crest/trough/second-crest amplitudes are evaluated by angle across
    the prism width. Component travel times use their progressive-wave speeds;
    the inlet SWE boundary combines the prescribed incoming Riemann invariant
    with the outgoing invariant from the prism interior (absorbing boundary).
    A supplied depth profile applies a first-order shoaling correction and
    integrates component travel time segment by segment. A separate, explicit
    damping coefficient is optional because VAW's far-field amplitudes already
    include empirical propagation decay. This is a reduced travel-time/energy
    routing approximation, not a fully nonlinear 1-D SWE solver.
    """
    G = 9.81

    def __init__(self, wave: ImpulseWave3D, *, depth_profile: Optional[np.ndarray] = None,
                 damping_per_m: float = 0.0, lake: Optional[LakeGeometry] = None):
        if lake is not None and depth_profile is None:
            depth_profile = lake.depth_profile()
        self.wave = wave
        self.depth_profile = (np.asarray(depth_profile, dtype=float).reshape(-1)
                              if depth_profile is not None else np.asarray([wave.lake_depth]))
        if self.depth_profile.size == 0 or np.any(self.depth_profile <= 0):
            raise ValueError("lake depth_profile must contain positive depths")
        if damping_per_m < 0:
            raise ValueError("damping_per_m must be nonnegative")
        self.damping_per_m = float(damping_per_m)
        self.last_near_field = False
        self._cache: Dict[float, Tuple[float, float, float, float, float, float, float, float]] = {}

    @staticmethod
    def _sech(x: float) -> float:
        return 1.0 / np.cosh(x)

    def _components(self, gamma_deg: float) -> Tuple[float, float, float, float, float, float, float, float]:
        key = round(float(gamma_deg), 3)
        if key in self._cache:
            return self._cache[key]
        p, g = self.wave, self.G
        h, b = max(p.lake_depth, 1e-9), max(p.slide_width, 1e-9)
        s, vol = max(p.thickness, 1e-9), max(p.slide_volume, 1e-9)
        alpha = np.deg2rad(p.impact_angle_deg)
        cos_term = max(np.cos(6.0 / 7.0 * alpha), 0.0)
        F = max(p.slide_speed, 1e-9) / np.sqrt(g * h)
        S = s / h
        M = max(p.slide_density * vol / (1000.0 * b * h * h), 1e-9)
        B = b / h
        P = F * np.sqrt(S) * M**0.25 * np.sqrt(cos_term)
        r = max(p.distance_to_dam, 0.0)
        gr = np.deg2rad(gamma_deg)
        r00 = 2.5 * max(P * B * cos_term, 1e-9)**0.25 * h
        r090 = b / 2 + 1.5 * max(P * cos_term, 1e-9)**0.25 * h
        r0 = np.sqrt((r00 * r00 * r090 * r090) /
                     max(r00 * r00 * np.sin(gr)**2 + r090 * r090 * np.cos(gr)**2, 1e-12))
        rstar = r - r0
        a0c1 = 0.20 * max(P, 1e-9)**0.5 * B**0.75 * max(cos_term, 1e-9)**0.25 * h
        a0t1 = 0.35 * max(P * B * cos_term, 1e-9)**0.5 * h
        a0c2 = 0.14 * max(P * B * cos_term, 1e-9)**0.25 * h
        near = r < r0
        if near:
            ac1, at1, ac2 = a0c1, a0t1, a0c2
            c1, c2 = 0.95 * np.sqrt(g * (h + ac1)), 0.70 * np.sqrt(g * (h + ac2))
            T = 10.0 * ((ac1 + at1) / h)**0.2 * np.sqrt(h / g)
        else:
            rs = max(rstar, 0.0)
            sr = np.sqrt(rs / h)
            decay = cos_term * np.exp(-0.15 * sr)
            gamma_frac = gamma_deg / 90.0
            ac1 = a0c1 * np.exp(-0.4 * (max(a0c1, 1e-9) / h)**-0.3 * sr) * self._sech(3.2 * gamma_frac)**decay
            at1 = a0t1 * np.exp(-0.4 * (max(a0t1, 1e-9) / h)**-0.3 * sr) * self._sech(3.6 * gamma_frac)**decay
            ac2 = a0c2 * np.exp(-0.1 * (max(a0c2, 1e-9) / h)**-0.3 * sr) * self._sech(3.0 * gamma_frac)**decay
            c1, c2 = 0.95 * np.sqrt(g * (h + ac1)), 0.70 * np.sqrt(g * (h + ac2))
            T = (10.0 * ((ac1 + at1) / h)**0.2 + rs / (2.0 * h)) * np.sqrt(h / g)
        # 1-D lake path shoaling and user-specified energy-loss damping.
        h_source, h_dam = self.depth_profile[0], self.depth_profile[-1]
        route_factor = (h_source / h_dam)**0.25 * np.exp(-self.damping_per_m * p.distance_to_dam)
        # Preserve the VAW 3-D directional decay; apply only path-depth correction.
        ac1, at1, ac2 = ac1 * route_factor, at1 * route_factor, ac2 * route_factor
        segments = max(self.depth_profile.size - 1, 1)
        dx_route = p.distance_to_dam / segments
        if self.depth_profile.size == 1:
            path_depths = self.depth_profile
        else:
            path_depths = 0.5 * (self.depth_profile[:-1] + self.depth_profile[1:])
        t_c1 = float(np.sum(dx_route / (0.95 * np.sqrt(g * (path_depths + ac1)))))
        t_c2 = float(np.sum(dx_route / (0.70 * np.sqrt(g * (path_depths + ac2)))))
        self.last_near_field = near
        result = (float(ac1), float(at1), float(ac2), float(c1), float(c2), float(T), t_c1, t_c2)
        self._cache[key] = result
        return result

    def surface_displacement(self, time_s: float, y_m: np.ndarray) -> np.ndarray:
        p = self.wave
        y = np.asarray(y_m, dtype=float)
        axis_y = float(np.mean(y)) if p.axis_y is None else p.axis_y
        gamma = np.rad2deg(np.arctan2(y - axis_y, max(p.distance_to_dam, 1e-9)))
        out = np.zeros_like(y)
        for j, angle in enumerate(gamma):
            ac1, at1, ac2, c1, c2, period, t1, t2 = self._components(float(angle))
            width = max(period / 3.0, 1e-3)
            def pulse(center: float) -> float:
                phase = (time_s - center + width / 2.0) / width
                return float(np.sin(np.pi * phase)) if 0.0 < phase < 1.0 else 0.0
            out[j] = ac1 * pulse(t1) - at1 * pulse(t1 + width) + ac2 * pulse(t2 + 2.0 * width)
        return out

    def boundary_state(self, time_s: float, y_m: np.ndarray, bed_z: np.ndarray,
                       still_level: float) -> Tuple[np.ndarray, np.ndarray]:
        """Return incident stage and progressive-wave velocity at dam boundary."""
        eta = self.surface_displacement(time_s, y_m)
        h0 = np.maximum(still_level - bed_z, 0.0)
        eta = np.maximum(eta, -h0 + 1e-6)
        u_inc = eta * np.sqrt(self.G / np.maximum(h0, 1e-6))
        return still_level + eta, u_inc


def impulse3d(wave: ImpulseWave3D, gamma_deg: float = 0.0, *,
              depth_profile: Optional[np.ndarray] = None) -> Dict[str, float]:
    """VAW-style 3-D screening summary at angle gamma (for cross-checks against the TypeScript module)."""
    b = LakeWaveBoundary(wave, depth_profile=depth_profile)
    ac1, at1, ac2, c1, c2, T, t1, t2 = b._components(gamma_deg)
    g = LakeWaveBoundary.G
    h = max(wave.lake_depth, 1e-9)
    bw = max(wave.slide_width, 1e-9)
    cos_term = max(np.cos(6.0 / 7.0 * np.deg2rad(wave.impact_angle_deg)), 0.0)
    F = max(wave.slide_speed, 1e-9) / np.sqrt(g * h)
    S = max(wave.thickness, 1e-9) / h
    M = max(wave.slide_density * max(wave.slide_volume, 1e-9) / (1000.0 * bw * h * h), 1e-9)
    P = float(F * np.sqrt(S) * M ** 0.25 * np.sqrt(cos_term))
    return {"P": P, "aM": ac1, "HM": ac1 + at1, "TM": T, "ac1": ac1, "at1": at1, "ac2": ac2,
            "c1": c1, "c2": c2, "t_crest1_s": t1, "t_crest2_s": t2,
            "near_field": bool(b.last_near_field)}


# =============================================================================
# 4. HYDRODYNAMICS  --  well-balanced 2-D SWE (hydrostatic reconstruction + HLL)
# =============================================================================

def _hll_normal(hL, unL, utL, hR, unR, utR, g):
    """HLL flux in the face-normal direction. Returns (F_h, F_normal, F_tangential)."""
    cL, cR = np.sqrt(g * hL), np.sqrt(g * hR)
    sL = np.minimum(unL - cL, unR - cR)
    sR = np.maximum(unL + cL, unR + cR)
    dryL, dryR = hL <= 1e-12, hR <= 1e-12
    sL = np.where(dryL, unR - 2 * cR, sL)
    sR = np.where(dryL, unR + cR, sR)
    sL = np.where(dryR, unL - cL, sL)
    sR = np.where(dryR, unL + 2 * cL, sR)

    FLh, FRh = hL * unL, hR * unR
    FLn, FRn = hL * unL**2 + 0.5 * g * hL**2, hR * unR**2 + 0.5 * g * hR**2
    FLt, FRt = hL * unL * utL, hR * unR * utR
    den = sR - sL
    den = np.where(np.abs(den) < 1e-12, 1.0, den)

    def hll(FL, FR, UL, UR):
        mid = (sR * FL - sL * FR + sL * sR * (UR - UL)) / den
        return np.where(sL >= 0, FL, np.where(sR <= 0, FR, mid))

    return (hll(FLh, FRh, hL, hR),
            hll(FLn, FRn, hL * unL, hR * unR),
            hll(FLt, FRt, hL * utL, hR * utR))


def _minmod3(a, b, c):
    """Three-argument minmod limiter, applied elementwise."""
    same = (np.sign(a) == np.sign(b)) & (np.sign(b) == np.sign(c))
    return np.where(same, np.sign(a) * np.minimum(np.abs(a), np.minimum(np.abs(b), np.abs(c))), 0.0)


def _limited_slope(a: np.ndarray, axis: int) -> np.ndarray:
    """Piecewise-linear minmod slope for a one-cell-padded field."""
    out = np.zeros_like(a)
    if axis == 0:
        out[1:-1, :] = _minmod3(a[1:-1, :] - a[:-2, :],
                                0.5 * (a[2:, :] - a[:-2, :]),
                                a[2:, :] - a[1:-1, :])
        out[1, :] = 0.0
        out[-2, :] = 0.0
    else:
        out[:, 1:-1] = _minmod3(a[:, 1:-1] - a[:, :-2],
                                0.5 * (a[:, 2:] - a[:, :-2]),
                                a[:, 2:] - a[:, 1:-1])
        out[:, 1] = 0.0
        out[:, -2] = 0.0
    return out


class Hydrodynamics:
    def __init__(self, cfg: EngineConfig, rho_w: float = 1000.0, grain_n: Optional[float] = None):
        self.cfg = cfg
        self.rho_w = rho_w
        self.grain_n = grain_n
        self.last_tau_total_max = 0.0
        self.speed_clip_events = 0
        self.speed_clip_cells = 0
        self.speed_clip_max_uncapped = 0.0
        self.speed_clip_locations: Dict[Tuple[int, int], int] = {}
        self.inflow_limit_events = 0

    def _face_flux(self, hL, unL, utL, zL, hR, unR, utR, zR,
                   hL_cell=None, hR_cell=None):
        """Hydrostatic reconstruction (Audusse et al. 2004) + HLL."""
        g = self.cfg.g
        zf = np.maximum(zL, zR)
        hLs = np.maximum(hL + zL - zf, 0.0)
        hRs = np.maximum(hR + zR - zf, 0.0)
        Fh, Fn, Ft = _hll_normal(hLs, unL, utL, hRs, unR, utR, g)
        hcL = hL if hL_cell is None else hL_cell
        hcR = hR if hR_cell is None else hR_cell
        # Hydrostatic correction uses cell-average depths, while the HLL flux
        # uses MUSCL-reconstructed face states; this preserves lake-at-rest.
        FnL = Fn + 0.5 * g * (hcL**2 - hLs**2)   # flux seen by the left cell
        FnR = Fn + 0.5 * g * (hcR**2 - hRs**2)   # flux seen by the right cell
        return Fh, FnL, FnR, Ft

    def bed_shear(self, mesh: MeshState) -> np.ndarray:
        """Bed stress for erosion. 'total' uses the hydraulic roughness (Chezy or Manning);
        'grain' uses the skin-friction part tau' = rho g n'^2 U^2 / h^(1/3), capped at the total."""
        speed2 = mesh.u**2 + mesh.v**2
        hs = np.maximum(mesh.h, self.cfg.h_dry)
        if self.cfg.friction_model == "manning":
            tau = self.rho_w * self.cfg.g * self.cfg.manning_n**2 * speed2 / hs ** (1.0 / 3.0)
        else:
            tau = self.rho_w * self.cfg.g * speed2 / self.cfg.chezy_C**2
        wet = mesh.h > self.cfg.h_dry
        self.last_tau_total_max = float(np.max(np.where(wet, tau, 0.0)))
        if self.cfg.erosion_shear == "grain":
            n_g = self.grain_n
            if n_g is None or n_g <= 0:
                raise ValueError("erosion_shear='grain' needs a positive grain Manning n")
            tau_g = self.rho_w * self.cfg.g * n_g**2 * speed2 / hs ** (1.0 / 3.0)
            tau = np.minimum(tau, tau_g)
        mesh.tau_b = np.where(wet, tau, 0.0)
        return mesh.tau_b

    def step(self, mesh: MeshState, res_level: float, dt_limit: float, *,
             wave_boundary: Optional[LakeWaveBoundary] = None, time_s: float = 0.0,
             inflow_available: Optional[Tuple[float, float]] = None
             ) -> Tuple[float, float, float]:
        """
        Advance the flow one adaptive step.
        Returns (dt, Q_left, Q_right) with Q_left = discharge entering the
        prism from the reservoir [m3/s, + into prism], Q_right = outflow.
        """
        cfg, g = self.cfg, self.cfg.g
        nx, ny, dx, dy = mesh.nx, mesh.ny, mesh.dx, mesh.dy
        h, u, v, z = mesh.h, mesh.u, mesh.v, mesh.z_b

        pad = lambda a: np.pad(a, 1, mode="edge")
        hP, uP, vP, zP = pad(h), pad(u), pad(v), pad(z)
        # left: reservoir stage, or incident wave plus absorbing outgoing characteristic
        zP[0, :] = zP[1, :]
        hP[0, :] = np.maximum(res_level - zP[0, :], 0.0)
        uP[0, :] = 0.0
        vP[0, :] = 0.0
        if wave_boundary is not None:
            eta_inc, u_inc = wave_boundary.boundary_state(time_s, mesh.y, mesh.z_b[0, :], res_level)
            h_inc = np.maximum(eta_inc - mesh.z_b[0, :], 1e-6)
            r_plus = u_inc + 2.0 * np.sqrt(g * h_inc)
            r_minus = u[0, :] - 2.0 * np.sqrt(g * np.maximum(h[0, :], 0.0))
            uP[0, 1:-1] = 0.5 * (r_plus + r_minus)
            c_boundary = np.maximum(0.25 * (r_plus - r_minus), 0.0)
            hP[0, 1:-1] = c_boundary**2 / g
        # right: transmissive (edge copy). y-walls: reflective
        vP[:, 0] = -vP[:, 1]
        vP[:, -1] = -vP[:, -2]
        if cfg.downstream_boundary == "wall":
            uP[-1, :] = -uP[-2, :]   # mirrored state -> zero mass flux at the right face
        elif cfg.downstream_boundary == "outfall":
            # Dry ghost cell: a free overfall. The default transmissive edge copy cannot drain a
            # still pond (no head difference across the last face), so a released lake fills the
            # whole prism and stalls at the lake stage. With a dry ghost the HLL solver lets the
            # last cell discharge (about 2/3*h*c per unit width for a still pond; supercritical
            # outflow is unchanged). Opt-in; the default is unchanged.
            hP[-1, :] = 0.0

        # adaptive time step from wave speeds (ghosts included)
        if cfg.cfl_interior_only:
            c = np.sqrt(g * h)
            smx = np.max(np.abs(u) + c)
            smy = np.max(np.abs(v) + c)
            if wave_boundary is not None:
                left_speed = np.abs(uP[0, 1:-1]) + np.sqrt(g * hP[0, 1:-1])
                smx = max(float(smx), float(np.max(left_speed)))
        else:
            c = np.sqrt(g * hP)
            smx = np.max(np.abs(uP) + c)
            smy = np.max(np.abs(vP) + c)
        dt = cfg.CFL / (smx / dx + smy / dy + 1e-12)
        dt = min(dt, cfg.dt_max_hydro, dt_limit)

        etaP = zP + hP
        if cfg.spatial_order == 2:
            sx_eta, sx_z = _limited_slope(etaP, 0), _limited_slope(zP, 0)
            sx_u, sx_v = _limited_slope(uP, 0), _limited_slope(vP, 0)
            etaL = etaP[:-1, 1:-1] + 0.5 * sx_eta[:-1, 1:-1]
            etaR = etaP[1:, 1:-1] - 0.5 * sx_eta[1:, 1:-1]
            zLx = zP[:-1, 1:-1] + 0.5 * sx_z[:-1, 1:-1]
            zRx = zP[1:, 1:-1] - 0.5 * sx_z[1:, 1:-1]
            hLx, hRx = np.maximum(etaL - zLx, 0.0), np.maximum(etaR - zRx, 0.0)
            uLx = uP[:-1, 1:-1] + 0.5 * sx_u[:-1, 1:-1]
            uRx = uP[1:, 1:-1] - 0.5 * sx_u[1:, 1:-1]
            vLx = vP[:-1, 1:-1] + 0.5 * sx_v[:-1, 1:-1]
            vRx = vP[1:, 1:-1] - 0.5 * sx_v[1:, 1:-1]
        elif cfg.spatial_order == 1:
            hLx, hRx = hP[:-1, 1:-1], hP[1:, 1:-1]
            zLx, zRx = zP[:-1, 1:-1], zP[1:, 1:-1]
            uLx, uRx = uP[:-1, 1:-1], uP[1:, 1:-1]
            vLx, vRx = vP[:-1, 1:-1], vP[1:, 1:-1]
        else:
            raise ValueError("spatial_order must be 1 or 2")

        # x faces: (nx+1, ny); reconstructed states preserve eta and bed slopes.
        Fh_x, FnL_x, FnR_x, Ft_x = self._face_flux(
            hLx, uLx, vLx, zLx, hRx, uRx, vRx, zRx,
            hP[:-1, 1:-1], hP[1:, 1:-1])

        if cfg.spatial_order == 2:
            sy_eta, sy_z = _limited_slope(etaP, 1), _limited_slope(zP, 1)
            sy_u, sy_v = _limited_slope(uP, 1), _limited_slope(vP, 1)
            etaLy = etaP[1:-1, :-1] + 0.5 * sy_eta[1:-1, :-1]
            etaRy = etaP[1:-1, 1:] - 0.5 * sy_eta[1:-1, 1:]
            zLy = zP[1:-1, :-1] + 0.5 * sy_z[1:-1, :-1]
            zRy = zP[1:-1, 1:] - 0.5 * sy_z[1:-1, 1:]
            hLy, hRy = np.maximum(etaLy - zLy, 0.0), np.maximum(etaRy - zRy, 0.0)
            vLy = vP[1:-1, :-1] + 0.5 * sy_v[1:-1, :-1]
            vRy = vP[1:-1, 1:] - 0.5 * sy_v[1:-1, 1:]
            uLy = uP[1:-1, :-1] + 0.5 * sy_u[1:-1, :-1]
            uRy = uP[1:-1, 1:] - 0.5 * sy_u[1:-1, 1:]
        else:
            hLy, hRy = hP[1:-1, :-1], hP[1:-1, 1:]
            zLy, zRy = zP[1:-1, :-1], zP[1:-1, 1:]
            vLy, vRy = vP[1:-1, :-1], vP[1:-1, 1:]
            uLy, uRy = uP[1:-1, :-1], uP[1:-1, 1:]
        # y faces: (nx, ny+1), normal=v and tangential=u.
        Gh_y, GnL_y, GnR_y, Gt_y = self._face_flux(
            hLy, vLy, uLy, zLy, hRy, vRy, uRy, zRy,
            hP[1:-1, :-1], hP[1:-1, 1:])

        if inflow_available is not None:
            # Positivity limit on the reservoir face: inflow over this step may not exceed
            # storage plus external inflow. Blocked fraction acts as a wall (pressure only).
            V_avail = max(inflow_available[0] + inflow_available[1] * dt, 0.0)
            into = np.maximum(Fh_x[0, :], 0.0)
            demand = float(np.sum(into) * dy * dt)
            if demand > V_avail:
                f = V_avail / demand
                pos = Fh_x[0, :] > 0.0
                wall_p = 0.5 * g * hP[1, 1:-1] ** 2
                Fh_x[0, :] = np.where(pos, f * Fh_x[0, :], Fh_x[0, :])
                FnR_x[0, :] = np.where(pos, f * FnR_x[0, :] + (1.0 - f) * wall_p, FnR_x[0, :])
                Ft_x[0, :] = np.where(pos, f * Ft_x[0, :], Ft_x[0, :])
                self.inflow_limit_events += 1
        Q_left = float(np.sum(Fh_x[0, :]) * dy)
        Q_right = float(np.sum(Fh_x[-1, :]) * dy)

        hu, hv = h * u, h * v
        h_new = h - dt / dx * (Fh_x[1:] - Fh_x[:-1]) - dt / dy * (Gh_y[:, 1:] - Gh_y[:, :-1])
        hu_new = hu - dt / dx * (FnL_x[1:] - FnR_x[:-1]) - dt / dy * (Gt_y[:, 1:] - Gt_y[:, :-1])
        hv_new = hv - dt / dx * (Ft_x[1:] - Ft_x[:-1]) - dt / dy * (GnL_y[:, 1:] - GnR_y[:, :-1])
        h_new = np.maximum(h_new, 0.0)

        wet = h_new > cfg.h_dry
        hs = np.maximum(h_new, cfg.h_dry)
        un = np.where(wet, hu_new / hs, 0.0)
        vn = np.where(wet, hv_new / hs, 0.0)
        sp = np.sqrt(un**2 + vn**2)
        if cfg.friction_model == "chezy":
            Cf = g / max(cfg.chezy_C, 1e-6)**2
            fac = 1.0 / (1.0 + dt * Cf * sp / hs)
        elif cfg.friction_model == "manning":
            n = max(cfg.manning_n, 0.0)
            # Manning friction slope Sf = n² U² / h^(4/3), represented
            # semi-implicitly as a drag acceleration opposite to velocity.
            coeff = g * n * n / np.maximum(hs, cfg.h_dry) ** (4.0 / 3.0)
            fac = 1.0 / (1.0 + dt * coeff * sp)
        else:
            raise ValueError("friction_model must be 'chezy' or 'manning'")
        un, vn = un * fac, vn * fac
        # safety clip
        sp = np.sqrt(un**2 + vn**2)
        clip = (sp > cfg.max_speed) & wet
        if np.any(clip):
            self.speed_clip_events += 1
            self.speed_clip_cells += int(np.count_nonzero(clip))
            self.speed_clip_max_uncapped = max(self.speed_clip_max_uncapped, float(np.max(sp[clip])))
            for i, j in np.argwhere(clip):
                key = (int(i), int(j))
                self.speed_clip_locations[key] = self.speed_clip_locations.get(key, 0) + 1
        sc = np.where(clip, cfg.max_speed / (sp + 1e-12), 1.0)
        un, vn = un * sc, vn * sc

        mesh.h, mesh.u, mesh.v = h_new, un, vn
        self.bed_shear(mesh)
        return dt, Q_left, Q_right


# =============================================================================
# 5. SEDIMENT TRANSPORT CAPACITY / DETACHMENT LAWS
# =============================================================================

class SedimentTransport:
    """
    Capacity laws return q* [m2/s of solids] (magnitude).
    Detachment laws (Partheniades, Hanson) return an entrainment rate E [m/s].
    """

    def __init__(self, cfg: EngineConfig, mat: MaterialProps):
        self.cfg, self.mat = cfg, mat
        self.s = mat.rho_s / mat.rho_w

    @property
    def is_capacity_law(self) -> bool:
        return self.cfg.transport in (TransportFormula.WU,
                                      TransportFormula.VAN_RIJN,
                                      TransportFormula.MPM)

    def shields(self, tau: np.ndarray) -> np.ndarray:
        return tau / ((self.s - 1.0) * self.mat.rho_w * self.cfg.g * self.mat.D50 + 1e-12)

    def capacity(self, tau: np.ndarray) -> np.ndarray:
        g, D, s = self.cfg.g, self.mat.D50, self.s
        scale = np.sqrt((s - 1.0) * g * D**3)
        th = self.shields(tau)
        thc = self.critical_shields_field()
        f = self.cfg.transport
        k = max(float(self.cfg.transport_capacity_factor), 0.0)
        if f == TransportFormula.MPM:
            return k * 8.0 * np.maximum(th - thc, 0.0) ** 1.5 * scale
        if f == TransportFormula.WU:
            # Wu, Wang & Jia (2000) bed load, single fraction, n'/n = 1
            return k * 0.0053 * np.maximum(th / thc - 1.0, 0.0) ** 2.2 * scale
        if f == TransportFormula.VAN_RIJN:
            # van Rijn (1984) bed load
            Dstar = D * ((s - 1.0) * g / 1.0e-6**2) ** (1.0 / 3.0)
            T = np.maximum(th / thc - 1.0, 0.0)
            return k * 0.053 * np.sqrt((s - 1.0) * g) * D**1.5 * T**2.1 / Dstar**0.3
        raise ValueError("capacity() called for a detachment-type formula")

    def detachment_rate(self, tau: np.ndarray) -> np.ndarray:
        rate = self.detachment_rate_uncapped(tau)
        if self.cfg.detachment_rate_cap is not None:
            rate = np.minimum(rate, max(self.cfg.detachment_rate_cap, 0.0))
        return rate

    def detachment_rate_uncapped(self, tau: np.ndarray) -> np.ndarray:
        m = self.mat
        if self.cfg.transport == TransportFormula.PARTHENIADES:
            rate = m.kd * np.maximum(tau / m.tau_c - 1.0, 0.0)
        elif self.cfg.transport == TransportFormula.HANSON:
            rate = m.kd * np.maximum(tau - m.tau_c, 0.0) ** m.n_exp
        else:
            raise ValueError("detachment_rate() called for a capacity formula")
        return rate

    def critical_shields_field(self) -> np.ndarray:
        """Optional D50–D90 threshold spread, normalized to preserve the D50 center."""
        mode = self.cfg.threshold_D.lower()
        if mode not in ("d50", "geometric", "d90"):
            raise ValueError("threshold_D must be 'D50', 'geometric' or 'D90'")
        if self.cfg.gradation_enabled and mode == "d50":
            mode = "geometric"            # legacy switch
        ratio = 1.0
        if mode != "d50" and self.mat.D90 > self.mat.D50:
            # Broad but bounded grain-size threshold spread for screening. A full
            # hiding/exposure closure requires a transported active-layer mixture.
            raw = self.mat.D90 / max(self.mat.D50, 1e-12)
            ratio = float(np.clip(np.sqrt(raw), 1.0, 3.0) if mode == "geometric"
                          else np.clip(raw, 1.0, 6.0))
        return np.asarray(self.mat.theta_c * ratio * max(self.cfg.threshold_factor, 0.0))


# =============================================================================
# 6. VERTICAL DETACHMENT LIMIT -- CHEN HYPERBOLIC
# =============================================================================

class ChenVertical:
    def __init__(self, mat: MaterialProps):
        self.mat = mat

    def rate(self, tau: np.ndarray) -> np.ndarray:
        """Maximum vertical detachment rate [m/s] (saturating hyperbola)."""
        m = self.mat
        ex = np.maximum(tau - m.tau_c, 0.0)
        return m.chen_scale * m.chen_k * ex / (m.chen_a + m.chen_b * ex + 1e-12)


# =============================================================================
# 7. LATERAL EROSION -- critical-shear reduction (Lane/Julien) or Ikeda-type force balance
# =============================================================================

def ikeda_side_slope_factor(alpha, phi, lift_drag: float = 0.85):
    """Threshold-shear ratio tau_cs/tau_c0 for a grain on a side slope (Ikeda 1982 type).

    Grain balance: tangential force sqrt(D^2 + (W sin a)^2) = mu (W cos a - L),
    with L = lift_drag * D, mu = tan(phi). Solves for the drag D at threshold
    and divides by the flat-bed value. Returns 1 at a = 0 and 0 at a >= phi.
    """
    alpha = np.asarray(alpha, dtype=float)
    mu = float(np.tan(phi))
    l = float(lift_drag)
    a = max(1.0 - (mu * l) ** 2, 1e-6)
    sa, ca = np.sin(alpha), np.cos(alpha)
    b = 2.0 * mu * mu * l * ca
    cc = sa ** 2 - (mu * ca) ** 2
    disc = np.maximum(b * b - 4.0 * a * cc, 0.0)
    D = np.where(cc < 0.0, (-b + np.sqrt(disc)) / (2.0 * a), 0.0)
    b0 = 2.0 * mu * mu * l
    D0 = (-b0 + np.sqrt(b0 * b0 + 4.0 * a * mu * mu)) / (2.0 * a)
    return np.clip(D / max(D0, 1e-12), 0.0, 1.0)


class LateralErosion:
    """
    Bank-cell retreat next to wet cells (lateral_model selects the slope factor:
    'critical_shear' = Lane/Julien, 'force_balance' = Ikeda-type grain balance).  A bank cell B (higher than wet
    neighbour A) loses volume at the rate the wetted wall retreats:
        R  = kd * max(tau_A - tau_cb, 0)^n         [m/s]
        tau_cb = tau_c * cos(a) * sqrt(1 - tan^2 a / tan^2 phi)   (Lane/Julien)
        dz_B = R * h_wet * dt / dy
    The solids go into the sediment field of A (mass conserved).
    """

    def __init__(self, mat: MaterialProps, cfg: EngineConfig):
        self.mat, self.cfg = mat, cfg

    def apply(self, mesh: MeshState, tau: np.ndarray, dt: float) -> float:
        m, cfg = self.mat, self.cfg
        p, phi = m.porosity, np.deg2rad(m.phi)
        z, S, h, zf = mesh.z_b, mesh.S, mesh.h, mesh.z_floor
        total = 0.0
        for ia, ib in ((slice(0, -1), slice(1, None)), (slice(1, None), slice(0, -1))):
            zA, zB = z[:, ia], z[:, ib]
            SA, hA, tA = S[:, ia], h[:, ia], tau[:, ia]
            drop = zB - zA
            mask = (hA > cfg.h_dry) & (drop > 1e-6)
            tan_a = np.where(mask, drop / mesh.dy, 0.0)
            if cfg.lateral_model == "force_balance":
                K = ikeda_side_slope_factor(np.arctan(tan_a), phi, cfg.lateral_lift_drag)
            else:
                K = np.cos(np.arctan(tan_a)) * np.sqrt(np.maximum(1.0 - (tan_a / np.tan(phi))**2, 0.0))
            tau_c_bank = (m.tau_c if cfg.bank_tau_c is None else cfg.bank_tau_c) * max(cfg.bank_threshold_factor, 0.0)
            n_bank = m.n_exp if cfg.bank_n_exp is None else cfg.bank_n_exp
            kd_bank = m.kd if cfg.bank_kd is None else cfg.bank_kd
            tau_bank = tA * max(cfg.near_bank_shear_factor, 0.0)
            tau_cb = tau_c_bank * K
            R = kd_bank * np.maximum(tau_bank - tau_cb, 0.0) ** n_bank
            hw = np.minimum(drop, hA)
            dzB = np.where(mask, R * hw * dt / mesh.dy, 0.0)
            dzB = np.minimum(dzB, np.maximum(drop, 0.0))
            dzB = np.minimum(dzB, np.maximum(zB - zf[:, ib], 0.0))
            zB -= dzB
            SA += (1.0 - p) * dzB
            total += float(np.sum(dzB)) * mesh.dx * mesh.dy
        return total


LateralForceBalance = LateralErosion   # backwards-compatible name


# =============================================================================
# 8. BANK STABILITY (Culmann planar wedge on every neighbouring pair)
# =============================================================================

class BankStability:
    def __init__(self, mat: MaterialProps, cfg: EngineConfig):
        self.mat, self.cfg = mat, cfg
        self.last_min_fs = float("inf")
        if cfg.bank_stability != BankStabilityMethod.CRITICAL_DEPTH:
            # Do not silently substitute a different stability method. A run
            # labelled Bishop or Spencer would otherwise produce Culmann
            # results while appearing to honour the requested configuration.
            raise NotImplementedError(
                f"bank_stability='{cfg.bank_stability.value}' is not implemented; "
                "only the Culmann critical-depth screening method is available."
            )

    @property
    def gamma(self) -> float:
        m = self.mat
        return (m.rho_s * (1.0 - m.porosity) + m.rho_w * m.porosity) * self.cfg.g

    def critical_height(self, beta: np.ndarray) -> np.ndarray:
        """Culmann critical height; infinite for beta <= phi (stable at any height)."""
        c, phi = self.mat.cohesion, np.deg2rad(self.mat.phi)
        beta = np.asarray(beta, dtype=float)
        num = 4.0 * c * np.sin(beta) * np.cos(phi)
        den = self.gamma * (1.0 - np.cos(beta - phi)) + 1e-12
        return np.where(beta > phi, num / den, np.inf)

    def _collapse_pairs(self, zA, zB, SA, SB, hA, hB, ds) -> float:
        p, phi = self.mat.porosity, np.deg2rad(self.mat.phi)
        dz = zA - zB
        ad = np.abs(dz)
        beta = np.arctan(ad / ds)
        Zc = self.critical_height(beta)
        fs_trigger = max(self.cfg.bank_fs_trigger, 1e-6)
        fs_target = max(self.cfg.bank_fs_target, 1e-6)
        FS = Zc / np.maximum(ad, 1e-12)            # Culmann height-based factor of safety
        if np.any(ad > 1e-9):
            self.last_min_fs = min(self.last_min_fs, float(np.min(FS[ad > 1e-9])))
        target = np.minimum(np.maximum(Zc / fs_target, ds * np.tan(phi)), ad)
        d = np.where(FS < fs_trigger, ad - target, 0.0)
        # Culmann is used only for a dry, unsupported high bank adjoining a
        # wet toe. Submerged or fully dry terrain pairs remain supported in
        # this screening closure; the model does not simulate full pore pressure.
        wetA, wetB = hA > self.cfg.h_dry, hB > self.cfg.h_dry
        unsupported = ((dz > 0.0) & (~wetA) & wetB) | ((dz < 0.0) & wetA & (~wetB))
        d = np.where((d > 1e-6) & unsupported, d, 0.0)
        fromA, fromB = np.where(dz > 0, d, 0.0), np.where(dz < 0, d, 0.0)
        zA -= fromA
        zB -= fromB
        toA, toB = fromB, fromA            # material lands in the lower cell
        wA, wB = wetA, wetB
        SA += np.where(wA, (1.0 - p) * toA, 0.0)
        zA += np.where(wA, 0.0, toA)
        SB += np.where(wB, (1.0 - p) * toB, 0.0)
        zB += np.where(wB, 0.0, toB)
        return float(np.sum(d))

    def check_and_collapse(self, mesh: MeshState) -> float:
        """Returns collapsed bulk volume [m3]. Mass is conserved."""
        total = 0.0
        self.last_min_fs = float("inf")
        for _ in range(max(self.cfg.collapse_iterations, 1)):
            moved = 0.0
            for axis, ds in ((1, mesh.dy), (0, mesh.dx)):
                n = mesh.z_b.shape[axis]
                for start in (0, 1):
                    a = slice(start, n - 1, 2)
                    b = slice(start + 1, n, 2)
                    ia = (slice(None), a) if axis == 1 else (a, slice(None))
                    ib = (slice(None), b) if axis == 1 else (b, slice(None))
                    moved += self._collapse_pairs(
                        mesh.z_b[ia], mesh.z_b[ib], mesh.S[ia], mesh.S[ib],
                        mesh.h[ia], mesh.h[ib], ds)
            total += moved
            if moved < 1e-9:
                break
        return total * mesh.dx * mesh.dy


# =============================================================================
# 9. HEADCUT (energy law at real scarps)
# =============================================================================

class Headcut:
    """
    Implements Temple/Hanson energy, Temple (1992), or thresholded SITES
    advance at every wet scarp. The upstream cell is lowered
    toward the downstream bed by dX/dx of the drop; the solids move into the
    sediment field of the downstream cell.
    """

    def __init__(self, cfg: EngineConfig, mat: MaterialProps):
        self.cfg, self.mat = cfg, mat

    @staticmethod
    def sites_rate_from_Kh(q_m2s: np.ndarray, H_m: np.ndarray, Kh: float) -> np.ndarray:
        """NRCS NEH 628 Ch. 51 SITES headcut rate using documented Kh relations.

        The source equations are in US customary units, so q and H are converted
        to ft²/s and ft; the result is converted back from ft/h to m/s.
        """
        kh = max(float(Kh), 1e-9)
        attack = np.cbrt(np.maximum(q_m2s, 0.0) * 10.7639104167 *
                         np.maximum(H_m, 0.0) * 3.280839895)
        if kh < 0.01:
            threshold = 0.0
        else:
            threshold = (1.0 / 3.0) * np.exp(-((np.log(kh) - 3.23) ** 2) / 189.0)
        coefficient = -0.79 * np.log(kh) + 3.04 if kh < 18.2 else 0.75
        ft_per_hour = coefficient * np.maximum(attack - threshold, 0.0)
        return ft_per_hour * 0.3048 / 3600.0

    def migrate(self, mesh: MeshState, qx: np.ndarray, dt: float) -> float:
        cfg, p = self.cfg, self.mat.porosity
        z = mesh.z_b
        drops = z[:-1, :] - z[1:, :]                     # (nx-1, ny), face i|i+1
        ok = (drops / max(mesh.dx, 1e-12) >= cfg.headcut_min_slope) & (mesh.h[1:, :] > cfg.h_dry) \
             & (np.abs(qx[:-1, :]) > 1e-6)
        if not np.any(ok):
            return 0.0
        istar, js = np.where(ok)
        H = drops[istar, js]
        q = np.abs(qx[istar, js])
        method = cfg.headcut_method.lower()
        if method == "energy":
            rate = cfg.headcut_C * np.cbrt(q * H)
        elif method == "temple":
            rate = cfg.headcut_C * np.cbrt(q) * np.sqrt(H)
        elif method == "sites":
            if self.mat.headcut_Kh is not None:
                rate = self.sites_rate_from_Kh(q, H, self.mat.headcut_Kh)
            else:
                rate = cfg.headcut_C * np.maximum(np.cbrt(q * H) - cfg.headcut_threshold_A0, 0.0)
        else:
            raise ValueError("headcut_method must be 'energy', 'temple', or 'sites'")
        if cfg.headcut_max_rate is not None:
            rate = np.minimum(rate, max(cfg.headcut_max_rate, 0.0))
        rate = rate * max(cfg.headcut_retardation, 0.0)
        requested = np.minimum(rate * dt, H)  # fractional-cell retreat; no whole-cell jump
        requested_by_cell = np.zeros_like(z)
        np.add.at(requested_by_cell, (istar, js), requested)
        if cfg.z_floor_enabled:
            available = np.maximum(z - mesh.z_floor, 0.0)
            scale = np.minimum(1.0, available / np.maximum(requested_by_cell, 1e-12))
        else:
            scale = np.ones_like(z)
        applied = requested * scale[istar, js]
        np.add.at(z, (istar, js), -applied)
        np.add.at(mesh.S, (istar + 1, js), (1.0 - p) * applied)
        mesh.headcut_i = int(np.min(istar))
        return float(np.sum(applied)) * mesh.dx * mesh.dy


# =============================================================================
# 10. MORPHOLOGY -- non-equilibrium transport + Exner (single bed equation)
# =============================================================================

class Morphology:
    def __init__(self, cfg: EngineConfig, mat: MaterialProps):
        self.cfg, self.mat = cfg, mat
        self.chen = ChenVertical(mat)
        self.lateral = LateralForceBalance(mat, cfg)
        self.bank = BankStability(mat, cfg)
        self.headcut = Headcut(cfg, mat)
        self.transport = SedimentTransport(cfg, mat)
        self.sed_out_total = 0.0      # solids leaving through boundaries [m3]
        self._transport_bed_change = 0.0   # net bulk bed lowering from transport/Exner [m3]
        self.chen_cap_applications = 0
        self.chen_cap_limited_cells = 0
        self.detachment_cap_limited_cells = 0
        self.last_diag: Dict[str, float] = {}

    # ---- sediment advection (conservative upwind) --------------------------
    def _advect(self, mesh, h, qx, qy, dt) -> float:
        cfg = self.cfg
        nx, ny = mesh.nx, mesh.ny
        c = np.where(h > cfg.h_dry, mesh.S / np.maximum(h, cfg.h_dry), 0.0)
        qf = np.zeros((nx + 1, ny))
        qf[1:-1] = 0.5 * (qx[:-1] + qx[1:])
        qf[0], qf[-1] = qx[0], qx[-1]
        cf = np.zeros((nx + 1, ny))
        cf[1:-1] = np.where(qf[1:-1] > 0, c[:-1], c[1:])
        cf[0] = np.where(qf[0] < 0, c[0], 0.0)      # clear-water inflow
        cf[-1] = np.where(qf[-1] > 0, c[-1], 0.0)
        Fx = qf * cf
        rf = np.zeros((nx, ny + 1))                  # walls: zero flux
        rf[:, 1:-1] = 0.5 * (qy[:, :-1] + qy[:, 1:])
        cg = np.zeros((nx, ny + 1))
        cg[:, 1:-1] = np.where(rf[:, 1:-1] > 0, c[:, :-1], c[:, 1:])
        Fy = rf * cg
        if cfg.positivity_fix and not cfg.legacy_negative_S:
            Fx, Fy = self._limit_outflow(mesh, Fx, Fy, dt)
        mesh.S = mesh.S - dt / mesh.dx * (Fx[1:] - Fx[:-1]) - dt / mesh.dy * (Fy[:, 1:] - Fy[:, :-1])
        return float((Fx[-1].sum() - Fx[0].sum()) * mesh.dy * dt)   # solids out

    @staticmethod
    def _limit_outflow(mesh, Fx, Fy, dt):
        """Scale donor-cell fluxes so no cell sends out more solids than it holds (conservative)."""
        S = np.maximum(mesh.S, 0.0)
        out = (dt / mesh.dx * (np.maximum(Fx[1:], 0.0) + np.maximum(-Fx[:-1], 0.0))
               + dt / mesh.dy * (np.maximum(Fy[:, 1:], 0.0) + np.maximum(-Fy[:, :-1], 0.0)))
        f = np.where(out > S, S / np.maximum(out, 1e-300), 1.0)
        fx = np.ones_like(Fx)
        fx[1:-1] = np.where(Fx[1:-1] > 0, f[:-1], f[1:])
        fx[0], fx[-1] = f[0], f[-1]
        fy = np.ones_like(Fy)
        fy[:, 1:-1] = np.where(Fy[:, 1:-1] > 0, f[:, :-1], f[:, 1:])
        return Fx * fx, Fy * fy

    def _slope_factor(self, mesh, ux, uy, speed) -> np.ndarray:
        if not self.cfg.use_slope_effect:
            return 1.0
        dzdx = np.gradient(mesh.z_b, mesh.dx, axis=0)
        dzdy = np.gradient(mesh.z_b, mesh.dy, axis=1)
        dzds = (dzdx * ux + dzdy * uy) / (speed + 1e-9)
        return np.clip(1.0 - self.cfg.slope_beta * dzds, 0.3, 3.0)

    # ---- transport + Exner over the accumulated interval --------------------
    def _transport_exner(self, mesh, h, qx, qy, tau, dt_total) -> None:
        cfg, p = self.cfg, self.mat.porosity
        if cfg.adaptation_length_mode == "depth_scaled":
            Ls = np.maximum(cfg.adaptation_depth_factor * np.maximum(h, cfg.h_dry), mesh.dx)
        else:
            Ls = max(cfg.adaptation_length, mesh.dx)
        wet = h > cfg.h_dry
        hs = np.maximum(h, cfg.h_dry)
        ux, uy = np.where(wet, qx / hs, 0.0), np.where(wet, qy / hs, 0.0)
        speed = np.sqrt(ux**2 + uy**2)
        capacity_mode = self.transport.is_capacity_law
        chen_active = (cfg.use_chen_detachment_cap and
                       self.mat.material_class in cfg.chen_cap_materials)
        chen_cap = self.chen.rate(tau) if chen_active else None
        E_det = None if capacity_mode else self.transport.detachment_rate(tau)
        q_star0 = self.transport.capacity(tau) if capacity_mode else None

        remaining, nsub = dt_total, 0
        while remaining > 1e-12 and nsub < 5000:
            nsub += 1
            umax = max(float(np.max(speed)), 1e-6)
            dt_s = min(remaining, cfg.sed_CFL * min(mesh.dx, mesh.dy) / umax)
            if capacity_mode:
                q_star = q_star0 * self._slope_factor(mesh, ux, uy, speed)
                S_eq = np.where(speed > 1e-4, q_star / np.maximum(speed, 1e-4), 0.0)
                rate = np.max(np.abs(S_eq - mesh.S) * speed / Ls) / (1.0 - p)
                if rate > 1e-12:
                    dt_s = min(dt_s, max(cfg.max_dz_per_substep / rate, 1e-3))
            dt_s = min(dt_s, remaining)

            self.sed_out_total += self._advect(mesh, h, qx, qy, dt_s)

            relax = 1.0 - np.exp(-dt_s * speed / Ls)
            if capacity_mode:
                dS = (S_eq - mesh.S) * relax
                if chen_cap is not None:
                    cap = (1.0 - p) * chen_cap * dt_s
                    limited = dS > cap
                    self.chen_cap_applications += 1
                    self.chen_cap_limited_cells += int(np.count_nonzero(limited))
                    dS = np.minimum(dS, cap)
            else:
                ent = (1.0 - p) * E_det * dt_s
                if cfg.detachment_rate_cap is not None:
                    unbounded = (1.0 - p) * self.transport.detachment_rate_uncapped(tau) * dt_s
                    self.detachment_cap_limited_cells += int(np.count_nonzero(unbounded > ent + 1e-15))
                if cfg.detachment_load_saturation:
                    sat = np.clip(1.0 - mesh.S / np.maximum(cfg.detachment_max_concentration * hs, 1e-12), 0.0, 1.0)
                    ent = ent * sat
                if chen_cap is not None and cfg.chen_apply_to_detachment:
                    cap = (1.0 - p) * chen_cap * dt_s
                    self.chen_cap_applications += 1
                    self.chen_cap_limited_cells += int(np.count_nonzero(ent > cap))
                    ent = np.minimum(ent, cap)
                dep = np.where(tau < self.mat.tau_c, mesh.S * relax, 0.0)
                dS = ent - dep
            avail = ((1.0 - p) * np.maximum(mesh.z_b - mesh.z_floor, 0.0)
                     if cfg.z_floor_enabled else np.full_like(mesh.z_b, np.inf))
            dS = np.where(wet, np.minimum(dS, avail), 0.0)
            if cfg.active_layer_cap_m is not None:
                dS = np.minimum(dS, np.maximum((1.0 - p) * cfg.active_layer_cap_m - mesh.S, 0.0))
            dS = np.maximum(dS, -mesh.S)
            mesh.S = mesh.S + dS
            mesh.z_b = mesh.z_b - dS / (1.0 - p)          # Exner
            self._transport_bed_change += float(np.sum(dS)) / (1.0 - p) * mesh.dx * mesh.dy
            remaining -= dt_s

    def step(self, mesh: MeshState, h: np.ndarray, qx: np.ndarray, qy: np.ndarray,
             tau: np.ndarray, dt: float) -> Dict[str, float]:
        """One morphological update from time-averaged hydraulics (h, qx, qy, tau)."""
        cfg, p = self.cfg, self.mat.porosity
        _tb0 = self._transport_bed_change
        self._transport_exner(mesh, h, qx, qy, tau, dt)
        trans = self._transport_bed_change - _tb0
        lat = self.lateral.apply(mesh, tau, dt) if cfg.lateral_erosion_enabled else 0.0
        hc = self.headcut.migrate(mesh, qx, dt) if cfg.headcut_enabled else 0.0
        col = self.bank.check_and_collapse(mesh) if cfg.bank_collapse_enabled else 0.0
        toe = 0.0
        if col > 0.0 and cfg.toe_scour_factor > 0.0:
            wet = mesh.h > cfg.h_dry
            bank_adjacent = np.zeros_like(wet)
            for a, b in ((slice(0, -1), slice(1, None)), (slice(1, None), slice(0, -1))):
                bank_adjacent[:, a] |= wet[:, a] & (~wet[:, b]) & (mesh.z_b[:, b] > mesh.z_b[:, a])
                bank_adjacent[:, b] |= wet[:, b] & (~wet[:, a]) & (mesh.z_b[:, a] > mesh.z_b[:, b])
            for a, b in ((slice(0, -1), slice(1, None)), (slice(1, None), slice(0, -1))):
                bank_adjacent[a, :] |= wet[a, :] & (~wet[b, :]) & (mesh.z_b[b, :] > mesh.z_b[a, :])
                bank_adjacent[b, :] |= wet[b, :] & (~wet[a, :]) & (mesh.z_b[a, :] > mesh.z_b[b, :])
            n_toe = int(np.count_nonzero(bank_adjacent))
            if n_toe:
                area = mesh.dx * mesh.dy
                dz_target = cfg.toe_scour_factor * col / (n_toe * area)
                dz_toe = np.full_like(mesh.z_b, dz_target) * bank_adjacent
                if cfg.z_floor_enabled:
                    dz_toe = np.minimum(dz_toe, np.maximum(mesh.z_b - mesh.z_floor, 0.0))
                mesh.z_b -= dz_toe
                mesh.S += (1.0 - p) * dz_toe
                toe = float(np.sum(dz_toe)) * area

        # sediment sitting in dry cells settles onto the bed (mass conserved)
        dry = mesh.h <= cfg.h_dry
        mesh.z_b = mesh.z_b + np.where(dry, mesh.S / (1.0 - p), 0.0)
        mesh.S = np.where(dry, 0.0, mesh.S)

        self.last_diag = {"lateral_m3": lat, "headcut_m3": hc, "collapsed_m3": col,
                          "toe_scour_m3": toe, "transport_net_erosion_m3": trans,
                          "min_bank_FS": float(min(self.bank.last_min_fs, 1e6)),
                          "max_S": float(np.max(mesh.S))}
        return self.last_diag


# =============================================================================
# 11. MAIN ENGINE
# =============================================================================

class UltimateBreachEngine:
    def __init__(self, mesh: MeshState, reservoir: Reservoir,
                 mat: MaterialProps, cfg: EngineConfig):
        self.mesh, self.reservoir, self.mat, self.cfg = mesh, reservoir, mat, cfg
        if mat.material_class not in ("cohesive", "noncohesive", "mixed"):
            raise ValueError("material_class must be 'cohesive', 'noncohesive' or 'mixed' (reserved)")
        if mat.material_class == "mixed":
            warnings.warn("material_class='mixed' is reserved; it is treated as noncohesive in V3.2", stacklevel=2)
        if (mat.material_class == "cohesive" and
                cfg.transport in (TransportFormula.WU, TransportFormula.MPM, TransportFormula.VAN_RIJN)):
            warnings.warn("a bed-load capacity formula is being applied to material_class='cohesive'; treat as a screening comparison", stacklevel=2)
        if cfg.use_chen_detachment_cap and mat.material_class not in cfg.chen_cap_materials:
            warnings.warn("Chen cap requested but disabled by chen_cap_materials for this material class", stacklevel=2)
        if cfg.use_non_hydrostatic:
            warnings.warn("non-hydrostatic correction not implemented (SWE only).")
        if cfg.free_surface == FreeSurfaceMethod.LOCAL_VOF:
            warnings.warn("local VOF not implemented (height function only).")
        if cfg.erosion_shear not in ("total", "grain"):
            raise ValueError("erosion_shear must be 'total' or 'grain'")
        self.grain_n = (cfg.grain_manning_n if cfg.grain_manning_n is not None
                        else float(max(mat.D50, 1e-9) ** (1.0 / 6.0) / 21.1))
        self.hydro = Hydrodynamics(cfg, mat.rho_w, grain_n=self.grain_n)
        self.morpho = Morphology(cfg, mat)
        self._initial_bed = mesh.z_b.copy()
        self._initial_bed_hash = hashlib.sha256(self._initial_bed.tobytes()).hexdigest()
        row_mean = np.mean(self._initial_bed, axis=1)
        crest_floor = 0.85 * float(np.max(row_mean))
        self._crest_rows = row_mean >= crest_floor
        self._dam_height = max(float(np.max(self._initial_bed) - np.min(mesh.z_floor)), 1e-9)
        self.time = 0.0
        self.history = []
        # balance bookkeeping
        self._V0 = mesh.water_volume()
        self._reservoir_V0 = reservoir.volume
        self.cum_external_inflow = 0.0
        self._solids0 = mesh.solids_volume(mat.porosity)
        self.cum_Q_left = 0.0
        self.cum_Q_right = 0.0
        self.peak_Q_prism_outlet = 0.0
        self.peak_time = 0.0
        self.peak_decline_steps = 0
        self.last_morph_time = 0.0
        self.morph_updates = 0
        self.stop_reason: Optional[str] = None
        self.nsteps = 0
        self.next_print = 0.0
        self._acc_dt = 0.0
        self._acc = {k: np.zeros_like(mesh.h) for k in ("h", "qx", "qy", "tau")}
        self._next_snapshot: Optional[float] = None
        self._next_checkpoint: Optional[float] = None
        self.timing = {"hydro_s": 0.0, "morph_s": 0.0, "wall_s": 0.0}
        self.source_totals = {k: 0.0 for k in ("lateral", "headcut", "collapse", "toe_scour", "transport_net")}
        self.run_status = "not_started"
        self._validate_v32_options()

    def _validate_v32_options(self) -> None:
        cfg = self.cfg
        checks = (("downstream_boundary", cfg.downstream_boundary, ("transmissive", "wall", "outfall")),
                  ("lateral_model", cfg.lateral_model, ("critical_shear", "force_balance")),
                  ("threshold_D", cfg.threshold_D.lower(), ("d50", "geometric", "d90")),
                  ("adaptation_length_mode", cfg.adaptation_length_mode, ("fixed", "depth_scaled")))
        for name, value, allowed in checks:
            if value not in allowed:
                raise ValueError(f"{name} must be one of {allowed}, got {value!r}")

    # ---- diagnostics -------------------------------------------------------
    def water_balance_error(self) -> float:
        """Prism water storage change minus net boundary inflow [m3] (should be ~0)."""
        dV = self.mesh.water_volume() - self._V0
        return dV - (self.cum_Q_left - self.cum_Q_right)

    def reservoir_water_balance_error(self) -> float:
        """Actual reservoir water-storage change minus inflow and prism transfer."""
        return (self.reservoir.volume - self._reservoir_V0 - self.cum_external_inflow
                + self.cum_Q_left - self.reservoir.hold_added_m3)

    def sediment_balance_error(self) -> float:
        """Solids storage change plus solids exported [m3] (should be ~0)."""
        now = self.mesh.solids_volume(self.mat.porosity)
        return (now - self._solids0) + self.morpho.sed_out_total

    def breach_development(self) -> Dict[str, float]:
        """Consistent crest progression indices from bed depth, width and area.

        These are geometric diagnostics for this synthetic prism, not a
        calibrated breach maturity law. The three normalized measures enter
        equally through a geometric mean, so one cannot alone set the index.
        """
        lowering = np.maximum(self._initial_bed - self.mesh.z_b, 0.0)
        threshold = max(0.02, 0.01 * self._dam_height)
        rows = np.where(self._crest_rows)[0]
        if rows.size == 0:
            return {"depth_m": 0.0, "width_m": 0.0, "area_m2": 0.0, "BDI": 0.0}
        row_areas = np.sum(lowering[rows, :], axis=1) * self.mesh.dy
        row = rows[int(np.argmax(row_areas))]
        cross = lowering[row, :]
        frac = max(float(self.cfg.breach_width_fraction), 0.0)
        active = np.where(cross >= max(threshold, frac * float(np.max(cross))))[0]
        if active.size == 0:
            return {"depth_m": 0.0, "width_m": 0.0, "area_m2": 0.0, "BDI": 0.0}
        width = (int(active[-1]) - int(active[0]) + 1) * self.mesh.dy
        depth = float(np.mean(cross[active]))
        area = float(np.sum(cross[active]) * self.mesh.dy)
        r_depth = np.clip(depth / self._dam_height, 0.0, 1.0)
        r_width = np.clip(width / (self.mesh.ny * self.mesh.dy), 0.0, 1.0)
        r_area = np.clip(area / (self._dam_height * self.mesh.ny * self.mesh.dy), 0.0, 1.0)
        bdi = float((r_depth * r_width * r_area) ** (1.0 / 3.0))
        return {"depth_m": depth, "width_m": width, "area_m2": area, "BDI": bdi}

    def channelization_index(self) -> float:
        """Transverse scour-concentration proxy; 1 means uniform scour across y."""
        scour_by_y = np.sum(np.maximum(self._initial_bed - self.mesh.z_b, 0.0), axis=0)
        active = scour_by_y[scour_by_y > 1e-10]
        return float(np.max(active) / max(float(np.mean(active)), 1e-12)) if active.size else 0.0

    def diagnostics_summary(self) -> Dict[str, object]:
        """Cumulative sediment sources, limiter activity, clipping and balance errors."""
        m, hy = self.morpho, self.hydro
        return {
            "run_status": self.run_status, "stop_reason": self.stop_reason,
            "time_s": self.time, "steps": self.nsteps, "morph_updates": self.morph_updates,
            "sediment_sources_m3": dict(self.source_totals),
            "chen_cap_applications": m.chen_cap_applications,
            "chen_cap_limited_cells": m.chen_cap_limited_cells,
            "detachment_cap_limited_cells": m.detachment_cap_limited_cells,
            "speed_clip_events": hy.speed_clip_events, "speed_clip_cells": hy.speed_clip_cells,
            "speed_clip_max_uncapped_ms": hy.speed_clip_max_uncapped,
            "water_balance_err_m3": self.water_balance_error(),
            "reservoir_balance_err_m3": self.reservoir_water_balance_error(),
            "sediment_balance_err_m3": self.sediment_balance_error(),
            "reservoir_hold_added_m3": self.reservoir.hold_added_m3,
            "reservoir_curve_overflow_m3": self.reservoir.curve_overflow_m3,
            "reservoir_clipped_m3": self.reservoir.clipped_m3,
            "reservoir_empty": self.reservoir.empty,
            "inflow_limit_events": hy.inflow_limit_events,
            "timing_s": dict(self.timing),
        }

    def write_diagnostics_csv(self, path: str) -> str:
        """Write the per-step history (including per-morph source volumes) to CSV."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not self.history:
            raise ValueError("no history to write")
        with open(path, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.history[0].keys()))
            writer.writeheader()
            writer.writerows(self.history)
        return path

    def _configuration_hash(self) -> str:
        def serial(obj):
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(type(obj).__name__)
        payload = json.dumps({"config": asdict(self.cfg), "material": asdict(self.mat)},
                             sort_keys=True, default=serial)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save_checkpoint(self, path: str) -> None:
        """Atomically save a restart point; NumPy archives are closed before replace (Windows-safe)."""
        meta = {
            "version": 6, "config_hash": self._configuration_hash(),
            "time": self.time, "reservoir_level": self.reservoir.level,
            "reservoir_volume": self.reservoir.volume,
            "reservoir_displaced_volume": self.reservoir.displaced_volume,
            "cum_Q_left": self.cum_Q_left, "cum_Q_right": self.cum_Q_right,
            "sed_out_total": self.morpho.sed_out_total,
            "peak_Q_prism_outlet": self.peak_Q_prism_outlet,
            "peak_time": self.peak_time, "peak_decline_steps": self.peak_decline_steps,
            "stop_reason": self.stop_reason, "nsteps": self.nsteps,
            "next_print": self.next_print, "history": self.history,
            "V0": self._V0, "solids0": self._solids0,
            "reservoir_V0": self._reservoir_V0,
            "cum_external_inflow": self.cum_external_inflow,
            "acc_dt": self._acc_dt, "next_snapshot": self._next_snapshot,
            "next_checkpoint": self._next_checkpoint,
            "last_morph_time": self.last_morph_time, "morph_updates": self.morph_updates,
            "dx": self.mesh.dx, "dy": self.mesh.dy, "nx": self.mesh.nx, "ny": self.mesh.ny,
            "reservoir_curve_elevs": self.reservoir.elevs.tolist(),
            "reservoir_curve_vols": self.reservoir.vols.tolist(),
            "speed_clip_events": self.hydro.speed_clip_events,
            "speed_clip_cells": self.hydro.speed_clip_cells,
            "speed_clip_max_uncapped": self.hydro.speed_clip_max_uncapped,
            "speed_clip_locations": [[i, j, n] for (i, j), n in self.hydro.speed_clip_locations.items()],
            "initial_bed_hash": self._initial_bed_hash,
            "hold_added_m3": self.reservoir.hold_added_m3,
            "reservoir_clipped_m3": self.reservoir.clipped_m3,
            "inflow_limit_events": self.hydro.inflow_limit_events,
            "source_totals": self.source_totals,
        }
        target = os.path.abspath(path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        temp = target + ".tmp"
        try:
            with open(temp, "wb") as stream:
                np.savez_compressed(stream, meta=np.asarray(json.dumps(meta)),
                    z_b=self.mesh.z_b, h=self.mesh.h, u=self.mesh.u, v=self.mesh.v,
                    S=self.mesh.S, tau_b=self.mesh.tau_b,
                    z_floor=self.mesh.z_floor, headcut_i=np.asarray(self.mesh.headcut_i),
                    acc_h=self._acc["h"], acc_qx=self._acc["qx"],
                    acc_qy=self._acc["qy"], acc_tau=self._acc["tau"])
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.remove(temp)

    def load_checkpoint(self, path: str) -> None:
        """Restore a checkpoint into an engine built with matching mesh/config/material."""
        with np.load(path, allow_pickle=False) as archive:
            data = {name: archive[name].copy() for name in archive.files}
        meta = json.loads(str(data["meta"]))
        if meta.get("version") != 6 or meta.get("config_hash") != self._configuration_hash():
            raise ValueError("checkpoint version/config/material does not match this engine")
        if (meta.get("nx") != self.mesh.nx or meta.get("ny") != self.mesh.ny
                or not np.isclose(meta.get("dx"), self.mesh.dx)
                or not np.isclose(meta.get("dy"), self.mesh.dy)):
            raise ValueError("checkpoint mesh dimensions or spacing do not match this engine")
        if meta.get("initial_bed_hash") != self._initial_bed_hash:
            raise ValueError("checkpoint initial bed geometry does not match this engine")
        if not (np.array_equal(np.asarray(meta["reservoir_curve_elevs"]), self.reservoir.elevs)
                and np.array_equal(np.asarray(meta["reservoir_curve_vols"]), self.reservoir.vols)):
            raise ValueError("checkpoint reservoir stage-volume curve does not match this engine")
        for name in ("z_b", "h", "u", "v", "S", "tau_b", "z_floor"):
            target = getattr(self.mesh, name)
            if data[name].shape != target.shape:
                raise ValueError(f"checkpoint {name} shape does not match mesh")
            setattr(self.mesh, name, data[name])
        self.mesh.headcut_i = int(data["headcut_i"])
        self.time = float(meta["time"])
        self.reservoir.level = float(meta["reservoir_level"])
        self.reservoir.volume = float(meta["reservoir_volume"])
        self.reservoir.displaced_volume = float(meta["reservoir_displaced_volume"])
        self.cum_Q_left = float(meta["cum_Q_left"])
        self.cum_Q_right = float(meta["cum_Q_right"])
        self.morpho.sed_out_total = float(meta["sed_out_total"])
        self.peak_Q_prism_outlet = float(meta["peak_Q_prism_outlet"])
        self.peak_time = float(meta["peak_time"])
        self.peak_decline_steps = int(meta["peak_decline_steps"])
        self.stop_reason = meta.get("stop_reason")
        self.nsteps = int(meta["nsteps"])
        self.next_print = float(meta["next_print"])
        self.history = meta.get("history", [])
        self._V0, self._solids0 = float(meta["V0"]), float(meta["solids0"])
        self._reservoir_V0 = float(meta["reservoir_V0"])
        self.cum_external_inflow = float(meta["cum_external_inflow"])
        self._acc_dt = float(meta["acc_dt"])
        for key in self._acc:
            name = "acc_" + key
            if data[name].shape != self._acc[key].shape:
                raise ValueError(f"checkpoint {name} shape does not match mesh")
            self._acc[key] = data[name]
        self._next_snapshot = meta.get("next_snapshot")
        self._next_checkpoint = meta.get("next_checkpoint")
        self.last_morph_time = float(meta.get("last_morph_time", 0.0))
        self.morph_updates = int(meta.get("morph_updates", 0))
        self.reservoir.hold_added_m3 = float(meta.get("hold_added_m3", 0.0))
        self.reservoir.clipped_m3 = float(meta.get("reservoir_clipped_m3", 0.0))
        self.hydro.inflow_limit_events = int(meta.get("inflow_limit_events", 0))
        self.source_totals.update(meta.get("source_totals", {}))
        self.hydro.speed_clip_events = int(meta.get("speed_clip_events", 0))
        self.hydro.speed_clip_cells = int(meta.get("speed_clip_cells", 0))
        self.hydro.speed_clip_max_uncapped = float(meta.get("speed_clip_max_uncapped", 0.0))
        self.hydro.speed_clip_locations = {(int(i), int(j)): int(n)
                                           for i, j, n in meta.get("speed_clip_locations", [])}

    def save_snapshot(self, directory: str) -> str:
        """Write an instantaneous field snapshot for post-processing."""
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"field_{self.time:012.3f}s.npz")
        temp = path + ".tmp"
        with open(temp, "wb") as stream:
            np.savez_compressed(stream, time=self.time, x=self.mesh.x, y=self.mesh.y,
                z_b=self.mesh.z_b, eta=self.mesh.eta, h=self.mesh.h, u=self.mesh.u,
                v=self.mesh.v, tau_b=self.mesh.tau_b, sediment=self.mesh.S)
        os.replace(temp, path)
        return path

    # ---- main loop ----------------------------------------------------------
    def run(self, t_end: float, Qin: Union[float, Callable[[float], float]] = 0.0,
            verbose: bool = True, print_every: float = 5.0, *,
            stop_at_peak: bool = False, peak_confirm_steps: int = 50,
            peak_tolerance: float = 1e-3,
            snapshot_dir: Optional[str] = None, snapshot_interval_s: Optional[float] = None,
            checkpoint_path: Optional[str] = None, checkpoint_interval_s: Optional[float] = None,
            wave_boundary: Optional[LakeWaveBoundary] = None,
            hold_reservoir_level: Optional[float] = None,
            max_wall_seconds: Optional[float] = None,
            stop_on_balance_error_m3: Optional[float] = None,
            monitor: Optional["InitiationMonitor"] = None,
            stop_when_drained_s: Optional[float] = None, drained_volume_m3: float = 1000.0):
        """Run to absolute ``t_end``; optionally stop after a confirmed prism-outlet peak."""
        cfg, mesh = self.cfg, self.mesh
        if print_every <= 0:
            raise ValueError("print_every must be positive")
        if cfg.dt_morpho_factor < 1:
            raise ValueError("dt_morpho_factor must be >= 1")
        if cfg.morph_accel <= 0 or cfg.max_dz_per_substep <= 0 or cfg.adaptation_length <= 0:
            raise ValueError("morph_accel, max_dz_per_substep, and adaptation_length must be positive")
        if cfg.friction_model not in ("chezy", "manning"):
            raise ValueError("friction_model must be 'chezy' or 'manning'")
        if cfg.friction_model == "manning" and cfg.manning_n <= 0:
            raise ValueError("manning_n must be positive")
        if cfg.spatial_order not in (1, 2):
            raise ValueError("spatial_order must be 1 or 2")
        if snapshot_dir is not None and snapshot_interval_s is None:
            raise ValueError("snapshot_interval_s is required when snapshot_dir is set")
        if checkpoint_path is not None and checkpoint_interval_s is None:
            raise ValueError("checkpoint_interval_s is required when checkpoint_path is set")
        if cfg.dt_morpho_target is not None and cfg.dt_morpho_target <= 0:
            raise ValueError("dt_morpho_target must be positive when specified")
        if self._next_snapshot is None and snapshot_interval_s is not None:
            if snapshot_interval_s <= 0: raise ValueError("snapshot_interval_s must be positive")
            self._next_snapshot = self.time + snapshot_interval_s
        if self._next_checkpoint is None and checkpoint_interval_s is not None:
            if checkpoint_interval_s <= 0: raise ValueError("checkpoint_interval_s must be positive")
            self._next_checkpoint = self.time + checkpoint_interval_s
        self._validate_v32_options()
        self.stop_reason = None
        self.run_status = "running"
        self.reservoir.hold_level = hold_reservoir_level
        wall0 = time.perf_counter()
        drained_since: Optional[float] = None
        while self.time < t_end - 1e-12:
            q_in = Qin(self.time) if callable(Qin) else Qin
            _th = time.perf_counter()
            limit = (None if (self.reservoir.legacy_unlimited_draw or self.reservoir.hold_level is not None)
                     else (self.reservoir.volume, q_in))
            dt, QL, QR = self.hydro.step(mesh, self.reservoir.level, t_end - self.time,
                                         wave_boundary=wave_boundary, time_s=self.time,
                                         inflow_available=limit)
            self.timing["hydro_s"] += time.perf_counter() - _th
            if (not np.isfinite(dt)) or dt <= 0.0 or not np.isfinite(QL) or not np.isfinite(QR) \
                    or not np.all(np.isfinite(mesh.h)):
                self.stop_reason = "nan_state"
                break
            if not self.reservoir._dry_warning_emitted and self.reservoir.level <= float(np.max(mesh.z_b[0, :])):
                warnings.warn("upstream reservoir ghost state is dry; no reservoir-to-prism stage head is available", stacklevel=2)
                self.reservoir._dry_warning_emitted = True

            # reservoir loses exactly what enters the prism
            self.reservoir.update(q_in, QL, dt)
            self.cum_external_inflow += q_in * dt
            self.cum_Q_left += QL * dt
            self.cum_Q_right += QR * dt

            # accumulate time-averaged hydraulics for the quasi-steady morph step
            self._acc_dt += dt
            self._acc["h"] += mesh.h * dt
            self._acc["qx"] += mesh.h * mesh.u * dt
            self._acc["qy"] += mesh.h * mesh.v * dt
            self._acc["tau"] += mesh.tau_b * dt
            self.time += dt
            self.nsteps += 1

            diag = {}
            morph_due = (self._acc_dt >= cfg.dt_morpho_target) if cfg.dt_morpho_target is not None else (self.nsteps % cfg.dt_morpho_factor == 0)
            if morph_due and self._acc_dt > 0:
                physical_morph_interval = self._acc_dt
                tau_for_morph = (mesh.tau_b if cfg.bed_shear_average == "instantaneous"
                                 else self._acc["tau"] / self._acc_dt)
                if cfg.bed_shear_average not in ("time_average", "instantaneous"):
                    raise ValueError("bed_shear_average must be 'time_average' or 'instantaneous'")
                _tm = time.perf_counter()
                diag = self.morpho.step(
                    mesh, self._acc["h"] / self._acc_dt, self._acc["qx"] / self._acc_dt, self._acc["qy"] / self._acc_dt,
                    tau_for_morph, self._acc_dt * cfg.morph_accel)
                self.timing["morph_s"] += time.perf_counter() - _tm
                diag["channelization_index"] = self.channelization_index()
                diag["morph_interval_s"] = float(physical_morph_interval)
                self._acc_dt = 0.0
                for value in self._acc.values(): value.fill(0.0)
                self.last_morph_time = self.time
                self.morph_updates += 1
                for src_key, diag_key in (("lateral", "lateral_m3"), ("headcut", "headcut_m3"),
                                          ("collapse", "collapsed_m3"), ("toe_scour", "toe_scour_m3"),
                                          ("transport_net", "transport_net_erosion_m3")):
                    self.source_totals[src_key] += float(diag.get(diag_key, 0.0))
                if monitor is not None:
                    monitor.update(self)

            breach_metrics = self.breach_development()
            self.history.append({
                "time": self.time, "Q_in_prism": QL, "Q_prism_outlet": QR,
                "WL_res": self.reservoir.level,
                "max_tau": float(np.max(mesh.tau_b)),
                "min_zb": float(np.min(mesh.z_b)),
                "morph_interval_s": float(diag.get("morph_interval_s", 0.0)),
                "breach_depth_m": breach_metrics["depth_m"],
                "breach_width_m": breach_metrics["width_m"],
                "breach_area_m2": breach_metrics["area_m2"],
                "breach_development_index": breach_metrics["BDI"],
                "channelization_index": self.channelization_index(),
                "lateral_m3": float(diag.get("lateral_m3", 0.0)),
                "headcut_m3": float(diag.get("headcut_m3", 0.0)),
                "collapsed_m3": float(diag.get("collapsed_m3", 0.0)),
                "toe_scour_m3": float(diag.get("toe_scour_m3", 0.0)),
                "transport_net_erosion_m3": float(diag.get("transport_net_erosion_m3", 0.0)),
                "min_bank_FS": float(diag.get("min_bank_FS", 1e6)),
                "reservoir_hold_added_m3": self.reservoir.hold_added_m3,
            })
            if QR > self.peak_Q_prism_outlet:
                self.peak_Q_prism_outlet, self.peak_time = float(QR), self.time
                self.peak_decline_steps = 0
            elif QR < self.peak_Q_prism_outlet * (1.0 - max(peak_tolerance, 0.0)):
                self.peak_decline_steps += 1
            else:
                self.peak_decline_steps = 0

            if snapshot_dir and snapshot_interval_s is not None and self._next_snapshot is not None and self.time >= self._next_snapshot:
                self.save_snapshot(snapshot_dir)
                while self._next_snapshot <= self.time:
                    self._next_snapshot += snapshot_interval_s
            if checkpoint_path and checkpoint_interval_s is not None and self._next_checkpoint is not None and self.time >= self._next_checkpoint and morph_due:
                # Save only at morphology boundaries so no partial averaged-flow
                # interval is silently discarded on restart.
                while self._next_checkpoint <= self.time:
                    self._next_checkpoint += checkpoint_interval_s
                self.save_checkpoint(checkpoint_path)

            if verbose and self.time >= self.next_print:
                self.next_print = self.time + print_every
                print(f"t={self.time:7.2f}s  WLres={self.reservoir.level:6.3f}  "
                      f"Qprism={QL:8.3f}  Q_prism_outlet={QR:8.3f}  "
                      f"BDI={breach_metrics['BDI']:5.3f}  maxTau={np.max(mesh.tau_b):6.1f}  headcut_i={mesh.headcut_i}")
            if max_wall_seconds is not None and (time.perf_counter() - wall0) >= max_wall_seconds:
                if checkpoint_path:
                    self.save_checkpoint(checkpoint_path)
                self.stop_reason = "wall_time_pause"
                break
            if stop_on_balance_error_m3 is not None and morph_due:
                tol = abs(stop_on_balance_error_m3)
                if (abs(self.water_balance_error()) > tol or abs(self.reservoir_water_balance_error()) > tol
                        or abs(self.sediment_balance_error()) > tol):
                    self.stop_reason = "balance_error"
                    break
            if stop_when_drained_s is not None and self.reservoir.hold_level is None:
                if self.reservoir.volume <= drained_volume_m3:
                    drained_since = self.time if drained_since is None else drained_since
                    if self.time - drained_since >= stop_when_drained_s and morph_due:
                        self.stop_reason = "reservoir_drained"
                        break
                else:
                    drained_since = None
            if (stop_at_peak and self.peak_Q_prism_outlet > 0.0
                    and self.peak_decline_steps >= max(peak_confirm_steps, 1)
                    and self.last_morph_time > self.peak_time):
                self.stop_reason = "confirmed_prism_outlet_peak"
                break
        self.timing["wall_s"] += time.perf_counter() - wall0
        self.run_status = "completed" if self.stop_reason is None else f"stopped:{self.stop_reason}"
        return self.history


# =============================================================================
# 11B. INITIATION TOOLS (diagnostics, perturbation, pre-registered criterion)
# =============================================================================

def perturb_crest(mesh: MeshState, sigma: float, seed: int = 0, crest_fraction: float = 0.85) -> float:
    """Reproducible Gaussian bed perturbation on crest rows (call BEFORE building the engine).

    Crest rows are those whose transverse-mean bed is at least ``crest_fraction``
    of the maximum. Returns the net bed volume change [m3]. Bed stays >= floor.
    """
    row_mean = np.mean(mesh.z_b, axis=1)
    rows = row_mean >= crest_fraction * float(np.max(row_mean))
    rng = np.random.default_rng(seed)
    noise = np.zeros_like(mesh.z_b)
    noise[rows, :] = rng.normal(0.0, sigma, (int(np.count_nonzero(rows)), mesh.ny))
    new = np.maximum(mesh.z_b + noise, mesh.z_floor)
    change = float(np.sum(new - mesh.z_b)) * mesh.dx * mesh.dy
    mesh.z_b = new
    return change


def weak_spot(mesh: MeshState, x0: float, x1: float, y_center: float, y_halfwidth: float,
              depth: float) -> float:
    """Lower a rectangular patch of the bed by ``depth`` (a weak spot / notch). Returns removed bulk volume [m3]."""
    xs, ys = mesh.x[:, None], mesh.y[None, :]
    box = (xs >= x0) & (xs <= x1) & (np.abs(ys - y_center) <= y_halfwidth)
    new = np.where(box, np.maximum(mesh.z_b - depth, mesh.z_floor), mesh.z_b)
    removed = float(np.sum(mesh.z_b - new)) * mesh.dx * mesh.dy
    mesh.z_b = new
    return removed


def auto_seed_notch(mesh: MeshState, x0: float, length: float, depth: float = 0.15,
                    y_center: Optional[float] = None) -> float:
    """Numerical fallback notch (one cell wide). Not evidence of natural initiation."""
    yc = float(np.mean(mesh.y)) if y_center is None else y_center
    return weak_spot(mesh, x0, x0 + length, yc, 0.5 * mesh.dy, depth)


@dataclass(frozen=True)
class InitiationCriterion:
    """Pre-registered initiation success criterion; fix it BEFORE running."""
    min_lowering_m: float = 0.10
    min_channelization: float = 1.5
    min_bdi: float = 0.0
    t_max_s: float = 120.0
    require_unseeded: bool = True
    channelization_basis: str = "final"   # "final": last record in the window; "best": legacy maximum


class InitiationMonitor:
    """Records stress, lowering and channelization at each morphology update."""

    def __init__(self, tau_threshold: Optional[float] = None, lowering_threshold_m: float = 0.05):
        self.tau_threshold = tau_threshold
        self.lowering_threshold_m = lowering_threshold_m
        self.records: List[Dict[str, float]] = []
        self.t_first_tau_exceed: Optional[float] = None
        self.t_first_lowering: Optional[float] = None

    def update(self, engine: "UltimateBreachEngine") -> None:
        mesh = engine.mesh
        lowering = float(np.max(np.maximum(engine._initial_bed - mesh.z_b, 0.0)))
        tau_max = float(np.max(mesh.tau_b))
        tau_ref = engine.mat.tau_c if self.tau_threshold is None else self.tau_threshold
        if self.t_first_tau_exceed is None and tau_max >= tau_ref:
            self.t_first_tau_exceed = engine.time
        if self.t_first_lowering is None and lowering >= self.lowering_threshold_m:
            self.t_first_lowering = engine.time
        self.records.append({"time": engine.time, "tau_max": tau_max, "tau_ratio": tau_max / max(tau_ref, 1e-12),
                             "max_lowering_m": lowering,
                             "channelization_index": engine.channelization_index(),
                             "BDI": engine.breach_development()["BDI"]})


def initiation_success(monitor: InitiationMonitor, criterion: InitiationCriterion, *,
                       seeded: bool) -> Dict[str, object]:
    """Evaluate the pre-registered criterion on the monitor record (within t_max_s)."""
    window = [r for r in monitor.records if r["time"] <= criterion.t_max_s]
    best_low = max((r["max_lowering_m"] for r in window), default=0.0)
    eligible = [r["channelization_index"] for r in window if r["max_lowering_m"] >= criterion.min_lowering_m]
    if criterion.channelization_basis == "best":
        best_ci = max(eligible, default=0.0)
    elif criterion.channelization_basis == "final":
        best_ci = eligible[-1] if eligible else 0.0
    else:
        raise ValueError("channelization_basis must be 'final' or 'best'")
    best_bdi = max((r["BDI"] for r in window), default=0.0)
    checks = {"lowering": best_low >= criterion.min_lowering_m,
              "channelization": best_ci >= criterion.min_channelization,
              "bdi": best_bdi >= criterion.min_bdi,
              "unseeded": (not seeded) or (not criterion.require_unseeded)}
    return {"success": all(checks.values()), "checks": checks, "max_lowering_m": best_low,
            "channelization_at_lowering": best_ci, "BDI": best_bdi, "seeded": seeded}


# =============================================================================
# 12. DEMO
# =============================================================================

def make_demo_setup(pilot_notch: bool = True, transport: TransportFormula = TransportFormula.WU,
                    nx: int = 40, ny: int = 20, crest_roughness_sigma: float = 0.0,
                    random_seed: int = 0, auto_seeded_notch: bool = False):
    """Small synthetic earth dam; supports resolution and initiation ensembles.

    ``auto_seeded_notch`` is an explicitly labelled numerical fallback, not
    evidence of natural initiation. ``crest_roughness_sigma`` applies a
    reproducible perturbation to the otherwise level crest.
    """
    Lx, Ly = 40.0, 20.0
    if nx < 8 or ny < 4:
        raise ValueError("demo mesh requires nx >= 8 and ny >= 4")
    dx = Lx / nx
    x = (np.arange(nx) + 0.5) * dx
    height, crest_start, crest_end = 3.0, 15.0, 18.0
    zb = np.zeros((nx, ny))
    for i, xi in enumerate(x):
        if xi < crest_start:
            zb[i, :] = height * xi / crest_start
        elif xi <= crest_end:
            zb[i, :] = height
        else:
            zb[i, :] = height * max(0.0, 1.0 - (xi - crest_end) / 10.0)
    if pilot_notch:
        notch = (x >= crest_start - 1.0) & (x <= crest_start + 5.0)
        y_mid = Ly / 2.0
        cross = np.abs((np.arange(ny) + 0.5) * Ly / ny - y_mid) <= max(Ly / ny, 1.5)
        zb[np.ix_(notch, cross)] -= 0.60
    elif auto_seeded_notch:
        notch = (x >= crest_start) & (x <= crest_start + max(dx, 2.0))
        cross = np.arange(ny) == ny // 2
        zb[np.ix_(notch, cross)] -= 0.15
    if crest_roughness_sigma > 0:
        rng = np.random.default_rng(random_seed)
        on_crest = (x >= crest_start) & (x <= crest_end)
        zb[on_crest, :] += rng.normal(0.0, crest_roughness_sigma, (np.count_nonzero(on_crest), ny))

    level0 = 2.95
    eta = np.where(x[:, None] < crest_start, level0, -1e9) * np.ones((nx, ny))  # water upstream only
    mesh = create_prism_mesh(Lx, Ly, nx, ny, zb, eta, z_floor=0.0)
    mesh.headcut_i = 0

    res = Reservoir({0.0: 0.0, 2.0: 20_000.0, 3.0: 40_000.0, 4.0: 65_000.0}, level0)
    mat = MaterialProps(D50=0.003, cohesion=2000.0, phi=28.0, tau_c=1.5,
                        chen_k=80.0, chen_a=1.0, chen_b=0.4)
    cfg = EngineConfig(transport=transport,
                       bank_stability=BankStabilityMethod.CRITICAL_DEPTH,
                       dt_morpho_factor=4, chezy_C=35.0,
                       use_chen_detachment_cap=False)
    return mesh, res, mat, cfg


if __name__ == "__main__":
    print("=== Dam Breach Studio V3 -- demo ===")
    mesh, res, mat, cfg = make_demo_setup()
    z0 = mesh.z_b.copy()
    engine = UltimateBreachEngine(mesh, res, mat, cfg)
    engine.run(t_end=120.0, Qin=0.5, verbose=True, print_every=10.0,
               stop_at_peak=True, peak_confirm_steps=50)

    Qmax = engine.peak_Q_prism_outlet
    print("\nSimulation finished.")
    print(f"Final reservoir level   : {res.level:.3f} m")
    print(f"Peak prism outlet flux  : {Qmax:.2f} m3/s at {engine.peak_time:.2f} s")
    metrics = engine.breach_development()
    print(f"Breach diagnostics      : depth={metrics['depth_m']:.3f} m, width={metrics['width_m']:.3f} m, area={metrics['area_m2']:.3f} m2, BDI={metrics['BDI']:.4f}")
    print(f"Min bed elevation       : {mesh.z_b.min():.3f} m   (max lowering {np.max(z0 - mesh.z_b):.3f} m)")
    print(f"Water mass balance err  : {engine.water_balance_error():+.4f} m3")
    print(f"Solids mass balance err : {engine.sediment_balance_error():+.4f} m3")
    clip_rate = engine.hydro.speed_clip_events / max(engine.nsteps, 1)
    print(f"Speed-cap diagnostics   : events={engine.hydro.speed_clip_events} ({clip_rate:.3%} of steps), cells={engine.hydro.speed_clip_cells}, max_uncapped={engine.hydro.speed_clip_max_uncapped:.3f} m/s")
    print(f"Erosion caps            : Chen limited cells={engine.morpho.chen_cap_limited_cells}, detachment cap limited cells={engine.morpho.detachment_cap_limited_cells}")
    print(f"Sediment sources [m3]   : {engine.source_totals}")
    print(f"Timing split [s]        : {engine.timing}   status={engine.run_status}")
    locations = sorted(engine.hydro.speed_clip_locations.items(), key=lambda item: item[1], reverse=True)
    if locations:
        print("Most clipped cells      : " + ", ".join(f"({i},{j})×{n}" for (i, j), n in locations[:cfg.log_speed_clip_limit]))
    if engine.stop_reason:
        print(f"Stop reason             : {engine.stop_reason}")
