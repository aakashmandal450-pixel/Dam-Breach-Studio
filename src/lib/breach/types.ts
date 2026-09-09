export type FailureMode = "overtopping" | "piping";
export type DamStructure = "homogeneous" | "zoned" | "moraine" | "ice_cored_moraine";
export type BreachStage = "filling" | "piping" | "headcut" | "open" | "empty";

/** Matches ids in src/lib/lake/volume.ts */
export type LakeVolumeFormulaId =
  | "manual"
  | "sakai"
  | "cook_quincey"
  | "huggel"
  | "evans"
  | "oconnor";

/** Time unit for building a discrete inflow series. */
export type InflowIntervalUnit = "s" | "min" | "h";

/** One node of Q_in(t). timeSec is always stored in seconds from t = 0. */
export interface InflowSeriesPoint {
  timeSec: number;
  Q: number;
}

export interface StudioInputs {
  projectName: string;
  mode: FailureMode;
  damStructure: DamStructure;

  crestElev: number;
  baseElev: number;
  crestWidth: number;
  crestLength: number;
  zUp: number;
  zDown: number;
  coreLength: number;

  initialWL: number;
  volumeM3: number;
  surfaceAreaHa: number;
  /** How volumeM3 was obtained / suggested. */
  lakeVolumeFormula: LakeVolumeFormulaId;
  inflowM3s: number;
  /**
   * Optional discrete inflow hydrograph Q_in(t).
   * When non-empty and inflowSeriesEnabled, the engine interpolates Q at each step
   * instead of using the constant inflowM3s.
   */
  inflowSeriesEnabled: boolean;
  inflowSeries: InflowSeriesPoint[];
  /** UI helpers for regenerating the table (not required by engine). */
  inflowSeriesDuration: number;
  inflowSeriesInterval: number;
  inflowSeriesUnit: InflowIntervalUnit;
  storageExponent: number;
  spillwayQ: number;

  rhoD: number;
  phiDeg: number;
  tauC: number;
  erosionIndexI: number;
  /**
   * Exponent n on excess shear: ε = kd·(τ−τc)^n. Default 1 = today's linear
   * (Wan & Fell-style) behaviour for cohesive/fine soils. Literature values:
   * n≈1.3 for cohesionless sand/gravel (Chen & Anderson 1986), n≈1.5 matches
   * Meyer-Peter–Müller-style transport-capacity scaling (as used in NWS BREACH).
   * Applies to the core/homogeneous material (piping + non-zoned overtopping).
   */
  erosionExponent: number;
  /** Zoned dams: shell erosion index (overtopping). Core uses erosionIndexI for piping. */
  shellErosionIndexI: number;
  shellTauC: number;
  /** Same as erosionExponent but for the zoned-dam shell material. Default 1. */
  shellErosionExponent: number;

  /**
   * Zoned-dam core geometry (trapezoidal core drawn on the cross-section and used
   * by DamSchematic). ct = top width (m), Zc = core face batter (H:1V),
   * Hc/Hb = core height as a fraction of dam height.
   */
  coreTopWidth: number;
  coreSideSlope: number;
  coreHeightFraction: number;

  manningN: number;
  zb: number;
  /**
   * @deprecated No longer read by the engine. Open-breach and headcut-face widening now use a
   * geometric friction-angle slump (ΔWb = 2·dz·cot(φ) each step) instead of this multiplier —
   * see engine.ts. Field kept only so existing saved projects / UI forms don't break; safe to
   * remove once the UI stops referencing it.
   */
  sideErosionFactor: number;

  /**
   * Open-breach erosion closure (does NOT affect piping or the headcut face, which
   * always stay on excess-shear).
   *  - "excess_shear" (default): detachment-limited ε = kd·(τ−τc)^n — unchanged legacy law.
   *  - "transport_capacity": sediment-transport-limited Meyer-Peter–Müller with the
   *    Smart (1984) gradation factor + Exner continuity — the NWS BREACH lineage, for
   *    cohesionless / granular / moraine / rockfill material (NOT fine cohesive soils).
   */
  erosionModel: "excess_shear" | "transport_capacity";
  /**
   * How the excess-shear erodibility coefficient kd is obtained. Applies wherever the
   * excess-shear law is used (piping, headcut face, and open breach when
   * erosionModel = "excess_shear").
   *  - "index"  (default): kd = 10^(−I) / ρd — legacy Wan & Fell-style index (unchanged).
   *  - "hanson": kd = 2e-7 · τc^(−0.5)  [m³/(N·s)] — Hanson & Simon (2001) JET regression
   *              (kd[cm³/N·s] = 0.2·τc^(−0.5), converted to SI); forces the exponent n = 1.
   *  - "direct": use kdDirect, a measured JET value entered in cm³/(N·s) (converted to SI).
   */
  kdMode: "index" | "hanson" | "direct";
  /** Measured detachment-rate coefficient from a JET, in cm³/(N·s). Used only when kdMode = "direct". */
  kdDirect: number;

  /** Median grain size D50 (m). Transport-capacity closure only. */
  grainD50_m: number;
  /** Gradation ratio D90/D30 for the Smart (1984) factor (D90/D30)^0.2. Transport-capacity only. */
  grainD90D30Ratio: number;
  /** Sediment grain density ρs (kg/m³). Transport-capacity only. Default 2650 (quartz). */
  grainDensity: number;
  /** Bed porosity p (0–1) in the Exner conversion. Transport-capacity only. */
  porosity: number;
  /** Critical Shields parameter θc. Transport-capacity only. Default 0.047 (MPM). */
  criticalShields: number;
  /** Meyer-Peter–Müller transport coefficient Kt. Transport-capacity only. Default 8. */
  mpmCoefficient: number;

  /** Enable Temple/WinDAM-style headcut migration during overtopping. */
  headcutEnabled: boolean;
  /** Overtopping head (m) required before a discrete headcut is tracked. */
  headcutInitDepth: number;
  /** Multiplier on the excess-shear rate for horizontal headcut advance (typically 3–15). */
  headcutAdvanceFactor: number;
  /**
   * Which headcut-migration law drives horizontal scarp advance dxh/dt.
   *  - "hydrostatic" (default): legacy Temple-style dxh/dt = fh·ε(τ_face) with τ_face≈ρg·h_face.
   *  - "energy": WinDAM / USDA-SITES energy-dissipation law dX/dt = C·(q·H)^(1/3), q = unit
   *    overfall discharge [m²/s], H = drop height. C is a material headcut-erodibility that can
   *    be tied to the same JET anchor as kd. Only affects overtopping; piping is unchanged.
   */
  headcutLaw: "hydrostatic" | "energy";
  /** WinDAM/SITES energy-headcut coefficient C in dX/dt = C·(q·H)^(1/3). Used only when headcutLaw="energy". */
  headcutEnergyCoeff: number;
  /**
   * Deepening-gate throttle: fraction of the excess-shear rate allowed to lower the invert
   * WHILE the headcut is still migrating through the crest width C. Legacy value 0.25 (default,
   * unchanged). Exposed so the gate — long suspected of over-throttling wide-crest moraine
   * breaches — can be re-examined; raise toward 1 to let the invert deepen closer to the full rate.
   */
  headcutGateDeepenFraction: number;
  /** Per-step cap on gated deepening as a fraction of dam height Hb. Legacy 0.015 (default, unchanged). */
  headcutGateDeepenCap: number;

  /**
   * Wave-overtopping transient forcing (opt-in) — the GLOF wave→breach chain. When enabled in
   * overtopping mode, a displacement/impulse wave (from the Impulse module's run-up result)
   * rides over the crest as a short pulse of peak depth waveOvertopDepth for waveOvertopDuration,
   * supplying the erosive head that initiates incision when the still pool sits at/near the crest
   * (little/no freeboard — the classic moraine-GLOF trigger). Applied to the erosion hydraulics
   * ONLY, not to reservoir storage (a wave is a surface surge, not added lake volume). Off by
   * default → engine behaviour is byte-identical to the pre-wave model.
   */
  waveForcingEnabled: boolean;
  /** Peak wave-overtopping depth on the crest d0 [m] (from run-up). Wave forcing only. */
  waveOvertopDepth: number;
  /** Wave-overtopping duration tO [s] of one pulse (from run-up). Wave forcing only. */
  waveOvertopDuration: number;
  /** Number of successive wave pulses (a GLOF wave train). Default 1. Wave forcing only. */
  waveOvertopCount: number;
  /** Spacing between successive wave pulses [s] (0 → use waveOvertopDuration ≈ wave period). Wave forcing only. */
  waveOvertopPeriod: number;

  /**
   * Fraction (0–1) of the avalanche/slide bulk volume treated as submerged in the lake for the
   * ONE-TIME Archimedes displaced-volume step applied at wave-forcing handoff (see
   * applyAvalancheDisplacement in engine.ts). This is separate from — and applied BEFORE — the
   * transient wave pulse: the avalanche mass permanently occupies space in the lake (raising
   * volumeM3 / initialWL, same as dropping a rock in a full glass), while the wave itself is a
   * surface surge that must NOT touch reservoir volume (that stays on waveForcingEnabled).
   * Default 1.0 = fully submerged (conservative upper bound on the level rise). Lower values
   * account for material that piles up on the fan / above the waterline rather than displacing
   * water. Unused unless a slide volume is actually passed to applyAvalancheDisplacement.
   */
  avalancheSubmergedFraction: number;

  CdOrifice: number;
  Cw: number;
  initialNotchWidth: number;
  initialPipeRadius: number;
  pipeInvert: number;
  collapseRatio: number;

  /**
   * Discrete bank mass-wasting during open-breach widening (moraine / ice_cored_moraine
   * only — ignored for homogeneous/zoned). Screening proxy for the fluvial-erosion +
   * geotechnical bank-collapse coupling documented for moraine breaches (Westoby et al.
   * 2014, HR-BREACH; validated against Dig Tsho). Smooth excess-shear erosion alone
   * under-widens moraine channels; this adds periodic discrete slump events instead.
   */
  bankCollapseEnabled: boolean;
  /**
   * Unsupported bank height (as a fraction of dam height Hb) the channel can expose
   * via deepening before a bank-collapse event triggers. Screening proxy, not a
   * literal limit-equilibrium (Culmann) calculation — smaller values collapse more
   * often / in smaller increments. Typical 0.08–0.20.
   */
  bankCollapseHeightFraction: number;
  /**
   * Converts the exposed bank height at collapse into an instantaneous widening of
   * Wb (both banks retreat as the slumped wedge is washed out). Screening proxy.
   * Typical 1–3.
   */
  bankCollapseWidthFactor: number;

  dt: number;
  /** Display unit for dt (stored value is always seconds). */
  dtUnit: "s" | "min" | "h";
  tMaxHours: number;
  /** Display unit for max duration (stored value is always hours). */
  tMaxUnit: "s" | "min" | "h";
  /** Half-width for I uncertainty band (Qp at I±deltaI). */
  uncertaintyDeltaI: number;

  /**
   * When false, the GLOF / ice screening module is omitted entirely
   * (simple homogeneous or zoned earthfill runs). Default true so existing
   * projects keep the panel; turn off for ordinary dam-breach work.
   */
  glofIceEnabled: boolean;
}

export interface SimStep {
  t: number;
  Q: number;
  WL: number;
  zb: number;
  Wb: number;
  Wtop: number;
  R: number;
  /** Headcut position into the crest from the downstream edge (0 … crestWidth). */
  xHeadcut: number;
  tau: number;
  V: number;
  stage: BreachStage;
}

export interface SimResult {
  series: SimStep[];
  Qpeak: number;
  tPeak: number;
  tCollapse: number | null;
  /** Time when the headcut first reaches the upstream crest edge (overtopping). */
  tHeadcutBreach: number | null;
  tEmpty: number | null;
  finalWb: number;
  finalDepth: number;
  elapsedMs: number;
  warnings: string[];
}

export const DEFAULT_INPUTS: StudioInputs = {
  projectName: "Homogeneous earthfill — overtopping",
  mode: "overtopping",
  damStructure: "homogeneous",
  crestElev: 12,
  baseElev: 0,
  crestWidth: 4,
  crestLength: 80,
  zUp: 3,
  zDown: 2.5,
  coreLength: 18,
  initialWL: 12.15,
  volumeM3: 180000,
  surfaceAreaHa: 3.2,
  lakeVolumeFormula: "manual",
  inflowM3s: 2,
  inflowSeriesEnabled: false,
  inflowSeries: [],
  inflowSeriesDuration: 6,
  inflowSeriesInterval: 1,
  inflowSeriesUnit: "h",
  storageExponent: 2,
  spillwayQ: 0,
  rhoD: 1800,
  phiDeg: 32,
  tauC: 8,
  erosionIndexI: 3.2,
  erosionExponent: 1,
  shellErosionIndexI: 2.8,
  shellTauC: 5,
  shellErosionExponent: 1,
  manningN: 0.03,
  zb: 0.5,
  sideErosionFactor: 1.2,
  // Zoned-core geometry (cross-section drawing)
  coreTopWidth: 2.5,
  coreSideSlope: 0.5,
  coreHeightFraction: 0.85,
  // Erosion closure — defaults preserve the legacy excess-shear + index-kd behaviour exactly
  erosionModel: "excess_shear",
  kdMode: "index",
  kdDirect: 0.5,
  grainD50_m: 0.03,
  grainD90D30Ratio: 8,
  grainDensity: 2650,
  porosity: 0.35,
  criticalShields: 0.047,
  mpmCoefficient: 8,
  headcutEnabled: true,
  headcutInitDepth: 0.04,
  headcutAdvanceFactor: 6,
  // Headcut law + deepening-gate — defaults preserve the legacy hydrostatic behaviour exactly
  headcutLaw: "hydrostatic",
  headcutEnergyCoeff: 0.5,
  headcutGateDeepenFraction: 0.25,
  headcutGateDeepenCap: 0.015,
  // Wave-overtopping transient forcing — off by default (regression-safe)
  waveForcingEnabled: false,
  waveOvertopDepth: 0,
  waveOvertopDuration: 0,
  waveOvertopCount: 1,
  waveOvertopPeriod: 0,
  avalancheSubmergedFraction: 1.0,
  CdOrifice: 0.6,
  Cw: 1.7,
  initialNotchWidth: 1.2,
  initialPipeRadius: 0.08,
  pipeInvert: 4,
  collapseRatio: 0.55,
  bankCollapseEnabled: true,
  bankCollapseHeightFraction: 0.12,
  bankCollapseWidthFactor: 1.5,
  dt: 2,
  dtUnit: "s",
  tMaxHours: 6,
  tMaxUnit: "h",
  uncertaintyDeltaI: 0.5,
  glofIceEnabled: true,
};
