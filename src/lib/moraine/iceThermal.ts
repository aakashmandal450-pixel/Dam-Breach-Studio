import type { IceThermalInputs, IceThermalResult } from "./types";

/**
 * Screening ice-core degradation (degree-day style).
 * Not a multi-physics FEM: no latent-heat mesh, no seepage–thermal coupling.
 *
 * Melt depth ≈ (DDF · PDD) / 1000  [m water equivalent],
 * applied to the ice-rich zone and capped by iceCoreThickness.
 * Freeboard loss ≈ settlementFactor · meltDepth · iceContent (void collapse proxy).
 * Strength interpolates frozen → thawed with thaw fraction.
 */
export function computeIceThermal(p: IceThermalInputs): IceThermalResult {
  const warnings: string[] = [];
  const notes: string[] = [];

  const ice = clamp(p.iceContent, 0, 0.8);
  const Hice = Math.max(p.iceCoreThickness, 0);
  const PDD = Math.max(p.positiveDegreeDays, 0);
  const DDF = Math.max(p.degreeDayFactorMm, 0); // mm / (°C·d)

  // Melt depth in metres (water-equivalent screening of buried ice)
  let meltDepth = (DDF * PDD) / 1000;
  if (meltDepth > Hice) {
    meltDepth = Hice;
    warnings.push("Seasonal melt depth exceeds ice-core thickness — core treated as fully thawed in the ice-rich zone.");
  }

  const thawFraction = Hice > 0 ? clamp(meltDepth / Hice, 0, 1) : 0;

  // Settlement / freeboard loss: only the ice volume fraction collapses
  const freeboardLoss = Math.max(0, p.settlementFactor * meltDepth * ice);
  const freeboardRemaining = p.freeboard0 - freeboardLoss;
  const overspillRisk = freeboardRemaining <= 0;

  const I_eff = p.I_frozen + (p.I_thawed - p.I_frozen) * thawFraction;
  const tauC_eff = p.tauC_frozen + (p.tauC_thawed - p.tauC_frozen) * thawFraction;

  notes.push(
    "Degree-day melt is a screening proxy for buried ice; real rates depend on debris cover, aspect, and groundwater.",
  );
  notes.push(
    "Pass I_eff / τc_eff and reduced freeboard to the formation engine for a linked breach screening run.",
  );
  if (ice > 0.4) {
    warnings.push("Ice content > 40% is at the high end of published ranges — treat Qp sensitivity carefully.");
  }
  if (overspillRisk) {
    warnings.push("Estimated freeboard loss exceeds initial freeboard — overspill / breach initiation risk.");
  }

  return {
    meltDepth,
    thawFraction,
    freeboardLoss,
    freeboardRemaining,
    I_eff,
    tauC_eff,
    overspillRisk,
    warnings,
    notes,
  };
}

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}
