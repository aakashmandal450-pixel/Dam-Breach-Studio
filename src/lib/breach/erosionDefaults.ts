import type { DamStructure, StudioInputs } from "./types";

/**
 * Screening defaults for the open-breach erosion closure by dam structure.
 *
 * Rationale: the Meyer-Peter–Müller / Smart transport-capacity law is a bedload
 * relation for cohesionless / granular material. Moraine and rockfill debris are
 * the natural fit (NWS BREACH lineage). Engineered cohesive fills and zoned clay
 * cores stay on the detachment-limited excess-shear law, where MPM would badly
 * over-predict as the effective grain size drops (θ explodes near threshold).
 *
 * Grain defaults are only consumed when erosionModel = "transport_capacity", so
 * they are harmless for the excess-shear structures.
 */
export function erosionDefaultsForStructure(s: DamStructure | undefined): {
  erosionModel: StudioInputs["erosionModel"];
  grainD50_m: number;
  grainD90D30Ratio: number;
} {
  switch (s) {
    case "moraine":
      // Poorly-sorted gravelly-cobbly debris matrix
      return { erosionModel: "transport_capacity", grainD50_m: 0.04, grainD90D30Ratio: 10 };
    case "ice_cored_moraine":
      // Finer thawed matrix, still granular
      return { erosionModel: "transport_capacity", grainD50_m: 0.025, grainD90D30Ratio: 8 };
    case "zoned":
    case "homogeneous":
    default:
      return { erosionModel: "excess_shear", grainD50_m: 0.03, grainD90D30Ratio: 8 };
  }
}
