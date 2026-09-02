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
  rhoGRatio: { lo: number; hi: number; value: number; ok: boolean };
  B: { lo: number; hi: number; value: number; ok: boolean };
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
  // Dimensionless groups (VAW Table 3-3)
  F: number;
  S: number;
  M: number;
  D: number;
  /** Relative granulate density ρg/ρw = (ρs/(1-n)) / ρw — distinct from D. */
  rhoGRatio: number;
  Vrel: number;
  B: number;
  /** Relative radial distance r/h */
  Rrel: number;
  gammaDeg: number;
  P: number;

  // Near-field geometry (Eq. 3.22-3.25)
  /** Near-field boundary radius along the slide axis, γ=0° [m] */
  r0_0: number;
  /** Near-field boundary radius perpendicular to the slide axis, γ=90° [m] */
  r0_90: number;
  /** Near-field boundary radius at the actual propagation angle γ [m] */
  r0Gamma: number;
  /** Distance beyond the near-field boundary, r - r0(γ) [m]. Only meaningful when !insideNearField. */
  rStar: number;

  // Near-field amplitude components at the r0(γ) boundary (Eq. 3.26-3.28)
  /** Leading crest amplitude at the near-field boundary [m] */
  a0c1: number;
  /** Trough amplitude at the near-field boundary [m] */
  a0t1: number;
  /** Second crest amplitude at the near-field boundary [m] */
  a0c2: number;

  /** True when r < r0(γ) — the dam/gauge point sits inside the slide's near-field
   * zone, where VAW defines no far-field formula (the sheet just shows "r < r_0").
   * ac1/at1/ac2/cc1/cc2/T1/L1 are null in this case; use a0c1/a0t1/a0c2 instead. */
  insideNearField: boolean;

  // Far-field wave components at (r, γ) — Eq. 3.29-3.35, null if insideNearField
  ac1: number | null;
  at1: number | null;
  ac2: number | null;
  cc1: number | null;
  cc2: number | null;
  T1: number | null;
  L1: number | null;

  /**
   * Convenience "representative wave" fields for run-up / breach chaining —
   * NOT a VAW-named quantity itself. a = ac1, H = ac1 + at1 (VAW's own
   * convention in the T1 formula), T = T1, c = cc1, L = L1. Falls back to
   * the near-field boundary values (a0c1, a0c1+a0t1, ...) when
   * insideNearField is true, since run-up still needs *some* estimate —
   * flagged via insideNearField rather than silently extrapolated.
   */
  aM: number;
  HM: number;
  TM: number;
  /** = r0Gamma, kept under this name for UI continuity with the 2D panel's "location of aM" stat. */
  rM: number;
  cRM: number;
  LM: number;

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
