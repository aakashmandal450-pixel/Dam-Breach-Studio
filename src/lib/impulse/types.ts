/** Impulse-wave (VAW-style) input and result types — 2D / 3D generation & propagation. */

export interface Impulse2DInputs {
  /** Vertical drop of slide mass (centre of mass) before impact [m] */
  fallHeight: number;
  /** Slide impact velocity [m/s] — computed from fall height unless overridden */
  Vs: number;
  /** If true, Vs is computed as √(2 g Hfall); if false, user override */
  autoVelocity: boolean;
  /** Bulk slide volume [m³] */
  slideVolume: number;
  /** Slide thickness [m] */
  s: number;
  /** Slide / reservoir width [m] */
  b: number;
  /** Bulk slide density [kg/m³] */
  rhoS: number;
  /** Bulk slide porosity [%] 30–45 typical */
  nPercent: number;
  /** Slide impact angle [°] from horizontal */
  alphaDeg: number;
  /** Still water depth [m] */
  h: number;
  /** Streamwise distance from impact [m] */
  x: number;
}

export interface Impulse3DInputs extends Omit<Impulse2DInputs, "x"> {
  /** Radial distance from impact [m] */
  r: number;
  /** Propagation angle from slide axis [°] (0 = main lobe) */
  gammaDeg: number;
}

export interface Impulse2DLimits {
  F: { lo: number; hi: number; value: number; ok: boolean };
  S: { lo: number; hi: number; value: number; ok: boolean };
  M: { lo: number; hi: number; value: number; ok: boolean };
  D: { lo: number; hi: number; value: number; ok: boolean };
  V: { lo: number; hi: number; value: number; ok: boolean };
  B: { lo: number; hi: number; value: number; ok: boolean };
  X: { lo: number; hi: number; value: number; ok: boolean };
  P: { lo: number; hi: number; value: number; ok: boolean };
  alpha: { lo: number; hi: number; value: number; ok: boolean };
  n: { lo: number; hi: number; value: number; ok: boolean };
}

export interface Impulse3DLimits extends Omit<Impulse2DLimits, "X" | "B"> {
  R: { lo: number; hi: number; value: number; ok: boolean };
  gamma: { lo: number; hi: number; value: number; ok: boolean };
}

export interface Impulse2DResult {
  F: number;
  S: number;
  M: number;
  D: number;
  Vrel: number;
  B: number;
  X: number;
  P: number;
  HM: number;
  aM: number;
  xM: number;
  TM: number;
  cXM: number;
  LM: number;
  Hx: number;
  ax: number;
  Tx: number;
  cx: number;
  Lx: number;
  limits: Impulse2DLimits;
  warnings: string[];
}

export interface Impulse3DResult {
  F: number;
  S: number;
  M: number;
  D: number;
  Vrel: number;
  P: number;
  /** Radial relative distance r/h */
  Rrel: number;
  gammaDeg: number;
  HM: number;
  aM: number;
  rM: number;
  TM: number;
  cRM: number;
  LM: number;
  Hr: number;
  ar: number;
  Tr: number;
  cr: number;
  Lr: number;
  limits: Impulse3DLimits;
  warnings: string[];
}

export const DEFAULT_IMPULSE_2D: Impulse2DInputs = {
  fallHeight: 40,
  Vs: 28.0, // ≈ √(2 g 40)
  autoVelocity: true,
  slideVolume: 50_000,
  s: 8,
  b: 40,
  rhoS: 1800,
  nPercent: 36,
  alphaDeg: 45,
  h: 40,
  x: 400,
};

export const DEFAULT_IMPULSE_3D: Impulse3DInputs = {
  fallHeight: 40,
  Vs: 28.0,
  autoVelocity: true,
  slideVolume: 50_000,
  s: 8,
  b: 40,
  rhoS: 1800,
  nPercent: 36,
  alphaDeg: 45,
  h: 40,
  r: 400,
  gammaDeg: 0,
};
