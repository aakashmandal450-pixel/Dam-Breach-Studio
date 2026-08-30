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
  /** Zoned dams: shell erosion index (overtopping). Core uses erosionIndexI for piping. */
  shellErosionIndexI: number;
  shellTauC: number;
  manningN: number;
  zb: number;
  sideErosionFactor: number;

  /** Enable Temple/WinDAM-style headcut migration during overtopping. */
  headcutEnabled: boolean;
  /** Overtopping head (m) required before a discrete headcut is tracked. */
  headcutInitDepth: number;
  /** Multiplier on the excess-shear rate for horizontal headcut advance (typically 3–15). */
  headcutAdvanceFactor: number;

  CdOrifice: number;
  Cw: number;
  initialNotchWidth: number;
  initialPipeRadius: number;
  pipeInvert: number;
  collapseRatio: number;

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
  shellErosionIndexI: 2.8,
  shellTauC: 5,
  manningN: 0.03,
  zb: 0.5,
  sideErosionFactor: 1.2,
  headcutEnabled: true,
  headcutInitDepth: 0.04,
  headcutAdvanceFactor: 6,
  CdOrifice: 0.6,
  Cw: 1.7,
  initialNotchWidth: 1.2,
  initialPipeRadius: 0.08,
  pipeInvert: 4,
  collapseRatio: 0.55,
  dt: 2,
  dtUnit: "s",
  tMaxHours: 6,
  tMaxUnit: "h",
  uncertaintyDeltaI: 0.5,
  glofIceEnabled: true,
};
