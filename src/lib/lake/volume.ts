/**
 * Empirical glacial-lake volume from surface area.
 * Formulas are inventory / regional regressions — not bathymetry.
 * Prefer surveyed V when available; always show the applicability note.
 *
 * Unit conventions (from the source papers):
 * - Sakai, Huggel, Evans-style: A in km², V in 10⁶ m³
 * - Cook & Quincey (re-plot of Huggel): V = 0.1217 · A^1.4129 with A in m², V in m³
 * - O’Connor (Cascades): V (m³) = 3.114 · A + 0.0001685 · A² with A in m²
 */

export type LakeVolumeFormulaId =
  | "manual"
  | "sakai"
  | "cook_quincey"
  | "huggel"
  | "evans"
  | "oconnor";

export interface LakeVolumeFormula {
  id: LakeVolumeFormulaId;
  name: string;
  region: string;
  /** V (m³) given A (m²). */
  compute: (areaM2: number) => number;
  note: string;
}

export const LAKE_VOLUME_FORMULAS: LakeVolumeFormula[] = [
  {
    id: "manual",
    name: "Manual / surveyed",
    region: "Any",
    compute: () => 0,
    note: "Enter volume directly from bathymetry or stage–storage. Preferred when data exist.",
  },
  {
    id: "sakai",
    name: "Sakai (Himalaya)",
    region: "Himalaya",
    // V (10⁶ m³) = 43.24 · A(km²)^1.53
    compute: (areaM2) => {
      const A_km2 = areaM2 / 1e6;
      return 43.24 * Math.pow(Math.max(A_km2, 1e-12), 1.53) * 1e6;
    },
    note: "Himalayan moraine-dammed lakes (Sakai 2012). Typical for larger Himalayan inventory lakes.",
  },
  {
    id: "cook_quincey",
    name: "Cook & Quincey (global)",
    region: "Global compilations",
    // Re-plot of Huggel data: V (m³) = 0.1217 · A(m²)^1.4129
    compute: (areaM2) => {
      return 0.1217 * Math.pow(Math.max(areaM2, 1), 1.4129);
    },
    note: "Global compilation (Cook & Quincey 2015, re-plot of Huggel). Broad screening; scatter is large.",
  },
  {
    id: "huggel",
    name: "Huggel",
    region: "Alpine / similar",
    // Common form: V (10⁶ m³) = 0.104 · A(km²)^1.42
    compute: (areaM2) => {
      const A_km2 = areaM2 / 1e6;
      return 0.104 * Math.pow(Math.max(A_km2, 1e-12), 1.42) * 1e6;
    },
    note: "Alpine and similar lakes (Huggel et al.). Useful first estimate outside the Himalaya.",
  },
  {
    id: "evans",
    name: "Evans",
    region: "Broad screening",
    // V (10⁶ m³) = 0.035 · A(km²)^1.5
    compute: (areaM2) => {
      const A_km2 = areaM2 / 1e6;
      return 0.035 * Math.pow(Math.max(A_km2, 1e-12), 1.5) * 1e6;
    },
    note: "Simple power-law screening (Evans). Often gives a lower volume for a given area.",
  },
  {
    id: "oconnor",
    name: "O’Connor (Cascades)",
    region: "Cascades-type",
    // V (m³) = 3.114 · A + 0.0001685 · A²  with A in m²
    compute: (areaM2) => {
      const A = Math.max(areaM2, 0);
      return 3.114 * A + 0.0001685 * A * A;
    },
    note: "Cascades moraine-dammed lakes (O’Connor et al. 2001). Quadratic; suited to that size range.",
  },
];

export function getLakeFormula(id: LakeVolumeFormulaId): LakeVolumeFormula {
  return LAKE_VOLUME_FORMULAS.find((f) => f.id === id) ?? LAKE_VOLUME_FORMULAS[0];
}

export function haToM2(ha: number): number {
  return ha * 10_000;
}

/** Estimate volume (m³) from area (ha) and formula id. Returns 0 for manual. */
export function estimateLakeVolume(areaHa: number, formulaId: LakeVolumeFormulaId): number {
  if (formulaId === "manual" || areaHa <= 0) return 0;
  const f = getLakeFormula(formulaId);
  return f.compute(haToM2(areaHa));
}

/** Freeboard = crest elevation − water surface elevation (positive when WL below crest). */
export function freeboard(crestElev: number, waterElev: number): number {
  return crestElev - waterElev;
}
