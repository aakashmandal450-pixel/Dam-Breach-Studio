/** Screening inputs for ice-cored moraine thermal degradation (not a full FEM thermal model). */
export interface IceThermalInputs {
  /** Volumetric ice content in the ice-rich zone (0–1). Literature often 0–0.4+. */
  iceContent: number;
  /** Thickness of the ice-rich / ice-core zone [m]. */
  iceCoreThickness: number;
  /** Depth from crest to top of ice-rich zone [m]. */
  iceCoreDepth: number;
  /** Mean positive degree-days over the analysis season [°C·d]. */
  positiveDegreeDays: number;
  /** Degree-day factor for buried ice melt [mm water equivalent / (°C·d)]. Typical snow 3–8; buried ice lower ~1–4. */
  degreeDayFactorMm: number;
  /** Fraction of melt thickness that appears as crest settlement (void collapse). 0.3–0.8 typical screening. */
  settlementFactor: number;
  /** Erosion index while frozen / ice-bonded. */
  I_frozen: number;
  /** Erosion index fully thawed matrix. */
  I_thawed: number;
  /** Critical shear frozen [Pa]. */
  tauC_frozen: number;
  /** Critical shear thawed [Pa]. */
  tauC_thawed: number;
  /** Initial freeboard [m]. */
  freeboard0: number;
}

export interface IceThermalResult {
  /** Melt depth of ice-rich zone [m] (capped by core thickness). */
  meltDepth: number;
  /** Thaw fraction of the ice-rich zone 0–1. */
  thawFraction: number;
  /** Estimated crest settlement / freeboard loss [m]. */
  freeboardLoss: number;
  /** Remaining freeboard [m] (may be negative → overspill). */
  freeboardRemaining: number;
  /** Effective erosion index after thaw mixing. */
  I_eff: number;
  /** Effective critical shear [Pa]. */
  tauC_eff: number;
  overspillRisk: boolean;
  warnings: string[];
  notes: string[];
}

/** Simplified infinite-slope style screening for the distal (downstream) face. */
export interface MoraineStabilityInputs {
  /** Dam height Hb [m]. */
  height: number;
  /** Downstream face slope as H:1V (Z2). */
  zDown: number;
  /** Bulk unit weight [kN/m³]. */
  gamma: number;
  /** Cohesion [kPa]. */
  cohesion: number;
  /** Friction angle [°]. */
  phiDeg: number;
  /** Ru = u / (γ z), pore-pressure ratio. 0 dry … 0.3–0.5 saturated screening. */
  ru: number;
  /** Crest width / dam height (geometry robustness). */
  widthToHeight: number;
  /** Freeboard / dam height. */
  freeboardRatio: number;
  /** Ice-cored? applies strength knockdown. */
  iceCored: boolean;
  /** Thaw fraction 0–1 for strength knockdown. */
  thawFraction: number;
}

export interface MoraineStabilityResult {
  betaDeg: number;
  FoS: number;
  FoS_class: "stable" | "marginal" | "unstable";
  geometryRisk: "low" | "medium" | "high";
  freeboardRisk: "low" | "medium" | "high";
  compositeScore: number;
  compositeClass: "low" | "moderate" | "high" | "very_high";
  notes: string[];
}

export const DEFAULT_ICE_THERMAL: IceThermalInputs = {
  iceContent: 0.25,
  iceCoreThickness: 8,
  iceCoreDepth: 2,
  positiveDegreeDays: 200,
  degreeDayFactorMm: 2.5,
  settlementFactor: 0.5,
  I_frozen: 3.5,
  I_thawed: 1.8,
  tauC_frozen: 25,
  tauC_thawed: 5,
  freeboard0: 2,
};

export const DEFAULT_MORAINE_STABILITY: MoraineStabilityInputs = {
  height: 20,
  zDown: 2,
  gamma: 18,
  cohesion: 5,
  phiDeg: 32,
  ru: 0.2,
  widthToHeight: 0.4,
  freeboardRatio: 0.1,
  iceCored: true,
  thawFraction: 0.3,
};
