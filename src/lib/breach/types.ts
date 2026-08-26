export type FailureMode = "overtopping" | "piping";
export type BreachStage = "filling" | "piping" | "headcut" | "open" | "empty";

export interface StudioInputs {
  projectName: string;
  mode: FailureMode;

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
  inflowM3s: number;
  storageExponent: number;
  spillwayQ: number;

  rhoD: number;
  phiDeg: number;
  tauC: number;
  erosionIndexI: number;
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
  tMaxHours: number;
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
  inflowM3s: 2,
  storageExponent: 2,
  spillwayQ: 0,
  rhoD: 1800,
  phiDeg: 32,
  tauC: 8,
  erosionIndexI: 3.2,
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
  tMaxHours: 6,
};
